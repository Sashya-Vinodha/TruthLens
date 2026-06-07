import re
from typing import Any, Dict, List
import logging
from .utils import extract_years, sentence_split, sentence_support_score

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Load the pipeline ONCE globally so the server stays lightning-fast
_NLI_PIPE = None

def _get_nli_pipeline():
    global _NLI_PIPE
    if _NLI_PIPE is not None:
        return _NLI_PIPE
    try:
        from transformers import pipeline
        logger.info("Loading NLI model into memory...")
        _NLI_PIPE = pipeline("text-classification", model="cross-encoder/nli-deberta-v3-small")
        return _NLI_PIPE
    except Exception as e:
        logger.warning(f"Failed to load NLI model: {e}. Using fallback matching.")
        return None

class Verifier:
    def __init__(self):
        self.embed_model = None
        self.nli_pipe = _get_nli_pipeline()

    def _split_into_sentences(self, text: str) -> List[str]:
        sents = sentence_split(text)
        final_chunks = []
        max_words = 200  
        overlap = 40
        
        for sent in (sents or [text.strip()]):
            words = sent.split()
            if len(words) > max_words:
                for i in range(0, len(words), max_words - overlap):
                    chunk = " ".join(words[i : i + max_words])
                    final_chunks.append(chunk)
            else:
                final_chunks.append(sent)
                
        return final_chunks

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
        norm_docs = []
        for d in retrieved_docs:
            if isinstance(d, dict):
                norm_docs.append({
                    "id": d.get("id"),
                    "text": d.get("text", ""),
                    "title": d.get("title", d.get("text", "")[:50]),
                    "score": d.get("score", 0.0) # <--- Preserving the Search Score!
                })
            else:
                norm_docs.append({
                    "id": None,
                    "text": str(d),
                    "title": str(d)[:50],
                    "score": 0.0
                })

        if not generated_text or not generated_text.strip():
            return {"claims": [], "overall_support": 0.0}

        # We still split the generated text into claims for granular reporting in the UI
        claims = sentence_split(generated_text)
        if not claims:
            claims = [generated_text.strip()]

        results = []
        total_score = 0.0
        has_any_contradiction = False

        # --- THE PATH 1 UPGRADE: MEGA-CONTEXT ---
        # Combine all retrieved docs into one large context for DeBERTa to read at once
        combined_context = " ".join([doc["text"] for doc in norm_docs])

        for claim in claims:
            normalized_claim = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", claim.lower())).strip()
            
            # Allow conversational corrections to pass automatically
            if normalized_claim in {"no that is incorrect", "that is incorrect", "actually", "not quite"}:
                results.append({
                    "text": claim, "cited_doc_idx": None, "cited_doc_id": None, "title": None,
                    "best_doc_sentence": "", "sim": 1.0, "nli_label": "ENTAILMENT", "nli_score": 1.0,
                    "score": 1.0, "supported": True,
                })
                total_score += 1.0
                continue

            # Handle abstentions
            if claim.lower() in {"not found", "i don't have enough information", "i do not have enough information"}:
                results.append({
                    "text": claim, "cited_doc_idx": None, "cited_doc_id": None, "title": None,
                    "best_doc_sentence": "", "sim": 0.0, "nli_label": "NEUTRAL", "nli_score": 0.0,
                    "score": 0.0, "supported": False,
                })
                continue

            best_nli_label = "NEUTRAL"
            best_nli_score = 0.0
            supported = False

            # Evaluate the claim against the ENTIRE context chunk
            if self.nli_pipe and combined_context.strip():
                try:
                    # Pass the whole context as text, and the claim as text_pair
                    nli_result = self.nli_pipe([{"text": combined_context, "text_pair": claim}], truncation=True, max_length=512)[0]
                    best_nli_label = nli_result["label"].upper()
                    best_nli_score = nli_result["score"]
                    
                    if best_nli_label == "CONTRADICTION":
                        has_any_contradiction = True
                        supported = False
                    elif best_nli_label == "ENTAILMENT" and best_nli_score > 0.4:
                        supported = True
                    else:
                        supported = False 
                except Exception as e:
                    logger.error(f"NLI run error: {e}")

            final_score = 0.0 if best_nli_label == "CONTRADICTION" else best_nli_score

            results.append({
                "text": claim,
                "cited_doc_idx": 0, 
                "cited_doc_id": norm_docs[0].get("id") if norm_docs else None,
                "title": norm_docs[0].get("title") if norm_docs else None,
                "best_doc_sentence": "Combined Document Context",
                "sim": 0.0, # Legacy compatibility
                "nli_label": best_nli_label,
                "nli_score": round(best_nli_score, 4),
                "score": round(final_score, 4),
                "supported": supported
            })

            total_score += final_score

        # --- THE FIX: Honest Confidence Math ---
        
        # 1. Calculate the Verifier Score (No Chatty Tax)
        factual_results = [r for r in results if len(r.get("text", "").split()) > 7]
        if not factual_results:
            factual_results = results 
            
        factual_total = sum(r["score"] for r in factual_results)
        verifier_score = (factual_total / len(factual_results)) if factual_results else 0.0

        # 2. Calculate the Retrieval Score (How good were the PDFs we found?)
        avg_retrieval_score = sum(doc.get("score", 0.0) for doc in norm_docs) / len(norm_docs) if norm_docs else 0.0

        # 3. True System Confidence = 60% Fact-Check + 40% Search Quality
        overall_support = (verifier_score * 0.6) + (avg_retrieval_score * 0.4)
        
        # Immediate kill switch for lies
        if has_any_contradiction:
            overall_support = 0.0

        return {
            "claims": results,
            "overall_support": round(overall_support, 4)
        }