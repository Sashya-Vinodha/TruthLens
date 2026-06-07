import json
import pickle
from pathlib import Path
from docling.document_converter import DocumentConverter
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "backend" / "data"
PDF_DIR = OUTPUT_DIR / "raw"

def process_regulatory_pdfs():
    converter = DocumentConverter()
    all_hierarchical_chunks = []
    
    if not PDF_DIR.exists():
        logger.error(f"❌ Raw directory does not exist at {PDF_DIR}")
        return

    pdf_files = list(PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        logger.error(f"❌ No PDFs found in {PDF_DIR}")
        return
    
    for pdf_path in pdf_files:
        logger.info(f"📄 Processing: {pdf_path.name}")
        doc = converter.convert(pdf_path).document
        
        sections = {}
        current_section = "General"
        sections[current_section] = []
        
        for item in doc.texts:
            if item.label == "section_header":
                current_section = item.text.strip()
                if current_section not in sections:
                    sections[current_section] = []
            elif item.label in ["text", "list_item", "figure_caption"]:
                sections[current_section].append(item.text.strip())
                
        for sec_name, texts in sections.items():
            # Preserve paragraph boundaries
            full_section_text = "\n\n".join(texts)
            words = full_section_text.split()
            
            MAX_WORDS = 200
            OVERLAP = 30
            
            if not words: 
                continue
            
            # THE SLICER: Overlapping chunk generation
            for i in range(0, len(words), MAX_WORDS - OVERLAP):
                chunk_words = words[i:i + MAX_WORDS]
                chunk_text = " ".join(chunk_words)
                
                if len(chunk_words) > 10:
                    all_hierarchical_chunks.append({
                        "id": f"{pdf_path.stem}_{len(all_hierarchical_chunks)}",
                        "title": f"[{sec_name}] {pdf_path.stem}",
                        "source_doc": pdf_path.stem,
                        "parent_section": sec_name,
                        "text": f"[Section: {sec_name}]\n{chunk_text}"
                    })

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Save JSON
    json_path = OUTPUT_DIR / "docs.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_hierarchical_chunks, f, indent=2)
        
    # Save Pickle (Required for the FAISS indexer)
    pkl_path = OUTPUT_DIR / "docs.pkl"
    with open(pkl_path, "wb") as f:
        pickle.dump(all_hierarchical_chunks, f)
        
    logger.info(f"✅ Built hierarchical DB with {len(all_hierarchical_chunks)} BULLETPROOF chunks.")

if __name__ == "__main__":
    process_regulatory_pdfs()
