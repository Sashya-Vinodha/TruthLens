"""Hybrid retriever with safe query rewriting and lazy model loading."""

from __future__ import annotations

import json
import logging
import pickle
from pathlib import Path
from typing import Dict, List, Sequence

import numpy as np

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    class BM25Okapi:  # type: ignore[override]
        def __init__(self, tokenized_corpus):
            self.tokenized_corpus = tokenized_corpus

        def get_scores(self, query_tokens):
            query_terms = set(query_tokens)
            if not query_terms:
                return np.zeros(len(self.tokenized_corpus), dtype=float)

            scores = []
            for doc_tokens in self.tokenized_corpus:
                doc_terms = set(doc_tokens)
                overlap = len(query_terms & doc_terms)
                scores.append(overlap / max(1, len(query_terms)))
            return np.asarray(scores, dtype=float)

from sentence_transformers import SentenceTransformer, util

from .utils import (
    build_query_variants,
    content_tokens,
    clean_text,
    keyword_overlap,
    rewrite_query_locally,
)

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DOC_CANDIDATES = [
    PROJECT_ROOT / "truthlens" / "data" / "docs.pkl",
    PROJECT_ROOT / "truthlens" / "backend" / "data" / "docs.pkl",
    PROJECT_ROOT / "truthlens" / "data" / "docs.json",
    PROJECT_ROOT / "data" / "docs.json",
]

SIMILARITY_THRESHOLD = 0.28

DOCS: List[Dict] = []
_EMBEDDER: SentenceTransformer | None = None
_DOC_EMBEDDINGS = None
_BM25: BM25Okapi | None = None


def _load_docs() -> List[Dict]:
    global DOCS
    if DOCS:
        return DOCS

    for path in DOC_CANDIDATES:
        if not path.exists():
            continue

        try:
            if path.suffix == ".pkl":
                with path.open("rb") as handle:
                    DOCS = pickle.load(handle)
            else:
                with path.open("r", encoding="utf-8") as handle:
                    DOCS = json.load(handle)
            if DOCS:
                logger.info("Loaded %s documents from %s", len(DOCS), path)
                return DOCS
        except Exception as exc:
            logger.warning("Failed to load docs from %s: %s", path, exc)

    DOCS = [
        {"id": "DOC_0", "text": "The Companies Act, 2013, governs the incorporation, responsibilities, and dissolution of companies in India."},
        {"id": "DOC_1", "text": "Alexander Fleming discovered penicillin in 1928."},
    ]
    return DOCS


def _get_embedder() -> SentenceTransformer | None:
    global _EMBEDDER
    if _EMBEDDER is not None:
        return _EMBEDDER

    try:
        _EMBEDDER = SentenceTransformer("all-MiniLM-L6-v2")
        return _EMBEDDER
    except Exception as exc:
        logger.warning("SentenceTransformer unavailable: %s", exc)
        _EMBEDDER = None
        return None


def _get_bm25(docs: Sequence[Dict]) -> BM25Okapi:
    global _BM25
    if _BM25 is not None:
        return _BM25

    tokenized_corpus = [content_tokens(clean_text(doc.get("text", ""))) for doc in docs]
    _BM25 = BM25Okapi(tokenized_corpus)
    return _BM25


def _get_doc_embeddings(docs: Sequence[Dict], embedder: SentenceTransformer | None):
    global _DOC_EMBEDDINGS
    if _DOC_EMBEDDINGS is not None:
        return _DOC_EMBEDDINGS

    if embedder is None:
        return None

    texts = [clean_text(doc.get("text", "")) for doc in docs]
    embeddings = embedder.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    _DOC_EMBEDDINGS = embeddings
    return _DOC_EMBEDDINGS


def _normalize_scores(values: np.ndarray) -> np.ndarray:
    if values.size == 0:
        return values
    minimum = float(values.min())
    maximum = float(values.max())
    if abs(maximum - minimum) < 1e-8:
        return np.zeros_like(values, dtype=float)
    return (values - minimum) / (maximum - minimum)


def _score_variant(query: str, docs: Sequence[Dict], bm25: BM25Okapi, embedder: SentenceTransformer | None, doc_embeddings):
    query = clean_text(query)
    query_tokens = content_tokens(query)
    if not query_tokens:
        return np.zeros(len(docs), dtype=float)

    bm25_scores = np.asarray(bm25.get_scores(query_tokens), dtype=float)
    bm25_scores = _normalize_scores(bm25_scores)

    lexical_scores = np.asarray(
        [keyword_overlap(query, clean_text(doc.get("text", ""))) for doc in docs],
        dtype=float,
    )

    if embedder is not None and doc_embeddings is not None:
        query_embedding = embedder.encode([query], convert_to_numpy=True, show_progress_bar=False)
        semantic_scores = util.cos_sim(query_embedding, doc_embeddings)[0].cpu().numpy().astype(float)
        semantic_scores = _normalize_scores(semantic_scores)
        combined = 0.8 * semantic_scores + 0.15 * bm25_scores + 0.05 * lexical_scores
    else:
        combined = 0.8 * bm25_scores + 0.2 * lexical_scores

    return combined


def _dedupe_docs(docs: Sequence[Dict]) -> List[Dict]:
    seen = set()
    deduped: List[Dict] = []
    for doc in docs:
        doc_id = doc.get("id") or doc.get("text", "")
        if doc_id in seen:
            continue
        seen.add(doc_id)
        deduped.append(doc)
    return deduped


def retrieve(query: str, k: int = 3) -> List[Dict]:
    """Hybrid retriever that combines rewrite, expansion, BM25, and embeddings."""

    docs = _load_docs()
    if not docs:
        return []

    bm25 = _get_bm25(docs)
    embedder = _get_embedder()
    doc_embeddings = _get_doc_embeddings(docs, embedder)

    query_variants = build_query_variants(query)
    if not query_variants:
        query_variants = [query]

    combined_scores = np.zeros(len(docs), dtype=float)
    for variant in query_variants:
        scores = _score_variant(variant, docs, bm25, embedder, doc_embeddings)
        combined_scores = np.maximum(combined_scores, scores)

    ranked_indices = list(np.argsort(combined_scores)[::-1][: max(k, 1)])
    ranked_docs: List[Dict] = []

    for idx in ranked_indices:
        score = float(combined_scores[idx])
        if score < SIMILARITY_THRESHOLD:
            continue
        doc = dict(docs[idx])
        doc.setdefault("title", doc.get("text", "")[:60])
        doc["score"] = round(score, 4)
        ranked_docs.append(doc)

    if ranked_docs:
        return _dedupe_docs(ranked_docs)[:k]

    lexical_fallback = []
    for doc in docs:
        overlap = keyword_overlap(clean_text(rewrite_query_locally(query)), clean_text(doc.get("text", "")))
        if overlap >= 0.35:
            fallback_doc = dict(doc)
            fallback_doc.setdefault("title", fallback_doc.get("text", "")[:60])
            fallback_doc["score"] = round(float(overlap), 4)
            lexical_fallback.append((overlap, fallback_doc))

    lexical_fallback.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in lexical_fallback[:k]]
