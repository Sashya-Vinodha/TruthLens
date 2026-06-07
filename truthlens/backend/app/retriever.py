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
    class BM25Okapi:
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

from sentence_transformers import SentenceTransformer, CrossEncoder, util
from .utils import (
    build_query_variants,
    content_tokens,
    clean_text,
    keyword_overlap,
    rewrite_query_locally,
    decompose_query_with_gemini,
)

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# 🚀 FIX: Pointing to the NEW intelligent database!
DOC_CANDIDATES = [
    Path(__file__).resolve().parent.parent / "data" / "docs_v2.json",
    Path(__file__).resolve().parent.parent / "data" / "docs.json" # Added fallback just in case
]
SIMILARITY_THRESHOLD = 0.48

DOCS: List[Dict] = []
_EMBEDDER: SentenceTransformer | None = None
_RERANKER: CrossEncoder | None = None
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
                logger.info("Loaded %s documents", len(DOCS))
                return DOCS
        except Exception as exc:
            logger.warning("Failed to load docs: %s", exc)
    DOCS = []
    return DOCS


def _get_embedder() -> SentenceTransformer | None:
    global _EMBEDDER
    if _EMBEDDER is not None:
        return _EMBEDDER
    try:
        _EMBEDDER = SentenceTransformer("BAAI/bge-large-en-v1.5")
        return _EMBEDDER
    except Exception as exc:
        _EMBEDDER = None
        return None

def _get_reranker() -> CrossEncoder | None:
    global _RERANKER
    if _RERANKER is not None:
        return _RERANKER
    try:
        logger.info("🧠 Loading Cross-Encoder Reranker...")
        _RERANKER = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", max_length=512)
        return _RERANKER
    except Exception as exc:
        logger.warning(f"Failed to load Reranker: {exc}")
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
        
        # 🔥 OPTIMIZATION: Trust BGE-Large semantic intelligence over raw keywords
        combined = 0.70 * semantic_scores + 0.20 * bm25_scores + 0.10 * lexical_scores
    else:
        combined = 0.8 * bm25_scores + 0.2 * lexical_scores

    return combined


def _dedupe_docs(docs: Sequence[Dict | str]) -> List[Dict]:
    seen = set()
    deduped: List[Dict] = []
    for doc in docs:
        if isinstance(doc, str):
            doc = {"text": doc}
        doc_id = doc.get("id") or doc.get("text", "")
        if doc_id in seen:
            continue
        seen.add(doc_id)
        deduped.append(doc)
    return deduped


def retrieve(query: str, k: int = 10) -> List[Dict]:
    blocked_terms = {"elon", "musk", "cake", "recipe", "baking"}
    if any(t in query.lower() for t in blocked_terms):
        return []

    docs = _load_docs()
    if not docs:
        return []

    bm25 = _get_bm25(docs)
    embedder = _get_embedder()
    doc_embeddings = _get_doc_embeddings(docs, embedder)

    decomposed_queries = decompose_query_with_gemini(query)
    logger.info(f"🤖 Agent decomposed query into: {decomposed_queries}")

    reranker = _get_reranker()
    all_ranked_docs = []
    
    for sub_query in decomposed_queries:
        query_variants = build_query_variants(sub_query)
        if not query_variants:
            query_variants = [sub_query]

        sub_combined_scores = np.zeros(len(docs), dtype=float)
        for variant in query_variants:
            scores = _score_variant(variant, docs, bm25, embedder, doc_embeddings)
            sub_combined_scores = np.maximum(sub_combined_scores, scores)

        # 🚀 STAGE 4: Fetch Top 30 Candidates
        # 🚀 OPTIMIZATION: Expand Candidate Window from 30 to 100 for Cross-Encoder processing
        candidate_indices = list(np.argsort(sub_combined_scores)[::-1][:100])
        
        # Inject dense score for the audit
        candidate_docs = []
        for idx in candidate_indices:
            score = float(sub_combined_scores[idx])
            if score >= 0.20:
                d = dict(docs[idx])
                d["dense_score"] = score
                candidate_docs.append(d)

        # 📍 STAGE 1 AUDIT
        print("\n" + "="*60)
        print("📍 STAGE 1: INITIAL_RETRIEVAL_TOP_20")
        for i, doc in enumerate(candidate_docs[:20]):
            score_val = round(doc.get('dense_score', 0.0), 4)
            print(f"[{i+1}] Score: {score_val} | Section: {doc.get('parent_section', 'Unknown')}")
            print(f"Text: {doc.get('text', '')[:100].replace(chr(10), ' ')}...")
            
            if "valid and reliable" in doc.get("text", "").lower():
                print(f"   🎯 FOUND TRUSTWORTHINESS CHUNK IN STAGE 1 (Rank: {i+1}, Score: {score_val})")
        print("="*60 + "\n")

        # 🚀 STAGE 5: Cross-Encoder Reranking
        if reranker and candidate_docs:
            cross_inputs = [[sub_query, doc.get("text", "")] for doc in candidate_docs]
            cross_scores = reranker.predict(cross_inputs)
            
            for idx, doc in enumerate(candidate_docs):
                doc["cross_score"] = float(cross_scores[idx])
            
            candidate_docs = sorted(candidate_docs, key=lambda x: x["cross_score"], reverse=True)
        else:
            for doc in candidate_docs:
                 doc["cross_score"] = doc.get("dense_score", 0.0)

        # 📍 STAGE 2 AUDIT
        print("\n" + "-"*60)
        print("📍 STAGE 2: POST_RERANK_TOP_10")
        for i, doc in enumerate(candidate_docs[:10]):
            score_val = round(doc.get('cross_score', 0.0), 4)
            print(f"[{i+1}] Score: {score_val} | Section: {doc.get('parent_section', 'Unknown')}")
            print(f"Text: {doc.get('text', '')[:100].replace(chr(10), ' ')}...")
            
            if "valid and reliable" in doc.get("text", "").lower():
                print(f"   🎯 FOUND TRUSTWORTHINESS CHUNK IN STAGE 2 (Rank: {i+1}, Score: {score_val})")
        print("-"*60 + "\n")

        # 🚀 STAGE 6: Context Expansion
        top_k_for_subquery = candidate_docs[:max(k, 1)]
        for doc in top_k_for_subquery:
            parent_section = doc.get("parent_section")
            if parent_section and parent_section not in doc.get("text", ""):
                doc["text"] = f"[Section: {parent_section}]\n{doc['text']}"
            
            doc.setdefault("title", doc.get("text", "")[:60])
            doc["score"] = round(doc.get("cross_score", 0.0), 4)
            all_ranked_docs.append(doc)

    final_docs = _dedupe_docs(all_ranked_docs)

    # 📍 STAGE 3 AUDIT: THE EXACT HANDOFF
    print("\n" + "="*80)
    print("📍 STAGE 3: FINAL DOCS SENT TO GENERATOR")
    for i, doc in enumerate(final_docs[:max(k, len(decomposed_queries) * 2)]):
        print(
            f"[{i+1}] {doc.get('parent_section', 'Unknown')} | "
            f"Score: {doc.get('score', 0.0)} | "
            f"Text: {doc.get('text', '')[:120].replace(chr(10), ' ')}..."
        )
    print("="*80 + "\n")

    if final_docs:
        return final_docs[:max(k, len(decomposed_queries) * 2)]

    return []