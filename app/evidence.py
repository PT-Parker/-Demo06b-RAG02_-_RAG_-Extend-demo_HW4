"""來源原文、生成答案與無命中的共同回傳格式。"""

from typing import Any


def evidence_response(query: str, docs: list[Any], answer: str | None = None) -> dict:
    """Keep excerpts distinct from generation; never echo prompts as an answer."""
    citations = [
        {"id": index, "source": doc.metadata.get("source", "unknown"),
         "chunk_id": doc.metadata.get("chunk_id"), "snippet": doc.page_content}
        for index, doc in enumerate(docs, 1)
    ]
    if not citations:
        answer = "知識庫未找到相關片段，請調整關鍵字或查閱其他來源。"
        mode = "no_match"
    elif not answer or not answer.strip():
        mode = "excerpts"
        answer = "檢索到的來源原文：\n\n" + "\n\n".join(
            f"[{c['id']}] {c['source']}（片段 {c['chunk_id']}）\n{c['snippet']}"
            for c in citations
        )
    else:
        mode = "generated"
        # These are the retrieved sources; listing them is not claim-level validation.
        answer = answer.strip() + "\n\n檢索來源：\n" + "\n".join(
            f"[{c['id']}] {c['source']}" for c in citations
        )
    return {"question": query, "answer": answer, "response_mode": mode,
            "citations": citations,
            "retrieved_chunks": [
                {"source": c["source"], "chunk_id": c["chunk_id"], "text": c["snippet"]}
                for c in citations]}
