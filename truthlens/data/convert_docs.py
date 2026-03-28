import json
import pickle
import os

def convert_docs():
    """
    Converts data.txt into docs.json and then docs.pkl
    Each line in data.txt becomes a separate document
    """
    
    input_file = "truthlens/data/data.txt"
    json_output = "truthlens/data/docs.json"
    pkl_output = "truthlens/data/docs.pkl"
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"❌ Error: {input_file} not found!")
        return
    
    print(f"📖 Reading {input_file}...")
    
    # Read data.txt and split by lines
    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # Create documents list
    docs = []
    for idx, line in enumerate(lines):
        line = line.strip()
        if line:  # Skip empty lines
            doc = {
                "id": f"DOC_{idx}",
                "text": line
            }
            docs.append(doc)
    
    print(f"✓ Loaded {len(docs)} documents from data.txt")
    
    # Save as JSON
    with open(json_output, "w", encoding="utf-8") as f:
        json.dump(docs, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Saved {json_output}")
    
    # Save as pickle
    with open(pkl_output, "wb") as f:
        pickle.dump(docs, f)
    
    print(f"✓ Saved {pkl_output}")
    print(f"\n📊 Summary:")
    print(f"  Total documents: {len(docs)}")
    print(f"  Sample doc: {docs[0]}")
    
    return docs

if __name__ == "__main__":
    print("=" * 60)
    print("Converting data.txt → docs.json → docs.pkl")
    print("=" * 60)
    convert_docs()
    print("=" * 60)
    print("✅ Conversion complete!")
    print("=" * 60)