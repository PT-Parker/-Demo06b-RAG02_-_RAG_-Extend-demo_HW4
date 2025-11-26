# Project Context

## Purpose
- Build a small retrieval-augmented chatbot that answers students' school reward/discipline questions in conversational Traditional Chinese (Taiwan).
- Run in a notebook/Colab setting with a simple Gradio web UI backed by a prebuilt FAISS vector store and Groq-hosted LLM.

## Tech Stack
- Python 3 in Jupyter/Colab notebooks
- LangChain + langchain-community for retrieval chains
- FAISS vector store loaded from `faiss_db` (downloaded via `gdown` from Google Drive)
- HuggingFace `google/embeddinggemma-300m` embeddings via `huggingface_hub`
- AI Suite client calling Groq's OpenAI-compatible chat models (e.g., `groq:openai/gpt-oss-120b`)
- Gradio for the chat UI
- gdown for asset download

## Project Conventions

### Code Style
- Notebook-first workflow; keep cells concise and focused.
- Use LangChain primitives (FAISS retriever, custom embedding class) and add short clarifying comments where behavior is not obvious.

### Architecture Patterns
- Retrieval-augmented generation: FAISS retriever -> prompt template -> Groq chat completion.
- In-memory chat history per session to keep conversation context.

### Testing Strategy
- Manual verification through the Gradio interface; no automated tests or CI in place yet.

### Git Workflow
- No documented branching or commit conventions; current work happens directly on the notebook.

## Domain Context
- Chatbot acts as a school reward/discipline advisor; responses should stay concise, friendly, and in Traditional Chinese tailored to students.

## Important Constraints
- Requires Groq API key and HuggingFace token (retrieved via `google.colab.userdata` in the notebook).
- Depends on external FAISS index (`faiss_db.zip` from Google Drive) and allows dangerous deserialization when loading.

## External Dependencies
- Groq OpenAI-compatible API (`groq:openai/gpt-oss-120b`)
- HuggingFace Hub (`google/embeddinggemma-300m`)
- Google Drive hosting for `faiss_db.zip`
- Gradio for web UI hosting
