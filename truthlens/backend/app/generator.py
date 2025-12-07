import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    logger.warning("Gemini SDK not installed. Using mock generator.")
    HAS_GEMINI = False


MODEL_NAME = "models/gemini-2.5-pro"   # YOUR WORKING MODEL


def generate_answer(question: str, retrieved_docs: list) -> str:
    """
    Returns a concise answer string that MUST include inline citations [DOC_i].
    If evidence is insufficient: "I abstain — evidence insufficient."
    """
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key or not HAS_GEMINI:
        logger.warning("Using mock fallback")
        return _mock_generate(question, retrieved_docs)

    try:
        return _call_gemini(api_key, question, retrieved_docs)
    except Exception as e:
        logger.error(f"Gemini error: {e}. Using mock fallback.")
        return _mock_generate(question, retrieved_docs)


def _build_context(retrieved_docs):
    parts = []
    for i, d in enumerate(retrieved_docs):
        parts.append(f"[DOC_{i}] {d.get('text','').strip()}")
    return "\n\n".join(parts)


def _call_gemini(api_key: str, question: str, retrieved_docs: list) -> str:
    """Primary generation logic using Gemini with robust response parsing."""
    genai.configure(api_key=api_key)

    MODEL_NAME = "models/gemini-2.5-pro"
    model = genai.GenerativeModel(MODEL_NAME)

    context_str = _build_context_string(retrieved_docs)

    prompt = f"""You are a precise verification assistant. Answer the question using ONLY the provided documents below.

Rules:
1. You must use ONLY the provided context. Do not use outside knowledge.
2. Every factual statement MUST be immediately followed by a citation in the format [DOC_i], where i is the index of the document.
3. If the provided documents do not contain enough information to answer the question, respond exactly with: "I abstain — evidence insufficient."

---
Few-Shot Examples:

Context:
[DOC_0] The Eiffel Tower is located in Paris, France. It was constructed in 1889.
[DOC_1] The Statue of Liberty is in New York.

Question: Where is the Eiffel Tower?
Answer: The Eiffel Tower is located in Paris, France [DOC_0].

Context:
[DOC_0] Apples are a type of fruit.
[DOC_1] Bananas are rich in potassium.

Question: Who was the first president of the USA?
Answer: I abstain — evidence insufficient.
---

Current Context:
{context_str}

Question: {question}
Answer:"""

    logger.info(f"Calling Gemini model: {MODEL_NAME}")

    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            candidate_count=1,
            max_output_tokens=300,
            temperature=0.0,
        )
    )

    # Try common quick-accessors first
    # 1) output_text
    try:
        if hasattr(response, "output_text") and response.output_text:
            return response.output_text.strip()
    except Exception:
        pass

    # 2) text (some SDK versions expose .text)
    try:
        if hasattr(response, "text") and response.text:
            return response.text.strip()
    except Exception:
        pass

    # 3) candidates -> content parts (most robust)
    try:
        if hasattr(response, "candidates") and response.candidates:
            cand = response.candidates[0]
            # Some SDKs use cand.content (list of parts)
            if hasattr(cand, "content") and cand.content:
                parts = []
                for part in cand.content:
                    # part may be a dict-like or an object with attributes
                    try:
                        # dict-like
                        if isinstance(part, dict):
                            # common keys: 'text', 'message', 'content'
                            text = part.get("text") or part.get("message") or part.get("content") or ""
                        else:
                            # object with attributes
                            text = getattr(part, "text", None) or getattr(part, "message", None) or getattr(part, "content", None) or str(part)
                    except Exception:
                        text = str(part)
                    if text:
                        parts.append(str(text))
                joined = " ".join(p for p in parts if p)
                if joined:
                    return joined.strip()

            # Some SDKs put text in candidate.output or candidate.message
            if hasattr(cand, "output") and cand.output:
                # output might be list of parts too
                try:
                    out_parts = []
                    for o in cand.output:
                        if isinstance(o, dict):
                            out_parts.append(o.get("text") or o.get("content") or "")
                        else:
                            out_parts.append(str(o))
                    joined = " ".join(p for p in out_parts if p)
                    if joined:
                        return joined.strip()
                except Exception:
                    pass

            # Finally try candidate.text / candidate.message
            for attr in ("text", "message", "content"):
                try:
                    t = getattr(cand, attr, None)
                    if t:
                        return str(t).strip()
                except Exception:
                    continue
    except Exception:
        pass

    # 4) As a last-ditch fallback, try str(response)
    try:
        raw = str(response)
        if raw and len(raw) > 0:
            return raw[:5000].strip()
    except Exception:
        pass

    # If nothing returned, raise so caller can fallback to mock
    raise RuntimeError("Unable to extract text from Gemini response.")

# ...existing code...

def _mock_generate(question, retrieved_docs):
    logger.info("Generating mock response...")

    # If no documents were retrieved, we can't answer
    if not retrieved_docs:
        return "I abstain — evidence insufficient."

    # Take the best document (the first one)
    best_doc = retrieved_docs[0]
    doc_text = best_doc.get("text", "")
    doc_id = best_doc.get("id", "UNKNOWN")

    # Simple heuristic: Return the first sentence or the whole text
    # This makes it work for ANY document in your JSON
    answer = doc_text.split('\n')[0]  # Take the first line/sentence
    
    return f"{answer} [{doc_id}]."

# ...existing code...


if __name__ == "__main__":
    print("--- Testing Generator Module ---")

    docs = [
        {"text": "Alexander Fleming discovered Penicillin in 1928."},
        {"text": "Insulin is a hormone regulating blood sugar."}
    ]

    print("\nQ: Who discovered penicillin?")
    print("A:", generate_answer("Who discovered penicillin?", docs))

    print("\nQ: What is the capital of Mars?")
    print("A:", generate_answer("What is the capital of Mars?", docs))
