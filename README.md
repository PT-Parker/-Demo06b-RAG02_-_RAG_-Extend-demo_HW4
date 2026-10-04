# Demo06b 台股知識 RAG 課程展示

將 Markdown 知識庫切成片段，檢索後在 Streamlit 顯示回答與來源。預設離線展示免 API 金鑰、免下載 embedding 模型；向量模式保留 FAISS + LLM 流程。

## 先跑免安裝展示

需要 Python 3.10+；以下命令在專案根目錄執行。離線 CLI 只用標準函式庫：

```powershell
python -m app.offline_demo "晨星晶片主要風險" --corpus tests/fixtures/corpus --top-k 1 --json
python -m app.offline_demo "火星探測器" --corpus tests/fixtures/corpus --json
python -m unittest discover -s tests -p "test_rag.py" -v
```

第一題應回傳 `response_mode: excerpts`、`chip_company.md` 與原文「單一客戶集中」；第二題應回傳 `no_match` 和空來源列表。`tests/fixtures/corpus` 為小型虛構資料，測試流程與來源對應，無法推論真實台股回答正確率。

原始教學知識庫也可直接檢索：

```powershell
python -m app.offline_demo "台積電的主要風險是什麼？" --json
```

這會列出靜態來源原文，並非 LLM 生成答案或摘要。

## 使用同一個 Streamlit 介面

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-demo.txt
.venv/Scripts/python.exe -m streamlit run app/streamlit_app.py
```

預設選取「離線來源檢索」。輸入問題、按「查詢」，查看原文與檔名；按「清除對話」清除目前結果與歷程。側邊欄可切換至向量模式，兩種模式使用同一個 `rag_answer` 入口及來源格式。畫面會明示原文、生成或無命中狀態。介面輸入的 Gemini 金鑰只存於該 session，清空欄位可移除；留白時仍會讀取服務環境的 `GEMINI_API_KEY`。

以虛構資料展示介面：

```powershell
$env:TW_STOCK_CORPUS_DIR = (Resolve-Path tests/fixtures/corpus).Path
.venv/Scripts/python.exe -m streamlit run app/streamlit_app.py
```

測試完整的 CLI、來源回傳、API 設定與 UI 操作：

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

`requirements-demo.txt` 固定已驗證的 Streamlit 版本；`requirements-demo-lock.txt` 記錄 Python 3.12 / Windows 環境的完整安裝版本。沒有 Streamlit 時，UI 測試會標示 skipped；其他測試可使用標準函式庫執行。API 測試使用 mock，不會呼叫外部模型。

## 啟用原始向量流程

```powershell
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m streamlit run app/streamlit_app.py
```

向量模式需要 LangChain、FAISS、sentence-transformers，第一次執行會嘗試下載 HuggingFace embedding 模型。優先嘗試 Gemma，建立失敗才退回 MiniLM。完整向量環境與真實 API 尚未實測；目前已驗證離線檢索、UI 和 API mock 流程。

| 設定 | 用途 | 預設或行為 |
| --- | --- | --- |
| `TW_STOCK_CORPUS_DIR` | 自訂 Markdown 知識庫 | `data/tw_stock_corpus`，兩種模式共用 |
| `RAG_TOP_K` | 共用入口的檢索片段上限 | 4，允許整數 1–10 |
| `GEMINI_API_KEY` | Gemini 生成金鑰 | 介面 session 金鑰優先；離線模式不使用 |
| `RAG_GEMINI_MODEL` | 後端 Gemini 模型 | `gemini-2.5-flash`；UI 有獨立模型欄位 |
| `GROQ_API_KEY` | Groq 備援金鑰 | Gemini 未產生內容時嘗試 |
| `OPENAI_API_KEY` | OpenAI 備援金鑰 | 無 Groq 金鑰時使用 OpenAI 端點 |
| `RAG_OPENAI_BASE_URL` | 自訂相容 API 端點 | Groq / OpenAI 各使用自己的預設 URL |
| `RAG_LLM_MODEL` | Groq / OpenAI 模型 | Groq: `openai/gpt-oss-120b`；OpenAI: `gpt-4o-mini` |
| `HUGGINGFACEHUB_API_TOKEN` | 原始 embedding 權杖設定 | 只在向量模式使用 |

Gemini 模型與 Groq/OpenAI 模型分開設定。無金鑰、空白生成結果或 API 失敗時，回傳檢索原文，且不把提示詞或歷程冒充摘要。

## 資料與驗證限制

- 原始 corpus 為靜態課程資料，公司、財務數字及產業描述未重新查證，未提供即時資訊。
- 離線檢索使用 Latin 詞與中文相鄰雙字的 TF-IDF 餘弦排序，屬詞彙檢索；共同字詞不等於問題已被資料回答，也不理解承接上文的追問。
- 向量模式沿用 top-k 檢索，未校準相關性門檻；有結果不代表相關或足夠。
- 來源清單對應檢索到的片段，未驗證生成答案的每句主張、引用編號或正確率。小型 synthetic 測試不能證明實務品質。

## 檔案入口

| 路徑 | 內容 |
| --- | --- |
| `app/rag_backend.py` | 共用入口、原始向量流程與提示組合 |
| `app/offline_demo.py` | 標準函式庫詞彙檢索與 CLI |
| `app/evidence.py` | 原文 / 生成 / 無命中的來源回傳格式 |
| `app/llm_clients.py` | 每次請求的 Gemini / 相容 API 設定 |
| `app/streamlit_app.py` | 同一 UI 的模式切換、來源與歷程 |
| `tests/` | 小型虛構 corpus 與行為回歸測試 |
| `report/` | 原始摘要及 2026 年補強驗證紀錄 |

## 更新紀錄

2026-10-04：新增離線詞彙檢索、來源回傳狀態、每次請求的 API 設定與回歸測試。測試環境、33 項測試結果與未測範圍見 [測試與驗證紀錄](report/2026-10-04_reproducibility_report.md)。
