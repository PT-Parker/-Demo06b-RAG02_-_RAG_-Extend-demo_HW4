# GitHub 與 Streamlit 部署指南

預設離線模式不需要 API 金鑰或 embedding 模型。向量模式另外使用 LangChain、FAISS 與 HuggingFace 模型；生成答案時需要 LLM 金鑰。以下命令在專案根目錄執行。

## 本機啟動

需要 Python 3.10+。離線 UI 的安裝與啟動：

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-demo.txt
.venv/Scripts/python.exe -m streamlit run app/streamlit_app.py
```

選取「離線來源檢索」並輸入問題，結果會顯示來源原文、檔名與片段編號。若要使用向量模式，先安裝完整依賴：

```powershell
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m streamlit run app/streamlit_app.py
```

向量模式首次查詢時會建立索引並下載 embedding 模型。未提供金鑰、API 失敗或生成結果為空時，系統顯示檢索到的來源原文。

## 將分支推送到 GitHub

確認目前分支及修改內容：

```powershell
git branch --show-current
git status --short
git diff --check
```

將完成的修改加入 Git 並提交後，可把目前分支推送到既有遠端：

```powershell
git push -u origin HEAD
```

在 GitHub 開啟該分支的 pull request，確認程式、依賴、測試與文件後再合併。不要把 API 金鑰、`.env` 或本機虛擬環境加入提交。

## 設定 Streamlit Community Cloud

1. 登入 [Streamlit Community Cloud](https://share.streamlit.io/)，建立 app。
2. 選擇 GitHub repository 與要展示的分支，入口填入 `app/streamlit_app.py`。
3. 專案根目錄的 `requirements.txt` 會安裝完整向量依賴。若只部署離線展示，可在部署分支把內容改成 `-r requirements-demo.txt`。
4. 向量模式可在 app 的 Secrets 以 TOML 根層級設定 `GEMINI_API_KEY`，或選用 `GROQ_API_KEY`／`OPENAI_API_KEY`；根層級值會成為程式可讀取的環境變數。金鑰不要寫入程式碼。
5. 部署後查詢範例問題，確認來源與回應狀態；再檢查無命中與清除對話流程。

Gemini 模型使用 `RAG_GEMINI_MODEL`；Groq／OpenAI 模型使用 `RAG_LLM_MODEL`。Gemini 預設 `gemini-2.5-flash`，Groq 預設 `openai/gpt-oss-120b`，OpenAI 預設 `gpt-4o-mini`。完整設定見 [README](README.md#啟用原始向量流程)。

平台操作依 Streamlit 官方的 [部署流程](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)、[依賴設定](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies) 與 [Secrets 設定](https://docs.streamlit.io/develop/concepts/connections/secrets-management)。

## 驗證範圍

本機離線 CLI 與 Streamlit UI 已驗證；Community Cloud 部署、完整向量依賴及真實 LLM API 尚未實測。測試方法與結果見 [測試與驗證紀錄](report/2026-10-04_reproducibility_report.md)。
