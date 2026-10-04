"""REST client regression tests using mock responses."""

import io
import json
import os
import unittest
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from app import llm_clients as clients


def json_response(payload):
    return io.BytesIO(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


def gemini_response(text="回答"):
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def compatible_response(text="回答"):
    return {"choices": [{"message": {"content": text}}]}


class LlmClientsTests(unittest.TestCase):
    def setUp(self):
        self.env_patch = patch.dict(os.environ, {}, clear=True)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.http_patch = patch.object(clients.request, "urlopen")
        self.urlopen = self.http_patch.start()
        self.addCleanup(self.http_patch.stop)

    def request_at(self, index=0):
        args, kwargs = self.urlopen.call_args_list[index]
        self.assertEqual(kwargs["timeout"], 30)
        return args[0]

    def test_no_credentials_never_opens_network(self):
        self.assertIsNone(clients.call_llm("問題"))
        self.urlopen.assert_not_called()

    def test_gemini_override_builds_rest_body_without_mutating_environment(self):
        os.environ.update({"GEMINI_API_KEY": "environment-dummy", "RAG_GEMINI_MODEL": "env-model",
                           "RAG_LLM_MODEL": "groq:other-model"})
        before = dict(os.environ)
        self.urlopen.return_value = json_response(gemini_response(" 回答 "))
        self.assertEqual(clients.call_llm("風險？", "session-dummy", "models/custom-model"), "回答")
        req = self.request_at()
        self.assertEqual(req.full_url, clients.GEMINI_BASE_URL + "/models/custom-model:generateContent")
        self.assertEqual(req.get_header("X-goog-api-key"), "session-dummy")
        self.assertNotIn("session-dummy", req.full_url)
        self.assertEqual(req.method, "POST")
        self.assertEqual(json.loads(req.data)["contents"], [{"role": "user", "parts": [{"text": "風險？"}]}])
        self.assertEqual(dict(os.environ), before)

    def test_none_gemini_key_reads_environment_and_provider_specific_model(self):
        os.environ.update({"GEMINI_API_KEY": "env-dummy", "RAG_GEMINI_MODEL": "env-model",
                           "RAG_LLM_MODEL": "groq:wrong-provider"})
        self.urlopen.return_value = json_response(gemini_response())
        self.assertEqual(clients.call_llm("問題"), "回答")
        req = self.request_at()
        self.assertIn("/models/env-model:generateContent", req.full_url)
        self.assertEqual(req.get_header("X-goog-api-key"), "env-dummy")

    def test_default_gemini_model(self):
        self.urlopen.return_value = json_response(gemini_response())
        self.assertEqual(clients.call_llm("問題", "dummy"), "回答")
        self.assertIn("/models/gemini-2.5-flash:generateContent", self.request_at().full_url)

    def test_explicit_empty_key_suppresses_environment_gemini(self):
        os.environ["GEMINI_API_KEY"] = "env-dummy"
        self.assertIsNone(clients.call_llm("問題", ""))
        self.urlopen.assert_not_called()

    def test_openai_key_selects_openai_endpoint_and_model(self):
        os.environ["OPENAI_API_KEY"] = "openai-dummy"
        self.urlopen.return_value = json_response(compatible_response())
        self.assertEqual(clients.call_llm("問題"), "回答")
        req = self.request_at()
        self.assertEqual(req.full_url, "https://api.openai.com/v1/chat/completions")
        self.assertEqual(req.get_header("Authorization"), "Bearer openai-dummy")
        self.assertEqual(json.loads(req.data)["model"], "gpt-4o-mini")

    def test_groq_has_priority_and_uses_groq_default_model(self):
        os.environ.update({"GROQ_API_KEY": "groq-dummy", "OPENAI_API_KEY": "openai-dummy"})
        self.urlopen.return_value = json_response(compatible_response())
        self.assertEqual(clients.call_llm("問題"), "回答")
        req = self.request_at()
        self.assertEqual(req.full_url, "https://api.groq.com/openai/v1/chat/completions")
        self.assertEqual(req.get_header("Authorization"), "Bearer groq-dummy")
        self.assertEqual(json.loads(req.data)["model"], "openai/gpt-oss-120b")

    def test_compatible_custom_endpoint_and_legacy_provider_prefix(self):
        os.environ.update({"GROQ_API_KEY": "groq-dummy", "RAG_LLM_MODEL": "groq:custom-model",
                           "RAG_OPENAI_BASE_URL": "https://example.invalid/v1/"})
        self.urlopen.return_value = json_response(compatible_response())
        self.assertEqual(clients.call_llm("問題"), "回答")
        req = self.request_at()
        self.assertEqual(req.full_url, "https://example.invalid/v1/chat/completions")
        self.assertEqual(json.loads(req.data)["model"], "custom-model")

    def test_gemini_failure_uses_configured_backup_and_logs_no_exception_details(self):
        os.environ.update({"GEMINI_API_KEY": "gemini-dummy", "OPENAI_API_KEY": "openai-dummy"})
        self.urlopen.side_effect = [URLError("secret-key-containing-error"), json_response(compatible_response("備援"))]
        with self.assertLogs(clients.LOGGER, level="WARNING") as logs:
            self.assertEqual(clients.call_llm("問題"), "備援")
        self.assertNotIn("secret-key-containing-error", "\n".join(logs.output))
        self.assertIn("URLError", "\n".join(logs.output))
        self.assertEqual(self.request_at(1).full_url, "https://api.openai.com/v1/chat/completions")

    def test_empty_or_blocked_gemini_response_uses_backup(self):
        os.environ.update({"GEMINI_API_KEY": "gemini-dummy", "GROQ_API_KEY": "groq-dummy"})
        self.urlopen.side_effect = [json_response({"promptFeedback": {"blockReason": "SAFETY"}}),
                                    json_response(compatible_response("備援"))]
        self.assertEqual(clients.call_llm("問題"), "備援")
        self.assertEqual(self.urlopen.call_count, 2)

    def test_gemini_thought_parts_are_excluded_from_answer(self):
        self.urlopen.return_value = json_response({"candidates": [{"content": {"parts": [
            {"thought": True, "text": "thought content"}, {"text": " 最終"}, {"text": "回答 "}]} }]})
        self.assertEqual(clients.call_llm("問題", "dummy"), "最終回答")

    def test_empty_or_malformed_compatible_responses_return_none(self):
        os.environ["OPENAI_API_KEY"] = "dummy"
        for payload in ({}, {"choices": []}, compatible_response(" "), compatible_response(None)):
            with self.subTest(payload=payload):
                self.urlopen.return_value = json_response(payload)
                self.assertIsNone(clients.call_llm("問題"))

    def test_http_and_invalid_json_failures_return_none_with_safe_logs(self):
        os.environ["OPENAI_API_KEY"] = "dummy"
        self.urlopen.side_effect = TimeoutError("secret-timeout-details")
        with self.assertLogs(clients.LOGGER, level="WARNING") as logs:
            self.assertIsNone(clients.call_llm("問題"))
        self.assertNotIn("secret-timeout-details", "\n".join(logs.output))
        self.urlopen.side_effect = None
        self.urlopen.return_value = io.BytesIO(b"not JSON")
        with self.assertLogs(clients.LOGGER, level="WARNING"):
            self.assertIsNone(clients.call_llm("問題"))

    def test_models_list_filters_deduplicates_and_follows_encoded_page_tokens(self):
        self.urlopen.side_effect = [json_response({"models": [
            {"name": "models/one", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/embedding", "supportedGenerationMethods": ["embedContent"]}],
            "nextPageToken": "next+/="}), json_response({"models": [
                {"name": "models/one", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/two", "supportedGenerationMethods": ["generateContent"]}]})]
        self.assertEqual(clients.fetch_gemini_models(" dummy "), ["models/one", "models/two"])
        self.assertEqual(self.request_at().method, "GET")
        self.assertEqual(self.request_at().get_header("X-goog-api-key"), "dummy")
        self.assertEqual(parse_qs(urlparse(self.request_at(1).full_url).query), {"pageToken": ["next+/="]})
        self.assertNotIn("dummy", self.request_at(1).full_url)

    def test_models_empty_key_does_not_open_network(self):
        self.assertEqual(clients.fetch_gemini_models(" "), [])
        self.urlopen.assert_not_called()

    def test_models_pagination_errors_return_empty_and_log_only_type(self):
        self.urlopen.side_effect = [json_response({"models": [], "nextPageToken": "same"}),
                                    json_response({"models": [], "nextPageToken": "same"})]
        with self.assertLogs(clients.LOGGER, level="WARNING"):
            self.assertEqual(clients.fetch_gemini_models("dummy"), [])
        self.assertEqual(self.urlopen.call_count, 2)
        self.urlopen.side_effect = URLError("secret-list-error")
        with self.assertLogs(clients.LOGGER, level="WARNING") as logs:
            self.assertEqual(clients.fetch_gemini_models("dummy"), [])
        self.assertNotIn("secret-list-error", "\n".join(logs.output))


if __name__ == "__main__":
    unittest.main()
