# 2026-10-04 測試與驗證紀錄

## 結果

在 Windows、Python 3.12.14、Streamlit 1.50.0 的專案虛擬環境中執行，共 33 項測試通過，0 failure、0 error、0 skipped。

| 測試類型 | 數量 | 驗證內容 |
| --- | ---: | --- |
| 後端與 CLI | 14 | 詞彙排序、切塊、top-k、來源對應、空白輸入、無命中及回退 |
| API client mock | 16 | Gemini／相容端點格式、模型設定、分頁及失敗回應 |
| Streamlit UI | 3 | 查詢、rerun、清除對話及 session 金鑰設定 |

API 測試使用 mock，不會呼叫外部模型。小型虛構 corpus 用於驗證流程，測試結果不代表真實問答正確率。

## 重現方法

在專案根目錄執行：

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-demo.txt
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

離線 CLI 不需要額外依賴：

```powershell
python -m app.offline_demo "晨星晶片主要風險" --corpus tests/fixtures/corpus --top-k 1 --json
python -m app.offline_demo "火星探測器" --corpus tests/fixtures/corpus --json
```

第一題應回傳 `excerpts`、`chip_company.md` 與「單一客戶集中」原文；第二題應回傳 `no_match` 與空來源列表。沒有安裝 Streamlit 時，UI 測試會標示 skipped，其餘測試可使用 Python 標準函式庫執行。

## 功能與驗證證據

| 證據 | 發現 | 實作與驗證位置 |
| --- | --- | --- |
| 無 LLM 時的回傳內容 | 回應需要區分來源原文與生成內容 | `app/evidence.py`、`tests/test_rag.py` |
| UI 的金鑰與模型設定 | 設定應限制於 session／每次請求 | `app/llm_clients.py`、`tests/test_llm_clients.py`、`tests/test_streamlit.py` |
| 未安裝向量依賴的離線操作 | 離線模式可獨立使用 | 延後載入向量依賴、`app/offline_demo.py`、禁止 offline 呼叫 vector／LLM 的測試 |
| 來源檔名、片段與回應狀態 | UI 和 CLI 使用相同格式 | `rag_answer` 共用入口與後端／UI 測試 |
| 本機瀏覽器查詢 | 顯示 `chip_company.md` 與「單一客戶集中」原文 | synthetic corpus 的實際 Streamlit 操作 |

瀏覽器驗證使用 `tests/fixtures/corpus` 啟動 Streamlit。輸入「晨星晶片主要風險」後，畫面顯示「來源原文片段」、`chip_company.md` 與「單一客戶集中」原文。無命中、rerun 及清除對話另由 AppTest 驗證。

REST 格式依 [Gemini generateContent](https://ai.google.dev/api/generate-content)、[Gemini models](https://ai.google.dev/api/models)、[Groq OpenAI compatibility](https://console.groq.com/docs/openai) 與 [OpenAI Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create) 文件核對。

## 未測範圍與限制

- 完整 LangChain／FAISS／sentence-transformers 環境、embedding 下載、真實 LLM API 與雲端部署尚未實測。
- 離線 TF-IDF 為詞彙檢索，無法保證同義詞、承接上文或只有部分字詞重合的問題能正確處理。
- 向量 top-k 尚未校準相關性門檻；找到片段不代表足以回答問題。
- 來源清單對應檢索片段，尚未評估生成答案的逐句引用或正確率。
- 原始 corpus 為靜態教學資料，未重新核實公司與財務資訊；不提供即時資料。

`requirements-demo.txt` 固定已驗證的 Streamlit 版本；`requirements-demo-lock.txt` 記錄上述 Windows／Python 環境的依賴版本。
