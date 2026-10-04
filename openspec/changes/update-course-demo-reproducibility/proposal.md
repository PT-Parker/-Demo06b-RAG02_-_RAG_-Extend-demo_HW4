# Change: Make the course demo reproducible locally

## Why

原程式在啟動時載入向量依賴，無 LLM 時把 prompt 截段當成摘要。介面也會把金鑰與 Gemini 模型寫入全域環境，影響其他 session 或相容 API 設定。

## What Changes

- 在同一個 Streamlit 入口提供免 API、免模型下載的 TF-IDF 詞彙檢索。
- 區分生成答案、來源原文及無命中，保留檔名與片段編號。
- API 使用每次請求的 Gemini 設定，相容端點使用各自的預設值。
- 加入小型虛構資料、CLI／後端／UI／API mock 測試與操作文件。

## Impact

- Affected specs: `course-demo`。
- Affected code: `app/`、展示依賴、README 與 `tests/`。
- 已驗證本機離線 CLI、Streamlit UI 與 mock API；完整向量環境、真實 LLM API 及雲端部署尚未實測。
