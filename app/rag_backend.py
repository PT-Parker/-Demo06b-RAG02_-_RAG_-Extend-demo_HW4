"""
簡易台股 RAG 後端，從 Demo06b notebook 重構而來。

功能：
- 載入本地 Markdown 知識庫，分割成 chunk 並建立 FAISS 向量索引。
- 使用 HuggingFace Embeddings（預設為 google/embeddinggemma-300m，無權杖時退回 MiniLM）。
- 提供 retriever 以及 rag_answer 函式，回傳答案與引用片段。

環境變數：
- TW_STOCK_CORPUS_DIR：自訂知識庫路徑，預設 data/tw_stock_corpus。
- RAG_TOP_K：檢索數量，預設 4。
- GROQ_API_KEY / OPENAI_API_KEY：呼叫 LLM 用，未提供時改用檢索摘要回應。
- RAG_LLM_MODEL：LLM 名稱，預設 groq:openai/gpt-oss-120b。
- RAG_OPENAI_BASE_URL：OpenAI 相容端點，Groq 預設 https://api.groq.com/openai/v1。
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.documents import Document
try:
    # langchain >=0.2 拆分為獨立套件
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:  # pragma: no cover - 舊版相容
    from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# 參數與預設值
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS_DIR = PROJECT_ROOT / "data" / "tw_stock_corpus"
SYSTEM_PROMPT = (
    "你是台股知識助理，請根據提供的文件片段回答問題，"
    "用繁體中文簡潔作答並附上引用來源編號；若資料不足請坦白說明。"
)
DEFAULT_MODEL = "groq:openai/gpt-oss-120b"


class EmbeddingGemmaEmbeddings(HuggingFaceEmbeddings):
    """沿用 Demo06b 的 embedding 前綴，保持檢索表現。"""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            model_name="google/embeddinggemma-300m",
            encode_kwargs={"normalize_embeddings": True},
            **kwargs,
        )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        decorated = [f"title: none | text: {t}" for t in texts]
        return super().embed_documents(decorated)

    def embed_query(self, text: str) -> List[float]:
        return super().embed_query(f"task: search result | query: {text}")


def _resolve_corpus_dir(corpus_dir: Optional[str] = None) -> Path:
    return Path(corpus_dir or os.getenv("TW_STOCK_CORPUS_DIR", DEFAULT_CORPUS_DIR)).resolve()


def load_corpus(corpus_dir: Optional[str] = None) -> List[Document]:
    """讀取 corpus 目錄並切成 chunk，附上來源檔名以供引用。"""
    target_dir = _resolve_corpus_dir(corpus_dir)
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=120)
    docs: List[Document] = []

    for path in sorted(target_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for idx, chunk in enumerate(splitter.split_text(text)):
            docs.append(
                Document(
                    page_content=chunk.strip(),
                    metadata={"source": path.name, "chunk_id": idx},
                )
            )

    if not docs:
        raise FileNotFoundError(f"未找到任何知識檔案，請確認路徑：{target_dir}")

    return docs


def _build_embedding_model() -> HuggingFaceEmbeddings:
    """優先使用 Demo06b 的 Gemma embedding，缺 token 時退回 MiniLM。"""
    hf_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
    try:
        kwargs = {}
        if hf_token:
            kwargs["huggingfacehub_api_token"] = hf_token
        return EmbeddingGemmaEmbeddings(**kwargs)
    except Exception as exc:  # pragma: no cover - 僅作防護
        logging.warning("Gemma embedding 建立失敗，改用 MiniLM：%s", exc)
        return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


def build_vector_store(docs: List[Document]) -> FAISS:
    embeddings = _build_embedding_model()
    return FAISS.from_documents(docs, embeddings)


def get_retriever(vs: FAISS, top_k: int = 5):
    return vs.as_retriever(search_kwargs={"k": top_k})


@lru_cache(maxsize=1)
def _lazy_vector_store() -> FAISS:
    docs = load_corpus()
    return build_vector_store(docs)


def _ensure_retriever(top_k: Optional[int] = None):
    vs = _lazy_vector_store()
    k = top_k or int(os.getenv("RAG_TOP_K", "4"))
    return vs, get_retriever(vs, k)


def _retrieve_docs(retriever: Any, query: str) -> List[Document]:
    """兼容新版 Retriever 介面（invoke）與舊版 get_relevant_documents。"""
    if hasattr(retriever, "get_relevant_documents"):
        return retriever.get_relevant_documents(query)
    if hasattr(retriever, "invoke"):
        result = retriever.invoke(query)
        if isinstance(result, list):
            return result
    raise AttributeError("retriever 物件缺少檢索方法")


def _format_context(docs: List[Document]) -> str:
    lines = []
    for idx, doc in enumerate(docs, start=1):
        src = doc.metadata.get("source", "unknown")
        lines.append(f"[{idx}] 來源: {src}\n{doc.page_content}")
    return "\n\n".join(lines)


def _format_history(history: Optional[List[Dict[str, str]]]) -> str:
    if not history:
        return "（無對話紀錄）"
    pairs = []
    for turn in history[-5:]:
        q = turn.get("question") or turn.get("user") or ""
        a = turn.get("answer") or turn.get("agent") or ""
        pairs.append(f"Q: {q}\nA: {a}")
    return "\n".join(pairs)


def _call_llm(prompt: str) -> str:
    # 1) 優先走 Gemini
    gemini_key = os.getenv("GEMINI_API_KEY")
    gemini_model = os.getenv("RAG_LLM_MODEL", "gemini-1.5-flash")
    if gemini_key:
        try:
            import google.generativeai as genai  # type: ignore

            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel(gemini_model)
            resp = model.generate_content(prompt)
            if hasattr(resp, "text") and resp.text:
                return resp.text
        except Exception as exc:  # pragma: no cover
            logging.warning("Gemini 呼叫失敗，嘗試其他路徑：%s", exc)

    # 2) 退回 OpenAI 相容端點（如 Groq/OpenRouter）
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
    model = os.getenv("RAG_LLM_MODEL", DEFAULT_MODEL)
    base_url = os.getenv("RAG_OPENAI_BASE_URL", "https://api.groq.com/openai/v1")
    if api_key:
        try:
            import aisuite as ai  # type: ignore

            client = ai.Client(api_key=api_key, base_url=base_url)
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
            return resp.choices[0].message.content
        except Exception as exc:  # pragma: no cover
            logging.warning("OpenAI 相容端點呼叫失敗，改用檢索摘要：%s", exc)

    return "目前無法連線至 LLM，以下為根據檢索片段彙整的摘要：\n" + prompt[:1200]


def rag_answer(query: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    """傳回答案、引用來源與檢索片段。"""
    vs, retriever = _ensure_retriever()
    docs = _retrieve_docs(retriever, query)

    if not docs:
        fallback = "知識庫未找到相關內容，請嘗試調整關鍵字或查閱公開資訊觀測站。"
        return {
            "question": query,
            "answer": fallback,
            "citations": [],
            "retrieved_chunks": [],
        }

    context_block = _format_context(docs)
    prompt = (
        f"使用者問題：{query}\n\n"
        f"對話紀錄：\n{_format_history(history)}\n\n"
        f"以下是檢索到的資料片段，請整理重點回答並標註引用編號：\n{context_block}\n\n"
        "回覆格式：先給出中文答案，最後列出參考來源的編號與檔名。"
    )
    answer = _call_llm(prompt).strip()

    citations = [
        {"id": idx, "source": doc.metadata.get("source", "unknown"), "snippet": doc.page_content}
        for idx, doc in enumerate(docs, start=1)
    ]
    retrieved = [
        {"source": doc.metadata.get("source", "unknown"), "chunk_id": doc.metadata.get("chunk_id"), "text": doc.page_content}
        for doc in docs
    ]

    if "參考來源" not in answer:
        cite_text = "\n".join([f"[{c['id']}] {c['source']}" for c in citations])
        answer = f"{answer}\n\n參考來源：\n{cite_text}"

    return {
        "question": query,
        "answer": answer,
        "citations": citations,
        "retrieved_chunks": retrieved,
    }


if __name__ == "__main__":  # 簡易手動測試
    demo_q = "台積電的主要風險是什麼？"
    result = rag_answer(demo_q)
    print(result["answer"])
