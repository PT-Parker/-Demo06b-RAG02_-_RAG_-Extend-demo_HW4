## Round 1
**User:** 我想把 Demo06b 改成跟台股有關的 RAG 系統。  
**Agent:** 沒問題，我會先閱讀 Demo06b notebook 了解現有 pipeline，再規劃台股專用的知識庫與 UI。

## Round 2
**User:** Notebook 裡用了哪些技術？  
**Agent:** 主要是 HuggingFace Embeddings 搭配 FAISS，LLM 透過 Groq 的 OpenAI 相容介面，還有 Gradio 前端。

## Round 3
**User:** 知識庫要長什麼樣？  
**Agent:** 我會用 Markdown 放市場概覽、產業/指數與代表公司（台積電、聯發科、鴻海），另加常見財務名詞，一檔一主題方便切 chunk。

## Round 4
**User:** 記得加警語，避免被當成投資建議。  
**Agent:** 會在 corpus README、前端 sidebar 與回答中強調僅供教學示範、非即時資訊。

## Round 5
**User:** 檢索與 embedding 要跟 Demo06b 一致嗎？  
**Agent:** 優先沿用 Gemma 300m 前綴設定，若缺 HuggingFace token 就退回 MiniLM，保持可跑性。

## Round 6
**User:** 需要引用來源。  
**Agent:** 我會在 `rag_answer` 回傳 citations（檔名與片段），並在答案末尾列出編號，符合 Demo06b 延伸需求。

## Round 7
**User:** history 要不要保留？  
**Agent:** 會接受可選 history，摘要最近幾輪放進 prompt，但資料來源仍以當次檢索結果為主。

## Round 8
**User:** 如果沒有 API key 呢？  
**Agent:** LLM 呼叫失敗時會回傳檢索摘要作為安全回覆，避免生成幻覺，並在 UI 提示缺少金鑰。

## Round 9
**User:** 向量庫怎麼建？  
**Agent:** 先用 `load_corpus` 讀 Markdown，`RecursiveCharacterTextSplitter` 切 500/120 overlap，再用 FAISS.from_documents 建索引並快取。

## Round 10
**User:** Streamlit 要有哪些區塊？  
**Agent:** 標題 + 警語 sidebar + 輸入框與執行按鈕，主要區塊顯示答案，expander 顯示引用片段，並呈現對話歷程。

## Round 11
**User:** 有沒有範例問題？  
**Agent:** sidebar 會放三個常見問題，幫助使用者快速測試。

## Round 12
**User:** requirements 要列齊。  
**Agent:** 會加入 streamlit、langchain、langchain-community、faiss-cpu、sentence-transformers、huggingface_hub、aisuite[all]。

## Round 13
**User:** README 怎麼寫？  
**Agent:** 中英混合，說明特色、架構、安裝步驟、環境變數、執行方式與 corpus 限制，方便上 GitHub。

## Round 14
**User:** 摘要要 300 字左右。  
**Agent:** 會描述動機、方法、系統設計與貢獻，控制在 250–350 字的正式中文。

## Round 15
**User:** 記得交付部署說明。  
**Agent:** 會提供 Git 初始化、推送到 GitHub、Streamlit Cloud 建立 app 的步驟與注意環境變數。

## Round 16
**User:** 有考慮未來擴充嗎？  
**Agent:** 在專案摘要會建議擴充爬取觀測站資料、加入監控指標與更多公司檔案。

## Round 17
**User:** 可以手動測試嗎？  
**Agent:** `rag_backend.py` 附上簡易主程式可印出回答；Streamlit 執行後即可互動測試。

## Round 18
**User:** 確認文件都在。  
**Agent:** 已生成 corpus、backend、Streamlit、摘要、對話紀錄、README、requirements、部署指南，可直接交付。
