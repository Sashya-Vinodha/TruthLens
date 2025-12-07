import json
import pickle
import os

# Read the JSON file
json_path = "truthlens/data/docs.json"
pkl_path = "truthlens/data/docs.pkl"

with open(json_path, "r", encoding="utf-8") as f:
    docs = json.load(f)

# Convert id format from "doc_001" to "DOC_0", "DOC_1", etc. (if needed)
# Or keep the original IDs - adjust based on your preference
for i, doc in enumerate(docs):
    # Option 1: Use sequential DOC_0, DOC_1, DOC_2...
    doc["id"] = f"DOC_{i}"
    
    # Option 2: Keep original IDs (comment out line above, uncomment below)
    # pass

print(f"Loaded {len(docs)} documents from {json_path}")

# Save as pickle
with open(pkl_path, "wb") as f:
    pickle.dump(docs, f)

print(f"Saved to {pkl_path}")
print(f"Sample doc: {docs[0]}")