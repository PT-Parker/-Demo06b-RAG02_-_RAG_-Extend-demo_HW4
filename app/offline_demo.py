"""Markdown 詞彙檢索展示，免 API 或模型下載。"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
import sys

try:
    from .evidence import evidence_response
except ImportError:  # streamlit run / direct script
    from evidence import evidence_response

DEFAULT_CORPUS = Path(__file__).resolve().parents[1] / "data" / "tw_stock_corpus"


@dataclass(frozen=True)
class Chunk:
    page_content: str
    metadata: dict


def tokenize(text: str) -> Counter:
    """Latin words and overlapping Chinese bigrams; not semantic embeddings."""
    tokens = []
    for part in re.findall(r"[a-z0-9]+|[\u3400-\u9fff]+", text.lower()):
        if re.fullmatch(r"[\u3400-\u9fff]+", part):
            tokens.extend(part[i:i + 2] for i in range(len(part) - 1))
            if len(part) == 1:
                tokens.append(part)
        else:
            tokens.append(part)
    return Counter(tokens)


def load_chunks(corpus: Path = DEFAULT_CORPUS, size: int = 500, overlap: int = 100) -> list[Chunk]:
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("chunk size must be positive and 0 <= overlap < size")
    if not corpus.is_dir():
        raise FileNotFoundError(f"知識庫目錄不存在：{corpus}")
    chunks = []
    for path in sorted(corpus.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        text = path.read_text(encoding="utf-8").strip()
        for index, start in enumerate(range(0, len(text), size - overlap)):
            chunks.append(Chunk(text[start:start + size], {"source": path.name, "chunk_id": index}))
            if start + size >= len(text):
                break
    if not chunks:
        raise ValueError("知識庫沒有可讀取的 Markdown 內容。")
    return chunks


def retrieve(query: str, chunks: list[Chunk], top_k: int = 4) -> list[Chunk]:
    """Rank by TF-IDF cosine. Zero lexical overlap returns no documents."""
    if not query.strip():
        raise ValueError("問題不可空白。")
    if not 1 <= top_k <= 10:
        raise ValueError("top_k 必須介於 1 與 10。")
    if not chunks:
        return []
    counts = [tokenize(c.page_content) for c in chunks]
    df = Counter(token for count in counts for token in count)
    idf = {token: math.log((1 + len(chunks)) / (1 + frequency)) + 1 for token, frequency in df.items()}

    def vector(count):
        weighted = {token: (1 + math.log(n)) * idf[token] for token, n in count.items() if token in idf}
        norm = math.sqrt(sum(value * value for value in weighted.values()))
        return {token: value / norm for token, value in weighted.items()} if norm else {}

    q = vector(tokenize(query))
    ranked = []
    for index, count in enumerate(counts):
        score = sum(q.get(token, 0) * weight for token, weight in vector(count).items())
        if score > 0:
            ranked.append((score, index))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [chunks[index] for _, index in ranked[:top_k]]


def answer(query: str, corpus: Path = DEFAULT_CORPUS, top_k: int = 4) -> dict:
    result = evidence_response(query, retrieve(query, load_chunks(corpus), top_k))
    result["retrieval_mode"] = "offline_lexical_tfidf"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--json", action="store_true", help="Print structured result")
    args = parser.parse_args()
    try:
        result = answer(args.question, args.corpus, args.top_k)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"錯誤：{exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result["answer"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
