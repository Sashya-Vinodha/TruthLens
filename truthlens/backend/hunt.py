import json
from pathlib import Path
from sentence_transformers import SentenceTransformer, util
import numpy as np

doc_path = Path("data/docs_v2.json") 
if not doc_path.exists():
    doc_path = Path("data/docs.json")

with open(doc_path, "r", encoding="utf-8") as f:
    docs = json.load(f)

target_idx = -1
for i, d in enumerate(docs):
    text_lower = d.get("text", "").lower()
    if "valid and reliable" in text_lower and "accountable" in text_lower:
        target_idx = i
        break

if target_idx == -1:
    print("❌ Could not find the golden chunk! The slicer might have split the list in half.")
    exit()

golden_chunk = docs[target_idx]
word_count = len(golden_chunk.get("text", "").split())
parent_section = golden_chunk.get("parent_section", "Unknown")

print("\n" + "="*70)
print("🎯 GOLDEN CHUNK FOUND!")
print(f"Index: {target_idx}")
print(f"Parent Section: {parent_section}")
print(f"Word Count: {word_count}")
print("\n--- CHUNK PREVIEW (First 500 chars) ---")
print(golden_chunk.get("text", "")[:500])
print("---------------------------------------")
print("="*70 + "\n")

print("🧠 Loading Embedder (BAAI/bge-large-en-v1.5)...")
embedder = SentenceTransformer("BAAI/bge-large-en-v1.5")
texts = [d.get("text", "") for d in docs]
doc_embeddings = embedder.encode(texts, convert_to_numpy=True, show_progress_bar=False) 

queries = [
    "What are the seven trustworthiness characteristics in the NIST AI RMF?"
]

for q in queries:
    query_emb = embedder.encode([q], convert_to_numpy=True)
    scores = util.cos_sim(query_emb, doc_embeddings)[0].numpy()
    sorted_indices = np.argsort(scores)[::-1]
    rank = np.where(sorted_indices == target_idx)[0][0] + 1
    score = scores[target_idx]
    
    print(f"Query: '{q}'")
    print(f"Rank: {rank} (Score: {score:.4f})\n")