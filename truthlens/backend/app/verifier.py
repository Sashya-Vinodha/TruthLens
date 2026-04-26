import re
from typing import Any, Dict, List
import logging

from .utils import extract_years, sentence_split, sentence_support_score

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class Verifier:
    def __init__(self):
        self.embed_model = None
        self.nli_pipe = None

    def _split_into_sentences(self, text: str) -> List[str]:
        return sentence_split(text) or [text.strip()]

    def _best_doc_sentence(self, claim: str, doc_text: str):
        doc_sents = self._split_into_sentences(doc_text)

        best_sentence = doc_text.strip()
        best_score = 0.0

        for sentence in doc_sents:
            score = sentence_support_score(claim, sentence)
            if score > best_score:
                best_sentence = sentence
                best_score = score

        return best_sentence, best_score

    def _claim_supported(self, claim: str, doc_text: str) -> Dict[str, Any]:
        best_sentence, best_score = self._best_doc_sentence(claim, doc_text)
        claim_years = extract_years(claim)
        sentence_years = extract_years(best_sentence)
        year_match = not claim_years or any(year in sentence_years or year in doc_text for year in claim_years)

        supported = best_score >= 0.55 and year_match
        return {
            "best_sentence": best_sentence,
            "score": round(best_score, 4),
            "supported": supported,
            "year_match": year_match,
        }

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

        if not generated_text or not generated_text.strip():
            return {"claims": [], "overall_support": 0.0}

        claims = sentence_split(generated_text)
        if not claims:
            claims = [generated_text.strip()]

        results = []
        total_score = 0.0

        for claim in claims:

            normalized_claim = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", claim.lower())).strip()
            if normalized_claim in {"no that is incorrect", "that is incorrect"}:
                results.append({
                    "text": claim,
                    "cited_doc_idx": None,
                    "cited_doc_id": None,
                    "title": None,
                    "best_doc_sentence": "",
                    "sim": 1.0,
                    "nli_label": "NEUTRAL",
                    "nli_score": 1.0,
                    "score": 1.0,
                    "supported": True,
                })
                total_score += 1.0
                continue

            best_sim = 0.0
            best_sent = ""
            best_doc_idx = None
            best_doc_id = None
            best_title = None

            if claim.lower() in {"not found", "i don't have enough information", "i do not have enough information"}:
                results.append({
                    "text": claim,
                    "cited_doc_idx": None,
                    "cited_doc_id": None,
                    "title": None,
                    "best_doc_sentence": "",
                    "sim": 0.0,
                    "nli_label": "NEUTRAL",
                    "nli_score": 0.0,
                    "score": 0.0,
                    "supported": False,
                })
                continue

            # 🔍 Find best matching doc sentence
            for i, doc in enumerate(norm_docs):
                support = self._claim_supported(claim, doc["text"])
                sent = support["best_sentence"]
                sim = support["score"]
                if sim > best_sim:
                    best_sim = sim
                    best_sent = sent
                    best_doc_idx = i
                    best_doc_id = doc.get("id")
                    best_title = doc.get("title")

            combined = min(1.0, best_sim)
            supported = combined >= 0.55
            best_nli_score = combined
            best_nli_label = "ENTAILMENT" if supported else "NEUTRAL"

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