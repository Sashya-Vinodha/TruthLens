from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict
import logging
from pathlib import Path

from . import retriever
from . import generator
from . import verifier as verifier_module
from . import fusion as fusion_module
from .utils import ABSTAIN_MESSAGE, topic_match

Verifier = verifier_module.Verifier

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="TruthLens - RAG Guardrail Prototype")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_PUBLIC = PROJECT_ROOT / "frontend" / "public"

if FRONTEND_PUBLIC.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_PUBLIC)), name="static")

@app.get("/", include_in_schema=False)
def root():
    index_path = FRONTEND_PUBLIC / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend not available")
    return FileResponse(str(index_path))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    question: str
    k: int = 3

# V1.0 Dead Code: Left intentionally for architectural interview discussions
STRICT_SUPPORT_THRESHOLD = 0.65
MIN_RETRIEVAL_SCORE = 0.4

def abstain_response(question: str, retrieved_docs: list[dict] | None = None) -> Dict[str, Any]:
    return {
        "question": question,
        "answer": "I couldn't find relevant information in the dataset. This query appears to be outside the scope of the provided governance documents.",
        "confidence": 0.0,
        "abstain": True,
        "safety_status": "Safe (Out of Scope)", # <-- UPDATED
        "evidence_label": "Out Of Corpus",
        "verifier": {"claims": [], "overall_support": 0.0},
        "retrieved_docs": []
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/query")
def query(req: QueryRequest) -> Dict[str, Any]:
    question = req.question
    k = req.k

    # Global Block for completely out of scope topics
    blocked_keywords = {"elon", "musk", "cake", "recipe", "baking", "tesla", "spacex"}
    if any(kw in question.lower() for kw in blocked_keywords):
        logger.info(f"🚫 Query blocked: '{question}'")
        return abstain_response(question)

    try:
        docs = retriever.retrieve(question, k=k)
    except Exception as e:
        logger.error(f"Retriever failed: {e}")
        return abstain_response(question)

    if not docs:
        return abstain_response(question)

    retrieved_docs = []
    for doc in docs:
        text = doc.get("text", "")
        retrieved_docs.append({
            "id": doc.get("id"),
            "text": text,
            "title": doc.get("title", text[:60])
        })

    doc_texts = [d.get("text", "") for d in docs if d.get("text", "").strip()]

    if len(doc_texts) == 0:
        return abstain_response(question, retrieved_docs)

    if not topic_match(question, doc_texts):
        logger.info("🚫 TOPIC MISMATCH - ABSTAINING")
        return abstain_response(question, retrieved_docs)

    # ==========================================
    # 🧠 GENERATOR BLOCK WITH DEBUG PRINT
    # ==========================================
    try:
        answer = generator.generate_answer(question, docs)
        print(f"\n[DEBUG] RAW GEMINI ANSWER:\n{answer}\n")
    except Exception as e:
        logger.error(f"Generator failed: {e}")
        return abstain_response(question, retrieved_docs)

    # ==========================================
    # ⚖️ VERIFIER BLOCK WITH DEBUG PRINT
    # ==========================================
    try:
        v = Verifier()
        verification = v.verify(answer, docs)
        print(f"[DEBUG] OVERALL SUPPORT SCORE: {verification.get('overall_support')}")
    except Exception as e:
        logger.error(f"Verifier failed: {e}")
        verification = {"claims": [], "overall_support": 0.0, "error": True}

    try:
        fusion_output = fusion_module.fuse(verification)
    except Exception as e:
        logger.error(f"Fusion failed: {e}")
        fusion_output = {"confidence": 0.0, "abstain": True}

    final_confidence = fusion_output.get("confidence", 0.0)
    final_answer = answer

    # ==========================================
    # 🛡️ THE SMART SAFETY & EVIDENCE POLICY
    # ==========================================
    
    # 1. Check for lies
    has_contradiction = any(
        claim.get("nli_label") == "CONTRADICTION" 
        for claim in verification.get("claims", [])
    )

    # 2. Check for explicit textual support
    has_entailment = any(
        claim.get("nli_label") == "ENTAILMENT"
        for claim in verification.get("claims", [])
    )

    # 3. Detect corpus-boundary refusals
    REFUSAL_PATTERNS = [
        "couldn't find relevant information",
        "cannot find relevant information",
        "do not mention",
        "not mentioned in the provided documents",
        "outside the scope of the dataset",
        "not found in the dataset"
    ]

    is_out_of_corpus = any(
        p in final_answer.lower()
        for p in REFUSAL_PATTERNS
    )

    # 4. Categorize Safety and Evidence
    if is_out_of_corpus:
        final_abstain = True
        safety_status = "Safe" 
        evidence_label = "Out Of Corpus"
        retrieved_docs = []    
        final_answer = "I couldn't find relevant information in the dataset. This query appears to be outside the scope of the provided governance documents." # <-- BRUTALLY OVERWRITE THE LLM    

    elif has_contradiction:
        logger.warning("🛑 VERIFIER BLOCKED: Contradiction detected.")
        final_abstain = True
        safety_status = "Blocked (Hallucination Detected)"
        evidence_label = "Contradicted / Unsupported"

        final_answer = (
            "The generated response was blocked. "
            "The system detected claims that directly contradicted "
            "the retrieved evidence, or lacked sufficient factual support."
        )

    else:
        final_abstain = False
        safety_status = "Safe (No Contradictions)"

        if has_entailment:
            evidence_label = "Direct Evidence"
        else:
            evidence_label = "Inferred From Sources"

    return {
        "question": question,
        "answer": final_answer,
        "confidence": round(final_confidence, 4), 
        "abstain": final_abstain,
        "safety_status": safety_status,
        "evidence_label": evidence_label,
        "verifier": verification,
        "retrieved_docs": retrieved_docs
    }