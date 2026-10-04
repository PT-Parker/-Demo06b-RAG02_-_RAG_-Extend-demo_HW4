"""Streamlit 文件檢索介面，支援離線與向量模式。"""

import streamlit as st

try:
    from app.rag_backend import rag_answer
    from app.llm_clients import fetch_gemini_models
except ModuleNotFoundError:  # direct script path outside the project root
    from rag_backend import rag_answer
    from llm_clients import fetch_gemini_models

st.set_page_config(page_title="台股知識 RAG 問答系統", layout="wide")

# 預設模型（可依需求修改，亦可於側邊欄覆寫）；API Key 不預設，避免外洩
DEFAULT_GEMINI_KEY = ""
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"

# 初始化 session state
if "history" not in st.session_state:
    st.session_state["history"] = []
if "gemini_models" not in st.session_state:
    st.session_state["gemini_models"] = []
if "selected_model" not in st.session_state:
    st.session_state["selected_model"] = DEFAULT_GEMINI_MODEL
if "api_key" not in st.session_state:
    st.session_state["api_key"] = DEFAULT_GEMINI_KEY


def run_rag(question: str):
    result = rag_answer(question, history=st.session_state["history"],
                        retrieval_mode=st.session_state["retrieval_mode"],
                        gemini_api_key=st.session_state["api_key"].strip() or None,
                        gemini_model=st.session_state["selected_model"])
    st.session_state["history"].append({"question": question, "answer": result["answer"]})
    st.session_state["last_result"] = result
    return result


st.title("台股知識檢索與問答")
st.caption("檢索知識庫文件，查看回答與來源片段。")

with st.sidebar:
    st.radio("檢索模式", ["offline", "vector"], key="retrieval_mode",
             format_func=lambda mode: "離線來源檢索（免 API）" if mode == "offline" else "向量檢索 + LLM（需完整依賴）")
    st.header("使用說明")
    st.markdown(
        "- 知識庫使用靜態示例，未提供即時報價。\n"
        "- 離線模式檢索來源原文；向量模式搭配 LLM 產生回答。"
    )
    st.divider()
    st.markdown("### 範例問題")
    st.markdown(
        "- 台積電的主要風險是什麼？\n"
        "- 範例資料中的聯發科產品重點有哪些？\n"
        "- 台股常見的財務指標有哪些？"
    )
    st.divider()
    st.text_input(
        "Gemini API Key",
        type="password",
        key="api_key",
        help="只保留於此 session；留白時使用 GEMINI_API_KEY 環境變數。離線模式不使用金鑰。",
        disabled=st.session_state["retrieval_mode"] == "offline",
    )
    list_models_clicked = st.button("列出可用 Gemini 模型", key="list_models_btn",
                                   disabled=st.session_state["retrieval_mode"] == "offline")
    if list_models_clicked:
        if not st.session_state["api_key"]:
            st.warning("請先輸入 Gemini API Key。")
        else:
            try:
                st.session_state["gemini_models"] = fetch_gemini_models(st.session_state["api_key"])
                if not st.session_state["gemini_models"]:
                    st.warning("未取得可用模型，請確認金鑰、連線與服務狀態。")
            except (OSError, ValueError, KeyError):
                st.warning("無法取得模型清單，請確認金鑰、網路與服務狀態。")
    models = st.session_state.get("gemini_models", [])
    if models:
        st.markdown("**可用模型：**")
        default_idx = 0
        if st.session_state["selected_model"] in models:
            default_idx = models.index(st.session_state["selected_model"])
        choice = st.selectbox("選擇模型", models, index=default_idx, key="model_select")
        st.session_state["selected_model"] = choice
        st.code(choice)
    else:
        st.text_input("Gemini 模型", key="selected_model",
                      disabled=st.session_state["retrieval_mode"] == "offline")


question = st.text_area("輸入你想詢問的台股問題", placeholder="例：台股有哪些主要指數？", height=120)
col_run, col_clear = st.columns([1, 1], gap="small")

run_clicked = col_run.button("查詢", key="query_btn")
clear_clicked = col_clear.button("清除對話", key="clear_btn")

if clear_clicked:
    st.session_state["history"] = []
    st.session_state.pop("last_result", None)
    st.rerun()

if run_clicked:
    if not question.strip():
        st.warning("請先輸入問題再送出。")
    else:
        try:
            with st.spinner("檢索中..."):
                result = run_rag(question.strip())
        except (ImportError, OSError, ValueError) as exc:
            st.error(f"無法完成查詢：{exc}。可先使用離線來源檢索模式。")
            st.stop()

if "last_result" in st.session_state:
    result = st.session_state["last_result"]
    st.subheader("查詢結果")
    labels = {"excerpts": "來源原文片段", "generated": "LLM 生成回答",
              "no_match": "未找到相關片段"}
    st.caption(labels[result["response_mode"]])
    st.write(result["answer"])

    with st.expander("檢索到的文件片段與來源", expanded=False):
        for cite in result["citations"]:
            st.markdown(f"**[{cite['id']}] {cite['source']} · 片段 {cite['chunk_id']}**")
            st.write(cite["snippet"])
            st.divider()

st.divider()
st.subheader("對話歷程")
if st.session_state["history"]:
    for turn in st.session_state["history"]:
        with st.chat_message("user"):
            st.write(turn["question"])
        with st.chat_message("assistant"):
            st.write(turn["answer"])
else:
    st.info("尚無對話紀錄。")
