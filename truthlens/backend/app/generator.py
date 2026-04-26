import os
import logging
import re

from .utils import (
    ABSTAIN_MESSAGE,
    extract_years,
    is_abstain_phrase,
    sentence_split,
    sentence_support_score,
)

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

DATE_PHRASE_RE = re.compile(
    r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2}(?:,\s*\d{4})?|\b(?:19|20)\d{2}\b",
    re.IGNORECASE,
)


def is_yes_no_question(q: str) -> bool:
	q = (q or "").lower().strip()
	return q.startswith(("is", "are", "does", "do", "can", "was", "were"))


def _format_correction(sentence: str) -> str:
    sentence = (sentence or "").strip()
    if not sentence:
        return ""
    if sentence[-1] not in ".!?":
        sentence += "."
    return f"No, that is incorrect. {sentence}"


def _extract_date_phrases(text: str) -> list[str]:
	return [match.group(0).strip() for match in DATE_PHRASE_RE.finditer(text or "")]


def _best_sentence(question: str, retrieved_docs: list) -> str:
	sentences = []
	for doc in retrieved_docs:
		doc_text = doc.get("text", "") if isinstance(doc, dict) else str(doc)
		sentences.extend(sentence_split(doc_text) or [doc_text.strip()])
	sentences = [sentence.strip() for sentence in sentences if sentence and sentence.strip()]
	if not sentences:
		return ""
	return max(sentences, key=lambda sentence: sentence_support_score(question, sentence))


def _has_contradiction(question: str, sentence: str) -> bool:
	question_years = extract_years(question)
	sentence_years = extract_years(sentence)
	if question_years and sentence_years and not any(year in sentence_years for year in question_years):
		return True

	question_dates = _extract_date_phrases(question)
	sentence_dates = _extract_date_phrases(sentence)
	if question_dates and sentence_dates and question_dates != sentence_dates:
		return True

	question_lower = (question or "").lower()
	sentence_lower = (sentence or "").lower()
	question_optional = "optional" in question_lower
	question_required = "required" in question_lower or "mandatory" in question_lower
	sentence_optional = "optional" in sentence_lower or "not required" in sentence_lower
	sentence_required = "required" in sentence_lower or "mandatory" in sentence_lower
	return (question_optional and sentence_required) or (question_required and sentence_optional)


def generate_answer(question: str, retrieved_docs: list) -> str:
    """
    Returns a concise extractive answer grounded only in retrieved evidence.
    If evidence is insufficient: "Not found".
    """
    if not retrieved_docs:
        return ABSTAIN_MESSAGE

    best_sentence = _best_sentence(question, retrieved_docs)
    if not best_sentence:
        return ABSTAIN_MESSAGE

    if is_yes_no_question(question) and _has_contradiction(question, best_sentence):
        return _format_correction(best_sentence)

    return best_sentence


def _build_context(retrieved_docs):
    parts = []
    for i, d in enumerate(retrieved_docs):
        parts.append(f"[DOC_{i}] {d.get('text','').strip()}")
    return "\n\n".join(parts)


def _best_doc(question: str, retrieved_docs: list):
    best_doc = None
    best_score = -1.0
    normalized_question = rewrite_query_locally(question)

    for doc in retrieved_docs:
        text = doc.get("text", "") if isinstance(doc, dict) else str(doc)
        score = keyword_overlap(normalized_question, text)
        if is_temporal_question(question):
            score += 0.15 if extract_first_year(text) else 0.0
        if isinstance(doc, dict):
            score += float(doc.get("score", 0.0)) * 0.2
        if score > best_score:
            best_score = score
            best_doc = doc

    return best_doc, best_score


def _extractive_answer(question: str, retrieved_docs: list) -> str:
    best_doc, score = _best_doc(question, retrieved_docs)
    if not best_doc or score < 0.2:
        return ""

    doc_text = best_doc.get("text", "") if isinstance(best_doc, dict) else str(best_doc)
    if not doc_text.strip():
        return ""

    if is_temporal_question(question):
        year = extract_first_year(doc_text)
        if year:
            subject = _subject_from_doc_text(doc_text)
            if subject:
                return f"{subject} was established in {year}."
            return f"It was established in {year}."

    first_sentence = doc_text.split("\n")[0].strip()
    if first_sentence and first_sentence[-1] not in ".!?":
        first_sentence += "."
    return first_sentence


def _call_gemini(api_key: str, question: str, retrieved_docs: list) -> str:
    """Primary generation logic using Gemini with robust response parsing."""
    genai.configure(api_key=api_key)

    MODEL_NAME = "models/gemini-2.5-pro"
    model = genai.GenerativeModel(MODEL_NAME)

    context_str = _build_context(retrieved_docs)

    prompt = f"""
Answer strictly from the provided context and include inline citations like [DOC_i].

If the user's question contains incorrect assumptions, explicitly respond with: "No, that is incorrect." and then provide the corrected fact from the context.

Only respond with "Not found" when the context truly lacks the necessary facts to answer or correct the question.

Context:
{context_str}

Question:
{question}

Answer:
"""

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

    if not retrieved_docs:
        return ABSTAIN_MESSAGE

    # Take the best document (the first one)
    best_doc = retrieved_docs[0]
    doc_text = best_doc.get("text", "")
    doc_id = best_doc.get("id", "UNKNOWN")

    answer = doc_text.split('\n')[0]
    
    return f"{answer}"

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
