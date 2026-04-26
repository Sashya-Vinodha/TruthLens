# truthlens/backend/app/main.py

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict
import logging
from pathlib import Path

# ---------------------------
# Import your backend modules
# ---------------------------
from . import retriever
from . import generator
from . import verifier as verifier_module
from . import fusion as fusion_module
from .utils import ABSTAIN_MESSAGE, topic_match

Verifier = verifier_module.Verifier

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ---------------------------
# FASTAPI APP
# ---------------------------
app = FastAPI(title="TruthLens - RAG Guardrail Prototype")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_PUBLIC = PROJECT_ROOT / "frontend" / "public"

# 1) Serve static frontend at /static
if FRONTEND_PUBLIC.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_PUBLIC)), name="static")

# 2) Serve index.html at root "/"
@app.get("/", include_in_schema=False)
def root():
    index_path = FRONTEND_PUBLIC / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend not available")
    return FileResponse(str(index_path))

# Enable CORS (frontend -> backend communication)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # change later for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# INPUT MODEL
# ---------------------------
class QueryRequest(BaseModel):
    question: str
    k: int = 3


STRICT_SUPPORT_THRESHOLD = 0.65
MIN_RETRIEVAL_SCORE = 0.4


def abstain_response(question: str, retrieved_docs: list[dict] | None = None) -> Dict[str, Any]:
    return {
        "question": question,
        "answer": ABSTAIN_MESSAGE,
        "confidence": 0.0,
        "abstain": True,
        "verifier": {},
        "retrieved_docs": retrieved_docs or []
    }

# ---------------------------
# HEALTH CHECK
# ---------------------------
@app.get("/health")
def health():
    return {"status": "ok"}

# ---------------------------
# MAIN QUERY ENDPOINT
# ---------------------------
@app.post("/query")
def query(req: QueryRequest) -> Dict[str, Any]:
    question = req.question
    k = req.k

    # 1) Retrieve documents
    try:
        docs = retriever.retrieve(question, k=k)
    except Exception as e:
        logger.error(f"Retriever failed: {e}")
        raise HTTPException(status_code=500, detail=f"Retriever error: {e}")

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
        print("🚫 TOPIC MISMATCH - ABSTAINING")
        return abstain_response(question, retrieved_docs)

    best_score = max(float(doc.get("score", 1.0)) for doc in docs)
    if best_score < MIN_RETRIEVAL_SCORE:
        return abstain_response(question, retrieved_docs)

    # 2) Generate answer
    try:
        answer = generator.generate_answer(question, docs)
    except Exception as e:
        logger.error(f"Generator failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generator error: {e}")

    # 3) Verify answer
    try:
        v = Verifier()
        verification = v.verify(answer, docs)
    except Exception as e:
        logger.error(f"Verifier failed: {e}")
        raise HTTPException(status_code=500, detail=f"Verifier error: {e}")

    # 4) Fusion logic
    try:
        fusion_output = fusion_module.fuse(verification)
    except Exception as e:
        logger.error(f"Fusion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Fusion error: {e}")

    final_confidence = fusion_output.get("confidence", 0.0)
    final_answer = answer
    final_abstain = fusion_output.get("abstain")

    if final_confidence is None:
        final_confidence = 0.0
    if final_abstain is None:
        final_abstain = False

    if verification.get("overall_support", 0.0) < STRICT_SUPPORT_THRESHOLD:
        final_abstain = True

    if any(not claim.get("supported", False) for claim in verification.get("claims", [])):
        final_abstain = True

    if final_abstain:
        final_answer = ABSTAIN_MESSAGE
        final_confidence = min(final_confidence, 0.25)

    # Final JSON response
    return {
        "question": question,
        "answer": final_answer,
        "confidence": final_confidence,
        "abstain": final_abstain,
        "verifier": verification,
        "retrieved_docs": retrieved_docs
    }
