# Demo06b 台股 RAG 系統 (Streamlit 版)

Retrieval-Augmented Generation demo focused on Taiwan stocks, refactored from the original Demo06b notebook into reusable Python modules + Streamlit UI.

## Features / 特色
- 本地 Markdown 台股知識庫，FAISS 向量檢索搭配 HuggingFace Embeddings（預設 Gemma，無權杖時退回 MiniLM）。
- RAG 回答附引用來源編號與片段，便於驗證與除錯。
- Streamlit 介面支援即問即答與對話歷程檢視，內含使用警語與範例問題。

## Project Structure
- `app/rag_backend.py`：載入 corpus、建立向量庫與 `rag_answer` 主流程。
- `app/streamlit_app.py`：Streamlit 入口，呼叫後端並顯示答案與引用。
- `data/tw_stock_corpus/`：台股示例知識庫與 README。
- `report/abstract_zh_300chars.md`：中文 300 字摘要。
- `logs/agent_conversation_log.md`：開發對話紀錄。
- `DEPLOY_STREAMLIT_GITHUB.md`：部署到 GitHub / Streamlit Cloud 指南。

## Setup
1. Python 3.10+ 環境。
2. 安裝依賴：
   ```bash
   pip install -r requirements.txt
   ```
3. （可選）設定環境變數：
   - `HUGGINGFACEHUB_API_TOKEN`：使用 `google/embeddinggemma-300m` 需要的權杖；缺省將改用 MiniLM。
   - **Gemini 首選**：`GEMINI_API_KEY`（預設模型 `gemini-1.5-flash`）。也可在 Streamlit 側邊欄直接輸入，程式會自動設定。
   - **其他相容端點**：`GROQ_API_KEY` 或 `OPENAI_API_KEY` + `RAG_OPENAI_BASE_URL`、`RAG_LLM_MODEL`，作為 Gemini 失敗時的備援。
   - `TW_STOCK_CORPUS_DIR`：自訂知識庫路徑。
   - `RAG_TOP_K`、`RAG_LLM_MODEL`：檢索數量與模型名稱（若使用 Gemini，可改為 `gemini-1.5-pro` 等）。

## Run Locally
```bash
streamlit run app/streamlit_app.py
```
介面將顯示輸入框與引用片段展開區；若無 API 金鑰仍可看到基於檢索的摘要回答。

## Data Notes
- 內建 corpus 為教學示例，涵蓋市場概覽、產業與三家代表公司，以及常見財務名詞。
- 所有內容均非即時資訊，僅供學術示範與程式設計作業，非投資建議。

## Background
- 原始來源：`【Demo06b】RAG02_打造_RAG_系統.ipynb` (LangChain + FAISS + Groq)。
- 本專案將 notebook 重構為可重複使用的模組，並加入引用顯示與 Streamlit 前端。
