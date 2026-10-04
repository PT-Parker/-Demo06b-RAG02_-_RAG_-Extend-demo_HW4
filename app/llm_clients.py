"""標準函式庫 REST clients，支援每次請求的模型與金鑰設定。

Contracts checked against the official Gemini generateContent / models APIs,
Groq OpenAI compatibility guide, and OpenAI Chat Completions reference:
https://ai.google.dev/api/generate-content
https://ai.google.dev/api/models
https://console.groq.com/docs/openai
https://developers.openai.com/api/reference/resources/chat
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any
from urllib import parse, request

LOGGER = logging.getLogger(__name__)
TIMEOUT_SECONDS = 30
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
SYSTEM_PROMPT = (
    "你是台股知識助理，請根據提供的文件片段回答問題，"
    "用繁體中文簡潔作答並附上引用來源編號；若資料不足請坦白說明。"
)


def _request_json(url: str, headers: dict[str, str], payload: dict | None = None) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = request.Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    with request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not isinstance(result, dict):
        raise ValueError("Expected a JSON object")
    return result


def _gemini_text(response: dict[str, Any]) -> str | None:
    candidates = response.get("candidates") or []
    if not candidates:
        return None
    parts = candidates[0].get("content", {}).get("parts", [])
    # Thought parts are distinct from the model's final answer.
    texts = [part["text"] for part in parts
             if isinstance(part.get("text"), str) and not part.get("thought")]
    answer = "".join(texts).strip()
    return answer or None


def call_llm(prompt: str, gemini_api_key: str | None = None,
             gemini_model: str | None = None) -> str | None:
    """Prefer Gemini, then an explicitly configured Groq or OpenAI credential.

    None reads GEMINI_API_KEY; an explicit empty key suppresses that fallback.
    Configuration is read for each request and never written to os.environ.
    Failures return None so the caller can display the retrieved excerpts.
    """
    key = (os.getenv("GEMINI_API_KEY", "") if gemini_api_key is None else gemini_api_key).strip()
    if key:
        model = (gemini_model or os.getenv("RAG_GEMINI_MODEL") or DEFAULT_GEMINI_MODEL).strip()
        model = model.removeprefix("models/")
        url = f"{GEMINI_BASE_URL}/models/{parse.quote(model, safe='')}:generateContent"
        try:
            response = _request_json(
                url, {"Content-Type": "application/json", "x-goog-api-key": key},
                {"systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                 "contents": [{"role": "user", "parts": [{"text": prompt}]}]},
            )
            answer = _gemini_text(response)
            if answer:
                return answer
        except Exception as exc:
            # Provider exceptions can contain URLs, headers, or response bodies.
            LOGGER.warning("Gemini request failed (%s)", type(exc).__name__)

    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    key = groq_key or os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        return None
    default_base = "https://api.groq.com/openai/v1" if groq_key else "https://api.openai.com/v1"
    default_model = "openai/gpt-oss-120b" if groq_key else "gpt-4o-mini"
    base_url = (os.getenv("RAG_OPENAI_BASE_URL") or default_base).rstrip("/")
    model = (os.getenv("RAG_LLM_MODEL") or default_model).strip().removeprefix("groq:")
    try:
        response = _request_json(
            f"{base_url}/chat/completions",
            {"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
            {"model": model, "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]},
        )
        choices = response.get("choices") or []
        content = choices[0].get("message", {}).get("content") if choices else None
        return content.strip() or None if isinstance(content, str) else None
    except Exception as exc:
        LOGGER.warning("OpenAI-compatible request failed (%s)", type(exc).__name__)
        return None


def fetch_gemini_models(api_key: str) -> list[str]:
    """List generateContent-capable model resource names across all pages."""
    key = api_key.strip()
    if not key:
        return []
    names: list[str] = []
    seen_names: set[str] = set()
    seen_tokens: set[str] = set()
    page_token = ""
    try:
        while True:
            suffix = "?" + parse.urlencode({"pageToken": page_token}) if page_token else ""
            response = _request_json(f"{GEMINI_BASE_URL}/models{suffix}", {"x-goog-api-key": key})
            for model in response.get("models", []):
                name = model.get("name")
                if (isinstance(name, str) and name
                        and "generateContent" in model.get("supportedGenerationMethods", [])
                        and name not in seen_names):
                    names.append(name)
                    seen_names.add(name)
            page_token = response.get("nextPageToken") or ""
            if not page_token:
                return names
            if not isinstance(page_token, str) or page_token in seen_tokens:
                raise ValueError("Invalid pagination token")
            seen_tokens.add(page_token)
    except Exception as exc:
        LOGGER.warning("Gemini model listing failed (%s)", type(exc).__name__)
        return []
