import os
import json
import pickle
import re
import fitz  # PyMuPDF
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parents[1]
OUTPUT_DIR = PROJECT_ROOT / "backend" / "data"
RAW_DATA_DIR = OUTPUT_DIR / "raw"

def parse_pdf_to_chunks(file_path: Path, source_prefix: str, max_words: int = 150) -> list[dict]:
    print(f"📖 Extracting text from {file_path.name} with PyMuPDF...")
    
    # PyMuPDF naturally ignores kerning spaces and extracts clean text natively
    doc = fitz.open(file_path)
    full_text = []
    
    for page in doc:
        text = page.get_text("text")
        if text:
            # Clean up standard hyphens at the end of lines
            text = re.sub(r'-\n', '', text)
            full_text.append(text)
            
    # Squash remaining visual line breaks
    clean_text = re.sub(r'\s+', ' ', " ".join(full_text)).strip()
    
    # Split strictly into sentences
    sentences = re.split(r'(?<=[.!?])\s+', clean_text)
    
    chunks = []
    current_chunk = []
    word_count = 0
    chunk_idx = 0
    
    for sentence in sentences:
        if not sentence.strip():
            continue
            
        sentence_words = sentence.strip().split()
        if word_count + len(sentence_words) > max_words and current_chunk:
            combined_text = " ".join(current_chunk)
            chunks.append({
                "id": f"{source_prefix}_{chunk_idx}",
                "title": f"{source_prefix} - {combined_text[:50].strip()}...",
                "text": combined_text
            })
            chunk_idx += 1
            current_chunk = [current_chunk[-1]]
            word_count = len(current_chunk[0].split())
            
        current_chunk.append(sentence.strip())
        word_count += len(sentence_words)
        
    if current_chunk:
        combined_text = " ".join(current_chunk)
        chunks.append({
            "id": f"{source_prefix}_{chunk_idx}",
            "title": f"{source_prefix} - {combined_text[:50].strip()}...",
            "text": combined_text
        })
        
    return chunks

def run_pipeline():
    print(f"🎯 Target output directory set to: {OUTPUT_DIR}")
    if not RAW_DATA_DIR.exists():
        print(f"❌ Error: Raw directory does not exist at {RAW_DATA_DIR}")
        return
        
    pdf_files = list(RAW_DATA_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"❌ Error: No PDFs found in {RAW_DATA_DIR}")
        return
        
    all_chunks = []
    for pdf_path in pdf_files:
        prefix = pdf_path.stem[:8].upper().replace(".", "_")
        all_chunks.extend(parse_pdf_to_chunks(pdf_path, prefix))
        
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    json_path = OUTPUT_DIR / "docs.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2)
        
    pkl_path = OUTPUT_DIR / "docs.pkl"
    with open(pkl_path, "wb") as f:
        pickle.dump(all_chunks, f)
        
    print(f"✅ Clean database successfully generated with {len(all_chunks)} chunks!")

if __name__ == "__main__":
    run_pipeline()