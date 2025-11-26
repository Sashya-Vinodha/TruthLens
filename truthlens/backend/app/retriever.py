# retriever.py — simple fallback retriever (no FAISS)

import pickle
import os
from typing import List, Dict
from sentence_transformers import SentenceTransformer, util

# Load docs at startup
DOC_PATH = "truthlens/backend/data/docs.pkl"

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

    return [DOCS[i] for i in topk]
