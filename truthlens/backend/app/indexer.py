# Required packages:
# pip install faiss-cpu sentence-transformers rank_bm25 numpy

import os
import sys
import json
import pickle
import argparse
import numpy as np
import faiss
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

def main():
    parser = argparse.ArgumentParser(description="TruthLens Indexer")
    parser.add_argument("--docs", type=str, default="data/docs.json", help="Path to input docs JSON")
    parser.add_argument("--out-dir", type=str, default="backend/data", help="Directory to save artifacts")
    args = parser.parse_args()

    # 1. Load Documents
    print(f"[INFO] Loading documents from {args.docs}...")
    if not os.path.exists(args.docs):
        print(f"[ERROR] Input file {args.docs} not found.")
        sys.exit(1)

    try:
        with open(args.docs, 'r', encoding='utf-8') as f:
            docs = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse JSON: {e}")
        sys.exit(1)

    if not docs:
        print("[ERROR] Document list is empty.")
        sys.exit(1)
    
    print(f"[INFO] Loaded {len(docs)} documents.")

    # Ensure output directory exists
    os.makedirs(args.out_dir, exist_ok=True)

    # 2. Build BM25 Index
    print("[INFO] Building BM25 index...")
    # NOTE: Simple whitespace splitting used here. For production, consider using NLTK or spaCy tokenizers.
    tokenized_corpus = [doc.get("text", "").split() for doc in docs]
    bm25 = BM25Okapi(tokenized_corpus)

    bm25_path = os.path.join(args.out_dir, "bm25.pkl")
    with open(bm25_path, "wb") as f:
        pickle.dump(bm25, f)
    print(f"[INFO] Saved BM25 index to {bm25_path}")

    # 3. Build FAISS Index
    print("[INFO] Loading SentenceTransformer model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')

    print("[INFO] Computing document embeddings...")
    texts = [doc.get("text", "") for doc in docs]
    embeddings = model.encode(texts, convert_to_numpy=True)

    print("[INFO] Normalizing embeddings and building FAISS index...")
    faiss.normalize_L2(embeddings)
    
    d = embeddings.shape[1]
    index = faiss.IndexFlatIP(d)  # Inner Product (Cosine similarity on normalized vectors)
    index.add(embeddings)

    faiss_path = os.path.join(args.out_dir, "faiss.index")
    faiss.write_index(index, faiss_path)
    print(f"[INFO] Saved FAISS index to {faiss_path}")

    # 4. Save Raw Docs
    print("[INFO] Saving original documents manifest...")
    docs_path = os.path.join(args.out_dir, "docs.pkl")
    with open(docs_path, "wb") as f:
        pickle.dump(docs, f)
    print(f"[INFO] Saved docs dump to {docs_path}")

    print("[SUCCESS] Indexing complete.")

if __name__ == "__main__":
    main()