import re
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer, util
from transformers import pipeline
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Lightweight defaults; these models are reasonably small (except MNLI which is larger)
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
NLI_MODEL_NAME = "roberta-large-mnli"  # you can swap to a smaller MNLI if needed


class Verifier:
    def __init__(self):
        logger.info("Loading embedding model (%s)...", EMBED_MODEL_NAME)
        self.embed_model = SentenceTransformer(EMBED_MODEL_NAME)

        logger.info("Loading NLI model (%s)... (this may take a minute on first run)", NLI_MODEL_NAME)
        self.nli_pipe = pipeline("text-classification", model=NLI_MODEL_NAME, device=0 if self._has_gpu() else -1)

    def _has_gpu(self):
        # simple check: prefer metal/mps if available, otherwise CPU
        try:
            import torch
            return torch.cuda.is_available()
        except Exception:
            return False

    def _split_into_sentences(self, text: str) -> List[str]:
        # Simple split that keeps abbreviations mostly okay for our demo use
        sents = re.split(r'(?<=[.?!])\s+', text.strip())
        sents = [s.strip() for s in sents if s.strip()]
        return sents if sents else [text.strip()]

    def _best_doc_sentence(self, claim: str, doc_text: str):
        """
        Split doc_text into sentences, compute embedding similarity vs claim,
        and return the best matching sentence + similarity score.
        """
        doc_sents = self._split_into_sentences(doc_text)
        # encode claim + doc sentences
        claim_emb = self.embed_model.encode(claim, convert_to_tensor=True)
        doc_embs = self.embed_model.encode(doc_sents, convert_to_tensor=True)
        sims = util.cos_sim(claim_emb, doc_embs).cpu().numpy().flatten()
        best_idx = int(sims.argmax())
        best_sim = float(sims[best_idx])
        best_sent = doc_sents[best_idx]
        return best_sent, best_sim

    def verify(self, generated_text: str, retrieved_docs: List[Any]) -> Dict[str, Any]:
        """
        Input:
            generated_text: string answer produced by generator (may contain [DOC_i] citations)
            retrieved_docs: list of docs (each doc is either a string or a dict with 'text' and 'id')
        Output:
            {
              "claims": [
                {
                  "text": "...",
                  "cited_doc_idx": 0 or null,
                  "cited_doc_id": "doc_123" or null,
                  "best_doc_sentence": "...",
                  "sim": 0.842,
                  "nli_label": "ENTAILMENT"/"NEUTRAL"/"CONTRADICTION",
                  "nli_score": 0.92,
                  "score": 0.78,            # combined score (0..1)
                  "supported": true/false
                }, ...
              ],
              "overall_support": 0.73
            }
        """
        # Normalize docs into dicts with 'text' and optional 'id'
        norm_docs = []
        for d in retrieved_docs:
            if isinstance(d, dict):
                norm_docs.append({"id": d.get("id"), "text": d.get("text", "")})
            else:
                norm_docs.append({"id": None, "text": str(d)})

        # Split into sentence-level claims
        claims = re.split(r'(?<=[.?!])\s+', generated_text)
        claims = [c.strip() for c in claims if c.strip()]

        results = []
        total_score = 0.0

        for claim in claims:
            # find cited doc indices
            doc_indices = [int(x) for x in re.findall(r'\[DOC_(\d+)\]', claim)]
            # choose target docs (from citations or fallback to top-1)
            target_docs = [norm_docs[i] for i in doc_indices if i < len(norm_docs)]
            if not target_docs and norm_docs:
                target_docs = [norm_docs[0]]

            best_sim = 0.0
            best_sent = ""
            best_doc_idx = None
            best_doc_id = None
            best_nli_score = 0.0
            best_nli_label = "NEUTRAL"

            if target_docs:
                # For each target doc, find best sentence and sim; pick overall best
                for idx, doc in enumerate(target_docs):
                    doc_text = doc["text"]
                    sent, sim = self._best_doc_sentence(claim, doc_text)
                    if sim > best_sim:
                        best_sim = sim
                        best_sent = sent
                        # If doc_indices were provided, map back to original index
                        if doc_indices:
                            # doc corresponds to doc_indices position
                            best_doc_idx = doc_indices[target_docs.index(doc)]
                        else:
                            # fallback: find index in norm_docs
                            best_doc_idx = norm_docs.index(doc)
                        best_doc_id = doc.get("id")

                # Run NLI on the best sentence vs claim
                # We pass premise=best_sent, hypothesis=claim
                nli_input = f"{best_sent} </s></s> {claim}"
                try:
                    nli_out = self.nli_pipe(nli_input, truncation=True, top_k=None)
                except TypeError:
                    # older transformers may not accept top_k=None; fall back to default (3)
                    nli_out = self.nli_pipe(nli_input, truncation=True)

                # nli_out is a list of label dicts. Find entailment score if present
                entail_score = 0.0
                label = "NEUTRAL"
                for entry in nli_out:
                    lab = entry.get("label", entry.get("score", None))
                    scr = float(entry.get("score", 0.0))
                    # labels can be 'ENTAILMENT','NEUTRAL','CONTRADICTION' (or variants)
                    if isinstance(lab, str) and lab.upper().startswith("ENTAIL"):
                        entail_score = scr
                        label = "ENTAILMENT"
                        break
                    # otherwise, capture the highest-scoring label if no entailment found
                    if scr > entail_score:
                        entail_score = scr
                        label = entry.get("label", "NEUTRAL")

                best_nli_score = float(entail_score)
                best_nli_label = label

            # Combine into a single support score (tuned for demo)
            # Give more weight to semantic similarity because NLI probabilities may be low
            combined = (0.6 * best_sim) + (0.4 * best_nli_score)
            supported = combined > 0.45  # slightly lower threshold for support


            results.append({
                "text": claim,
                "cited_doc_idx": best_doc_idx,
                "cited_doc_id": best_doc_id,
                "best_doc_sentence": best_sent,
                "sim": round(best_sim, 4),
                "nli_label": best_nli_label,
                "nli_score": round(best_nli_score, 4),
                "score": round(combined, 4),
                "supported": bool(supported)
            })

            total_score += combined

        overall_support = (total_score / len(results)) if results else 0.0

        return {
            "claims": results,
            "overall_support": round(overall_support, 4)
        }
