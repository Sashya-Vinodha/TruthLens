import re
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer, util
from transformers import pipeline
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
NLI_MODEL_NAME = "typeform/distilbert-base-uncased-mnli"  # lighter & stable


class Verifier:
    def __init__(self):
        logger.info("Loading embedding model...")
        self.embed_model = SentenceTransformer(EMBED_MODEL_NAME)

        logger.info("Loading NLI model...")
        self.nli_pipe = pipeline(
            "text-classification",
            model=NLI_MODEL_NAME,
            device=-1  # keep CPU for stability
        )

    def _split_into_sentences(self, text: str) -> List[str]:
        sents = re.split(r'(?<=[.?!])\s+', text.strip())
        return [s.strip() for s in sents if s.strip()] or [text.strip()]

    def _best_doc_sentence(self, claim: str, doc_text: str):
        doc_sents = self._split_into_sentences(doc_text)

        claim_emb = self.embed_model.encode(claim, convert_to_tensor=True)
        doc_embs = self.embed_model.encode(doc_sents, convert_to_tensor=True)

        sims = util.cos_sim(claim_emb, doc_embs).cpu().numpy().flatten()

        best_idx = int(sims.argmax())
        return doc_sents[best_idx], float(sims[best_idx])

    def verify(self, generated_text: str, retrieved_docs: List[Any]) -> Dict[str, Any]:

        # Normalize docs
        norm_docs = []
        for d in retrieved_docs:
            if isinstance(d, dict):
                norm_docs.append({
                    "id": d.get("id"),
                    "text": d.get("text", ""),
                    "title": d.get("title", d.get("text", "")[:50])
                })
            else:
                norm_docs.append({
                    "id": None,
                    "text": str(d),
                    "title": str(d)[:50]
                })

        claims = re.split(r'(?<=[.?!])\s+', generated_text)
        claims = [c.strip() for c in claims if c.strip()]

        results = []
        total_score = 0.0

        for claim in claims:

            best_sim = 0.0
            best_sent = ""
            best_doc_idx = None
            best_doc_id = None
            best_title = None

            # 🔍 Find best matching doc sentence
            for i, doc in enumerate(norm_docs):
                sent, sim = self._best_doc_sentence(claim, doc["text"])
                if sim > best_sim:
                    best_sim = sim
                    best_sent = sent
                    best_doc_idx = i
                    best_doc_id = doc.get("id")
                    best_title = doc.get("title")

            # 🧠 NLI (only if needed)
            best_nli_score = 0.0
            best_nli_label = "NEUTRAL"

            if best_sim > 0.8:
                # 🔥 Strong match → skip NLI
                best_nli_score = 1.0
                best_nli_label = "ENTAILMENT"
            else:
                try:
                    nli_input = f"{best_sent} </s></s> {claim}"
                    nli_out = self.nli_pipe(nli_input)

                    best_nli_score = float(nli_out[0]["score"])
                    best_nli_label = nli_out[0]["label"]

                except Exception:
                    best_nli_score = 0.5
                    best_nli_label = "NEUTRAL"

            # 🎯 Combined scoring (tuned)
            combined = (0.85 * best_sim) + (0.15 * best_nli_score)

            # 🔥 Boost if strong similarity
            if best_sim > 0.75:
                combined += 0.1

            combined = min(combined, 1.0)

            supported = combined > 0.6

            results.append({
                "text": claim,
                "cited_doc_idx": best_doc_idx,
                "cited_doc_id": best_doc_id,
                "title": best_title,
                "best_doc_sentence": best_sent,
                "sim": round(best_sim, 4),
                "nli_label": best_nli_label,
                "nli_score": round(best_nli_score, 4),
                "score": round(combined, 4),
                "supported": supported
            })

            total_score += combined

        overall_support = (total_score / len(results)) if results else 0.0

        return {
            "claims": results,
            "overall_support": round(overall_support, 4)
        }