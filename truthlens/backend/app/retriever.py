# retriever.py — simple fallback retriever (no FAISS)

import os
import pickle
import re
from typing import Dict, List

from sentence_transformers import SentenceTransformer, util

# Load docs at startup
# Load docs at startup
SIMILARITY_THRESHOLD = 0.5
MIN_KEYWORD_LENGTH = 4

# Load docs at startup
DOC_PATH = "truthlens/data/docs.pkl"

if os.path.exists(DOC_PATH):
    with open(DOC_PATH, "rb") as f:
        DOCS = pickle.load(f)
else:
    DOCS = [
        {"id": "DOC_0", "text": "Alexander Fleming discovered penicillin in 1928."},
        {"id": "DOC_1", "text": "Insulin is a peptide hormone."},
    ]

# Embedding model
embedder = SentenceTransformer("all-MiniLM-L6-v2")

def _has_keyword_overlap(question: str, doc_text: str) -> bool:
    """Require at least one non-trivial keyword overlap to keep the doc."""
    keywords = {
        token
        for token in re.findall(r"\w+", question.lower())
        if len(token) >= MIN_KEYWORD_LENGTH
    }
    if not keywords:
        return True  # fallback: allow doc when no useful keywords
    lowered = doc_text.lower()
    return any(keyword in lowered for keyword in keywords)

def retrieve(query: str, k: int = 3) -> List[Dict]:
    """Simple cosine-similarity retriever (no FAISS)."""

    # Compute query embedding
    q_emb = embedder.encode(query, convert_to_tensor=True)

    # Compute doc embeddings
    doc_texts = [d["text"] for d in DOCS]
    doc_embs = embedder.encode(doc_texts, convert_to_tensor=True)

    # Compute similarities
    sims = util.cos_sim(q_emb, doc_embs)[0]

    # Top-k indices sorted by similarity
    topk = sims.topk(min(k, len(DOCS))).indices.tolist()

    if not topk:
        return []

    scores = [float(sims[idx]) for idx in topk]
    print("QUERY:", query)
    print("SIMILARITY SCORES:", scores)

    best_score = scores[0]
    if best_score < SIMILARITY_THRESHOLD:
        return []

    strict_docs: List[Dict] = []
    for idx in topk:
        doc = DOCS[idx]
        score = float(sims[idx])
        if score < SIMILARITY_THRESHOLD:
            continue
        if not _has_keyword_overlap(query, doc.get("text", "")):
            continue
        strict_docs.append(doc)

    return strict_docs[:k]
    return [DOCS[i] for i in topk]
