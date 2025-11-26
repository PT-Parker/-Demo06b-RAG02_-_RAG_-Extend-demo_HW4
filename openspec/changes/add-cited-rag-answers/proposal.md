# Change: Add cited RAG answers

## Why
- Current chatbot replies do not show where information comes from, reducing student trust and making it hard to verify retrieval quality.
- Missing citations make it difficult to debug or improve the FAISS dataset coverage.

## What Changes
- Add response formatting that surfaces retrieved document titles/identifiers and snippets as citations alongside each answer.
- Render citations in the Gradio UI so students can see the supporting sources.
- Provide a polite fallback when retrieval yields no relevant documents instead of guessing.

## Impact
- Affected specs: rag-advisor
- Affected code: RAG notebook (retriever/prompt formatting, Gradio UI)
