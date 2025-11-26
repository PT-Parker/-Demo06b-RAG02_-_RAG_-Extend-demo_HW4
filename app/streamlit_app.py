import os
import streamlit as st

from rag_backend import rag_answer

st.set_page_config(page_title="台股知識 RAG 問答系統", layout="wide")

# 預設模型（可依需求修改，亦可於側邊欄覆寫）；API Key 不預設，避免外洩
DEFAULT_GEMINI_KEY = ""
DEFAULT_GEMINI_MODEL = "models/gemini-2.5-flash"

# 初始化 session state
if "history" not in st.session_state:
    st.session_state["history"] = []
if "gemini_models" not in st.session_state:
    st.session_state["gemini_models"] = []
if "selected_model" not in st.session_state:
    st.session_state["selected_model"] = DEFAULT_GEMINI_MODEL
if "api_key" not in st.session_state:
    st.session_state["api_key"] = DEFAULT_GEMINI_KEY


def fetch_gemini_models(api_key: str):
    """列出具有 generateContent 能力的 Gemini 模型清單。"""
    try:
        import google.generativeai as genai  # type: ignore

        genai.configure(api_key=api_key)
        names = []
        for m in genai.list_models():
            if "generateContent" in getattr(m, "supported_generation_methods", []):
                names.append(m.name)
        return names
    except Exception as exc:
        st.warning(f"無法取得模型清單：{exc}")
        return []


def run_rag(question: str):
    result = rag_answer(question, history=st.session_state["history"])
    st.session_state["history"].append({"question": question, "answer": result["answer"]})
    return result


st.title("台股知識 RAG 問答系統 (Demo06b Extension)")
st.caption("以向量檢索 + LLM 生成方式，示範如何針對台股知識庫進行問答。")

with st.sidebar:
    st.header("說明 / 警語")
    st.markdown(
        "- 僅供課程示範，非投資建議。\n"
        "- 資訊為靜態示例，無即時報價，請以公開資訊觀測站為準。\n"
        "- 若無 API 金鑰，系統會回傳檢索摘要作為草稿。"
    )
    st.divider()
    st.markdown("### 範例問題")
    st.markdown(
        "- 台積電的主要風險是什麼？\n"
        "- 聯發科目前的產品重點有哪些？\n"
        "- 台股常見的財務指標有哪些？"
    )
    st.divider()
    if "api_key" not in st.session_state:
        st.session_state["api_key"] = ""
    api_key_input = st.text_input(
        "Gemini API Key（google.generativeai）",
        type="password",
        value=st.session_state["api_key"],
        help="若留白則改用本地檢索摘要回覆。",
    )
    if api_key_input.strip():
        st.session_state["api_key"] = api_key_input.strip()
        os.environ["GEMINI_API_KEY"] = st.session_state["api_key"]
        os.environ.setdefault("RAG_LLM_MODEL", st.session_state["selected_model"])
    else:
        # 若未輸入，僅維持預設模型，不寫入空金鑰
        os.environ["RAG_LLM_MODEL"] = st.session_state["selected_model"]
    list_models_clicked = st.button("列出可用 Gemini 模型", key="list_models_btn")
    if list_models_clicked:
        if not st.session_state["api_key"]:
            st.warning("請先輸入 Gemini API Key。")
        else:
            st.session_state["gemini_models"] = fetch_gemini_models(st.session_state["api_key"])
    models = st.session_state.get("gemini_models", [])
    if models:
        st.markdown("**可用模型：**")
        default_idx = 0
        if st.session_state["selected_model"] in models:
            default_idx = models.index(st.session_state["selected_model"])
        choice = st.selectbox("選擇模型", models, index=default_idx, key="model_select")
        st.session_state["selected_model"] = choice
        os.environ["RAG_LLM_MODEL"] = choice
        st.code(choice)


question = st.text_area("輸入你想詢問的台股問題", placeholder="例：台股有哪些主要指數？", height=120)
col_run, col_clear = st.columns([1, 1], gap="small")

run_clicked = col_run.button("執行 RAG")
clear_clicked = col_clear.button("清除對話")

if clear_clicked:
    st.session_state["history"] = []
    st.rerun()

if run_clicked:
    if not question.strip():
        st.warning("請先輸入問題再送出。")
    else:
        with st.spinner("檢索與生成中..."):
            result = run_rag(question.strip())

        st.subheader("回答")
        st.write(result["answer"])

        with st.expander("檢索到的文件片段與來源", expanded=False):
            for cite in result["citations"]:
                st.markdown(f"**[{cite['id']}] {cite['source']}**")
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
