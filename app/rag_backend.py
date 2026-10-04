"""
簡易台股 RAG 後端，從 Demo06b notebook 重構而來。
支援離線詞彙檢索與向量檢索，回傳答案及來源片段。

功能：
- 載入本地 Markdown 知識庫，分割成 chunk 並建立 FAISS 向量索引。
- 使用 HuggingFace Embeddings（預設為 google/embeddinggemma-300m，無權杖時退回 MiniLM）。
- 提供 retriever 以及 rag_answer 函式，回傳答案與引用片段。

環境變數：
- TW_STOCK_CORPUS_DIR：自訂知識庫路徑，預設 data/tw_stock_corpus。
- RAG_TOP_K：檢索數量，預設 4。
- GROQ_API_KEY / OPENAI_API_KEY：呼叫 LLM 用，未提供時列出檢索原文片段。
- RAG_LLM_MODEL：LLM 名稱，預設 groq:openai/gpt-oss-120b。
- RAG_OPENAI_BASE_URL：OpenAI 相容端點，Groq 預設 https://api.groq.com/openai/v1。
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.documents import Document
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.vectorstores import FAISS

try:
    from .evidence import evidence_response
    from .llm_clients import call_llm
except ImportError:
    from evidence import evidence_response
    from llm_clients import call_llm

# 參數與預設值
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS_DIR = PROJECT_ROOT / "data" / "tw_stock_corpus"
SYSTEM_PROMPT = (
    "你是台股知識助理，請根據提供的文件片段回答問題，"
    "用繁體中文簡潔作答並附上引用來源編號；若資料不足請坦白說明。"
)
DEFAULT_MODEL = "groq:openai/gpt-oss-120b"


def _resolve_corpus_dir(corpus_dir: Optional[str] = None) -> Path:
    return Path(corpus_dir or os.getenv("TW_STOCK_CORPUS_DIR", DEFAULT_CORPUS_DIR)).resolve()


def load_corpus(corpus_dir: Optional[str] = None) -> List[Document]:
    """讀取 corpus 目錄並切成 chunk，附上來源檔名以供引用。"""
    from langchain_core.documents import Document
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    target_dir = _resolve_corpus_dir(corpus_dir)
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=120)
    docs: List[Document] = []

    for path in sorted(target_dir.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        text = path.read_text(encoding="utf-8")
        for idx, chunk in enumerate(splitter.split_text(text)):
            docs.append(
                Document(
                    page_content=chunk.strip(),
                    metadata={"source": path.name, "chunk_id": idx},
                )
            )

    if not docs:
        raise FileNotFoundError(f"未找到任何知識檔案，請確認路徑：{target_dir}")

    return docs


def _build_embedding_model() -> HuggingFaceEmbeddings:
    """優先使用 Demo06b 的 Gemma embedding，缺 token 時退回 MiniLM。"""
    from langchain_community.embeddings import HuggingFaceEmbeddings
    import logging

    class EmbeddingGemmaEmbeddings(HuggingFaceEmbeddings):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(model_name="google/embeddinggemma-300m",
                             encode_kwargs={"normalize_embeddings": True}, **kwargs)

        def embed_documents(self, texts: List[str]) -> List[List[float]]:
            return super().embed_documents([f"title: none | text: {t}" for t in texts])

        def embed_query(self, text: str) -> List[float]:
            return super().embed_query(f"task: search result | query: {text}")

    hf_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
    try:
        kwargs = {}
        if hf_token:
            kwargs["huggingfacehub_api_token"] = hf_token
        return EmbeddingGemmaEmbeddings(**kwargs)
    except Exception as exc:  # pragma: no cover - 僅作防護
        logging.warning("Gemma embedding 建立失敗，改用 MiniLM：%s", exc)
        return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


def build_vector_store(docs: List[Document]) -> FAISS:
    from langchain_community.vectorstores import FAISS
    embeddings = _build_embedding_model()
    return FAISS.from_documents(docs, embeddings)


def get_retriever(vs: FAISS, top_k: int = 5):
    return vs.as_retriever(search_kwargs={"k": top_k})


@lru_cache(maxsize=1)
def _lazy_vector_store(corpus_dir: str) -> FAISS:
    docs = load_corpus(corpus_dir)
    return build_vector_store(docs)


def _ensure_retriever(top_k: Optional[int] = None):
    vs = _lazy_vector_store(str(_resolve_corpus_dir()))
    k = top_k if top_k is not None else _retrieval_k()
    return vs, get_retriever(vs, k)


def _retrieval_k() -> int:
    try:
        k = int(os.getenv("RAG_TOP_K", "4"))
    except ValueError as exc:
        raise ValueError("RAG_TOP_K 必須為 1 到 10 的整數。") from exc
    if not 1 <= k <= 10:
        raise ValueError("RAG_TOP_K 必須為 1 到 10 的整數。")
    return k


def _retrieve_docs(retriever: Any, query: str) -> List[Document]:
    """兼容新版 Retriever 介面（invoke）與舊版 get_relevant_documents。"""
    if callable(getattr(retriever, "invoke", None)):
        result = retriever.invoke(query)
        if isinstance(result, list):
            return result
    if callable(getattr(retriever, "get_relevant_documents", None)):
        return retriever.get_relevant_documents(query)
    raise AttributeError("retriever 物件缺少檢索方法")


def _format_context(docs: List[Document]) -> str:
    lines = []
    for idx, doc in enumerate(docs, start=1):
        src = doc.metadata.get("source", "unknown")
        lines.append(f"[{idx}] 來源: {src}\n{doc.page_content}")
    return "\n\n".join(lines)


def _format_history(history: Optional[List[Dict[str, str]]]) -> str:
    if not history:
        return "（無對話紀錄）"
    pairs = []
    for turn in history[-5:]:
        q = turn.get("question") or turn.get("user") or ""
        a = turn.get("answer") or turn.get("agent") or ""
        pairs.append(f"Q: {q}\nA: {a}")
    return "\n".join(pairs)


def _call_llm(prompt: str, gemini_api_key: Optional[str] = None,
              gemini_model: Optional[str] = None) -> Optional[str]:
    return call_llm(prompt, gemini_api_key=gemini_api_key, gemini_model=gemini_model)


def rag_answer(query: str, history: Optional[List[Dict[str, str]]] = None,
               retrieval_mode: str = "vector", gemini_api_key: Optional[str] = None,
               gemini_model: Optional[str] = None) -> Dict[str, Any]:
    """傳回答案與來源。offline 使用詞彙檢索且不呼叫 LLM。"""
    if not query.strip():
        raise ValueError("問題不可空白。")
    if retrieval_mode == "offline":
        try:
            from .offline_demo import answer
        except ImportError:
            from offline_demo import answer
        return answer(query, _resolve_corpus_dir(), top_k=_retrieval_k())
    if retrieval_mode != "vector":
        raise ValueError("retrieval_mode 必須為 offline 或 vector。")
    _, retriever = _ensure_retriever(_retrieval_k())
    docs = _retrieve_docs(retriever, query)

    if not docs:
        result = evidence_response(query, [])
        result["retrieval_mode"] = "vector"
        return result

    context_block = _format_context(docs)
    prompt = (
        f"使用者問題：{query}\n\n"
        f"對話紀錄：\n{_format_history(history)}\n\n"
        f"以下是檢索到的資料片段，請整理重點回答並標註引用編號：\n{context_block}\n\n"
        "回覆格式：先給出中文答案，最後列出參考來源的編號與檔名。"
    )
    result = evidence_response(query, docs, _call_llm(prompt, gemini_api_key, gemini_model))
    result["retrieval_mode"] = "vector"
    return result


if __name__ == "__main__":  # 簡易手動測試
    demo_q = "台積電的主要風險是什麼？"
    result = rag_answer(demo_q)
    print(result["answer"])
