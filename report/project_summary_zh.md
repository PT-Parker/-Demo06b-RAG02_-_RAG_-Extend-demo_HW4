# 專案摘要

本專案將 Demo06b RAG 課程範例延伸為台股知識展示，使用 Markdown 知識庫檢索資料，並在 Streamlit 顯示回應與來源。預設離線模式免 API 金鑰與模型下載，另保留 FAISS 向量檢索及 LLM 生成流程。

## 系統設計

- 知識庫：`data/tw_stock_corpus/` 包含市場概覽、產業與指數、公司介紹及財務名詞，資料為靜態示例。
- 離線檢索：以 Latin 詞與中文相鄰雙字建立 TF-IDF，依餘弦相似度排序，回傳來源原文。
- 向量檢索：分割 Markdown，使用 HuggingFace embedding 建立 FAISS 索引；優先嘗試 Gemma，建立失敗時改用 MiniLM。
- 生成與回退：Gemini 優先，另支援 Groq／OpenAI 相容端點；沒有生成內容時顯示來源原文。
- 來源呈現：兩種模式使用共用入口與回傳格式，區分生成答案、來源原文及無命中，保留檔名和片段編號。
- 設定管理：介面金鑰存於目前 session，API 設定隨請求傳入，避免寫入全域環境變數。

## 執行方式

離線 CLI 只需要 Python 3.10+：

```powershell
python -m app.offline_demo "晨星晶片主要風險" --corpus tests/fixtures/corpus --top-k 1 --json
```

離線 UI 使用 Streamlit：

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-demo.txt
.venv/Scripts/python.exe -m streamlit run app/streamlit_app.py
```

向量模式另安裝 `requirements.txt`。設定與操作細節見 [README](../README.md)。

## 測試與後續方向

33 項測試通過，包括 14 項後端／CLI、16 項 API mock 和 3 項 Streamlit UI 測試。測試驗證來源對應、失敗回應及操作流程，尚未評估真實問答正確率。

目前未實測完整向量依賴、真實 API 或雲端部署。後續可擴充知識庫、建立相關性門檻與問答評估集，衡量檢索品質及生成答案的來源一致性。詳見 [測試與驗證紀錄](2026-10-04_reproducibility_report.md)。
