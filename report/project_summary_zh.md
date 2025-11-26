# 專案摘要（中文）

## 目標與動機
- 台股資訊分散且更新頻繁，初學者與學生難以快速取得可靠重點。本專案將 Demo06b 的 RAG 教學範例改造成台股題材，提供可延伸的學術示範。

## 系統設計
- 知識庫：`data/tw_stock_corpus/` 內含市場概覽、產業與指數、台積電/聯發科/鴻海公司介紹，以及財務名詞解釋；均為靜態 Markdown 檔。
- 檢索：使用 `RecursiveCharacterTextSplitter` 分割後，以 HuggingFace Embeddings（預設 `google/embeddinggemma-300m`，無權杖時退回 MiniLM）建構 FAISS 向量庫並提供 retriever。
- 生成：根據檢索片段組合提示，呼叫 OpenAI 相容端點（預設 Groq 模型）。若無金鑰則回傳檢索摘要以避免幻覺。
- 引用呈現：RAG 回覆包含來源檔名與片段，並於 Streamlit 展開區顯示，方便驗證與除錯。

## 執行方式
1. `pip install -r requirements.txt`
2. 設定（可選）環境變數：`HUGGINGFACEHUB_API_TOKEN`、`GROQ_API_KEY`/`OPENAI_API_KEY`、`TW_STOCK_CORPUS_DIR`、`RAG_TOP_K`。
3. `streamlit run app/streamlit_app.py`，輸入台股問題即可獲得 RAG 回答。

## 限制與延伸
- 目前 corpus 規模小且為示範性摘要，未含即時報價與完整財報。可擴充為自動爬取公開資訊觀測站或新聞稿。
- LLM 端點以 Groq/OpenAI 相容介面為主，可替換為本地模型或其他 API。
- 建議後續增加單元測試與監控指標（命中率、引用品質）以追蹤 RAG 表現。
