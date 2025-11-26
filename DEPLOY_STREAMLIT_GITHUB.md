# 部署到 GitHub 與 Streamlit Cloud 指南

## 1. 初始化 Git 專案
```bash
git init
git add .
git commit -m "Add Demo06b 台股 RAG app"
```

## 2. 推送到 GitHub
1. 在 GitHub 建立新 repository（可設為 public）。
2. 將遠端加入並推送：
   ```bash
   git remote add origin https://github.com/<your-account>/<repo-name>.git
   git push -u origin main
   ```
3. 檢查檔案已上傳（可在 repo 頁面確認 `app/streamlit_app.py`、`requirements.txt` 等）。

## 3. 建立 Streamlit Cloud App
1. 前往 https://streamlit.io/cloud ，登入後點選 **New app**。
2. 選擇剛才的 GitHub repo 與分支，`Main file path` 填寫 `app/streamlit_app.py`。
3. 在 **Advanced settings → Secrets** 新增需要的金鑰（若有）：
   ```toml
   GROQ_API_KEY = "your_api_key"
   HUGGINGFACEHUB_API_TOKEN = "your_token_if_any"
   RAG_LLM_MODEL = "groq:openai/gpt-oss-120b"  # 可選
   RAG_TOP_K = "4"                             # 可選
   ```
4. 點擊 **Deploy**，等待建置完成。

## 4. 本地驗證
部署前先在本機執行：
```bash
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```
確保可看到回答與引用片段。若無 API key，畫面仍會顯示基於檢索的摘要。

## 5. 注意事項
- corpus 為示範性質，更新內容時請重新部署以重建向量索引。
- 若要改用其他 LLM 服務，可在 `rag_backend.py` 中調整 `RAG_LLM_MODEL` 與 `RAG_OPENAI_BASE_URL`，並將相應金鑰放入 Secrets。
- Streamlit Cloud 會在安裝依賴時使用 `requirements.txt`；若新增套件請同步更新並推送。
