"""Streamlit 介面的離線操作回歸測試。"""

import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "corpus"
HAS_STREAMLIT = importlib.util.find_spec("streamlit") is not None


@unittest.skipUnless(HAS_STREAMLIT, "Install requirements-demo.txt for Streamlit UI checks")
class StreamlitOfflineTests(unittest.TestCase):
    def setUp(self):
        from streamlit.testing.v1 import AppTest
        self.env = patch.dict(os.environ, {"TW_STOCK_CORPUS_DIR": str(FIXTURE), "RAG_TOP_K": "2"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.app = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=10).run()
        self.assertEqual(len(self.app.exception), 0)

    def test_default_offline_query_and_result_survive_rerun_then_clear(self):
        self.assertEqual(self.app.radio[0].value, "offline")
        self.app.text_area[0].set_value("晨星晶片主要風險")
        self.app.button(key="query_btn").click().run()
        self.assertEqual(len(self.app.exception), 0)
        result = self.app.session_state["last_result"]
        self.assertEqual(result["response_mode"], "excerpts")
        self.assertEqual(result["citations"][0]["source"], "chip_company.md")
        self.assertIn("單一客戶集中", result["answer"])
        self.app.run()
        self.assertEqual(self.app.session_state["last_result"], result)
        self.app.button(key="clear_btn").click().run()
        self.assertEqual(self.app.session_state["history"], [])
        self.assertNotIn("last_result", self.app.session_state)

    def test_unrelated_and_blank_questions_show_clear_outcome(self):
        self.app.text_area[0].set_value("火星探測器")
        self.app.button(key="query_btn").click().run()
        self.assertEqual(self.app.session_state["last_result"]["response_mode"], "no_match")
        self.app.text_area[0].set_value(" ")
        self.app.button(key="query_btn").click().run()
        self.assertTrue(any("請先輸入問題" in w.value for w in self.app.warning))
        self.assertEqual(len(self.app.session_state["history"]), 1)

    def test_session_key_can_be_cleared_without_changing_process_environment(self):
        initial = {name: os.environ.get(name) for name in ["GEMINI_API_KEY", "RAG_LLM_MODEL"]}
        self.app.radio[0].set_value("vector").run()
        self.app.text_input(key="api_key").set_value("synthetic-test-key").run()
        self.assertEqual(self.app.session_state["api_key"], "synthetic-test-key")
        self.app.text_input(key="api_key").set_value("").run()
        self.assertEqual(self.app.session_state["api_key"], "")
        self.assertEqual({name: os.environ.get(name) for name in initial}, initial)


if __name__ == "__main__":
    unittest.main()
