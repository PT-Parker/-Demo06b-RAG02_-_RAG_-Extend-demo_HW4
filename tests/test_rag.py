"""離線檢索與來源回傳的行為回歸測試。"""

from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from app.evidence import evidence_response
from app.offline_demo import Chunk, answer, load_chunks, retrieve
from app import rag_backend

FIXTURE = Path(__file__).parent / "fixtures" / "corpus"
ROOT = Path(__file__).resolve().parents[1]


class OfflineRetrievalTests(unittest.TestCase):
    def test_chinese_and_english_queries_find_expected_source(self):
        chunks = load_chunks(FIXTURE)
        cases = [("晨星晶片主要風險", "chip_company.md"), ("EPS earnings", "finance_terms.md")]
        for query, expected in cases:
            with self.subTest(query=query):
                self.assertEqual(retrieve(query, chunks, 1)[0].metadata["source"], expected)

    def test_readme_and_empty_files_are_not_indexed(self):
        chunks = load_chunks(FIXTURE)
        self.assertEqual(len(chunks), 2)
        self.assertFalse(any("README_ONLY_SENTINEL" in c.page_content for c in chunks))

    def test_no_overlap_returns_no_match_and_no_citations(self):
        result = answer("火星探測器", FIXTURE)
        self.assertEqual(result["response_mode"], "no_match")
        self.assertEqual(result["citations"], [])

    def test_chunk_overlap_and_source_identity_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            corpus = Path(folder)
            (corpus / "long.md").write_text("abcdefghijk", encoding="utf-8")
            chunks = load_chunks(corpus, size=6, overlap=2)
            self.assertEqual([c.page_content for c in chunks], ["abcdef", "efghij", "ijk"])
            self.assertEqual([c.metadata["chunk_id"] for c in chunks], [0, 1, 2])

    def test_ties_are_deterministic_and_top_k_limits_results(self):
        chunks = [Chunk("EPS earnings", {"source": f"{i}.md", "chunk_id": 0}) for i in range(3)]
        self.assertEqual([c.metadata["source"] for c in retrieve("EPS", chunks, 2)], ["0.md", "1.md"])

    def test_bad_input_and_missing_empty_corpus_fail_clearly(self):
        with self.assertRaises(ValueError):
            retrieve("   ", load_chunks(FIXTURE))
        with self.assertRaises(ValueError):
            retrieve("EPS", load_chunks(FIXTURE), 0)
        with self.assertRaises(ValueError):
            load_chunks(FIXTURE, size=10, overlap=10)
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                load_chunks(Path(folder))
            with self.assertRaises(FileNotFoundError):
                load_chunks(Path(folder) / "missing")

    def test_cli_json_can_be_run_from_another_working_directory(self):
        import json
        with tempfile.TemporaryDirectory() as folder:
            run = subprocess.run([sys.executable, str(ROOT / "app" / "offline_demo.py"), "晨星晶片風險",
                                  "--corpus", str(FIXTURE), "--top-k", "1", "--json"],
                                 cwd=folder, encoding="utf-8", capture_output=True, check=True,
                                 env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        result = json.loads(run.stdout)
        self.assertEqual(result["citations"][0]["source"], "chip_company.md")
        self.assertEqual(result["response_mode"], "excerpts")


class BackendResponseTests(unittest.TestCase):
    def setUp(self):
        self.docs = load_chunks(FIXTURE)
        self.retriever = Mock()
        self.retriever.invoke.return_value = self.docs[:1]

    def test_offline_common_entry_never_calls_vector_or_llm(self):
        with patch.dict(os.environ, {"TW_STOCK_CORPUS_DIR": str(FIXTURE), "RAG_TOP_K": "1"}), \
             patch.object(rag_backend, "_ensure_retriever", side_effect=AssertionError("vector called")), \
             patch.object(rag_backend, "_call_llm", side_effect=AssertionError("LLM called")):
            result = rag_backend.rag_answer("晨星晶片風險", retrieval_mode="offline")
        self.assertEqual(result["response_mode"], "excerpts")
        self.assertEqual(len(result["citations"]), 1)

    def test_missing_llm_returns_original_excerpt_without_prompt_or_history(self):
        with patch.object(rag_backend, "_ensure_retriever", return_value=(None, self.retriever)), \
             patch.object(rag_backend, "_call_llm", return_value=None):
            result = rag_backend.rag_answer("晨星晶片風險", history=[{"question": "HISTORY_SENTINEL", "answer": "old"}])
        self.assertEqual(result["response_mode"], "excerpts")
        self.assertIn(self.docs[0].page_content, result["answer"])
        self.assertNotIn("HISTORY_SENTINEL", result["answer"])
        self.assertNotIn("回覆格式", result["answer"])

    def test_generated_answer_keeps_exact_source_and_does_not_claim_validation(self):
        result = evidence_response("question", self.docs, "  已生成答案 [1]  ")
        self.assertEqual(result["response_mode"], "generated")
        self.assertIn("檢索來源：", result["answer"])
        for cite, doc in zip(result["citations"], self.docs):
            self.assertEqual(cite["snippet"], doc.page_content)
            self.assertEqual(cite["source"], doc.metadata["source"])
            self.assertEqual(cite["chunk_id"], doc.metadata["chunk_id"])

    def test_vector_empty_result_skips_generation_and_keeps_mode(self):
        self.retriever.invoke.return_value = []
        with patch.object(rag_backend, "_ensure_retriever", return_value=(None, self.retriever)), \
             patch.object(rag_backend, "_call_llm", side_effect=AssertionError("LLM called")):
            result = rag_backend.rag_answer("火星探測器")
        self.assertEqual(result["response_mode"], "no_match")
        self.assertEqual(result["retrieval_mode"], "vector")

    def test_session_gemini_config_is_forwarded_per_request(self):
        with patch.object(rag_backend, "_ensure_retriever", return_value=(None, self.retriever)), \
             patch.object(rag_backend, "_call_llm", return_value="生成答案") as call:
            rag_backend.rag_answer("晨星晶片風險", gemini_api_key="test-key", gemini_model="test-model")
        self.assertEqual(call.call_args.args[1:], ("test-key", "test-model"))

    def test_bad_mode_empty_query_and_invalid_top_k_fail_before_models(self):
        with self.assertRaises(ValueError):
            rag_backend.rag_answer(" ")
        with self.assertRaises(ValueError):
            rag_backend.rag_answer("EPS", retrieval_mode="unknown")
        for value in ["0", "11", "not-a-number"]:
            with self.subTest(value=value), patch.dict(os.environ, {"RAG_TOP_K": value}), \
                 patch.object(rag_backend, "_ensure_retriever", side_effect=AssertionError("vector called")):
                with self.assertRaises(ValueError):
                    rag_backend.rag_answer("EPS")

    def test_modern_and_legacy_retriever_interfaces(self):
        modern = Mock()
        modern.invoke.return_value = self.docs
        modern.get_relevant_documents.side_effect = AssertionError("deprecated method called")
        self.assertEqual(rag_backend._retrieve_docs(modern, "EPS"), self.docs)
        legacy = type("Legacy", (), {"get_relevant_documents": lambda _, q: self.docs})()
        self.assertEqual(rag_backend._retrieve_docs(legacy, "EPS"), self.docs)


if __name__ == "__main__":
    unittest.main()
