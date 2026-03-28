# truthlens/backend/app/main.py

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict
import logging

# ---------------------------
# Import your backend modules
# ---------------------------
from . import retriever
from . import generator
from . import verifier as verifier_module
from . import fusion as fusion_module

Verifier = verifier_module.Verifier

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ---------------------------
# FASTAPI APP
# ---------------------------
app = FastAPI(title="TruthLens - RAG Guardrail Prototype")

# 1) Serve static frontend at /static
app.mount("/static",
          StaticFiles(directory="truthlens/frontend/public"),
          name="static")

# 2) Serve index.html at root "/"
@app.get("/", include_in_schema=False)
def root():
    return FileResponse("truthlens/frontend/public/index.html")

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
        # Hard abstain when nothing relevant is found
        return {
            "question": question,
            "answer": "No relevant information found in dataset.",
            "confidence": 0.0,
            "abstain": True,
            "verifier": {},
            "retrieved_docs": []
        }

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

    # Ensure each retrieved doc has a title for the frontend Sources panel.
    retrieved_docs = []
    for doc in docs:
        text = doc.get("text", "")
        retrieved_docs.append({
            "id": doc.get("id"),
            "text": text,
            "title": doc.get("title", text[:60])
        })

    final_confidence = fusion_output.get("confidence", 0.0)
    final_answer = answer
    final_abstain = fusion_output.get("abstain")

    if final_confidence is None:
        final_confidence = 0.0
    if final_abstain is None:
        final_abstain = False

    # Final JSON response
    return {
        "question": question,
        "answer": final_answer,
        "confidence": final_confidence,
        "abstain": final_abstain,
        "verifier": verification,
        "retrieved_docs": retrieved_docs
    }
