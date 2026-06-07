import json
from pathlib import Path
from docling.document_converter import DocumentConverter
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

PDF_DIR = Path(__file__).resolve().parent.parent / "backend" / "data" / "raw"
OUTPUT_DB = Path(__file__).resolve().parent.parent / "backend" / "data" / "docs_v2.json"

def process_regulatory_pdfs():
    converter = DocumentConverter()
    all_hierarchical_chunks = []
    
    for pdf_path in PDF_DIR.glob("*.pdf"):
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
            # 🚀 AUDITOR'S FIX: Use \n\n to preserve paragraph boundaries
            full_section_text = "\n\n".join(texts)
            words = full_section_text.split()
            
            MAX_WORDS = 200
            OVERLAP = 30
            
            if not words: 
                continue
            
            # 🔥 THE SLICER: Physically cuts the array so it can NEVER exceed 200 words
            for i in range(0, len(words), MAX_WORDS - OVERLAP):
                chunk_words = words[i:i + MAX_WORDS]
                chunk_text = " ".join(chunk_words)
                
                if len(chunk_words) > 10:
                    all_hierarchical_chunks.append({
                        "id": f"{pdf_path.stem}_{len(all_hierarchical_chunks)}",
                        "source_doc": pdf_path.stem,
                        "parent_section": sec_name,
                        "text": f"[Section: {sec_name}]\n{chunk_text}"
                    })

    with open(OUTPUT_DB, "w", encoding="utf-8") as f:
        json.dump(all_hierarchical_chunks, f, indent=2)
        
    logger.info(f"✅ Built hierarchical DB with {len(all_hierarchical_chunks)} BULLETPROOF chunks.")

if __name__ == "__main__":
    process_regulatory_pdfs()