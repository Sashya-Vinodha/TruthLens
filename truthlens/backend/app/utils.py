"""Shared query and evidence helpers for the TruthLens RAG pipeline."""

from __future__ import annotations

import re
from typing import List

try:
	import google.generativeai as genai

	HAS_GEMINI = True
except ImportError:
	genai = None
	HAS_GEMINI = False


STOPWORDS = {
	"a","an","and","are","at","be","been","being","by","for","from","has","have",
	"in","is","it","of","on","or","the","to","was","were","when","what","which",
	"who","why","with",
}

CONTROLLED_SYNONYMS = {
	"act": ["law", "regulation", "code", "bill"],
	"adopted": ["enacted", "introduced", "passed"],
	"company": ["companies"],
	"companies": ["company"],
	"established": ["enacted", "introduced", "passed", "founded", "formed"],
	"establish": ["enact", "introduce", "pass", "found", "form"],
	"founded": ["established"],
	"formed": ["established"],
	"law": ["act", "regulation"],
	"regulation": ["act", "law"],
}

PHRASE_NORMALIZATIONS = {
	"company act": "companies act",
	"company acts": "companies acts",
	"mfa": "multi factor authentication",
}

LEGAL_KEYWORDS = {
	"act","law","code","section","wages","company","companies","regulation","bill",
}

ABSTAIN_MESSAGE = "I couldn't find relevant information in the dataset."

YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")


def normalize_text(text: str) -> str:
	text = text or ""
	text = re.sub(r"[^\x00-\x7F]", " ", text)
	text = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
	return re.sub(r"\s+", " ", text).strip()


def tokenize(text: str) -> List[str]:
	return re.findall(r"[a-z0-9]+", (text or "").lower())


def content_tokens(text: str) -> List[str]:
	return [token for token in tokenize(text) if token not in STOPWORDS]


def clean_text(text: str) -> str:
	text = normalize_text(text)
	text = re.sub(r"\d+", " ", text)
	return re.sub(r"\s+", " ", text).strip()


def rewrite_query_locally(query: str) -> str:
	rewritten = query or ""
	for source, target in PHRASE_NORMALIZATIONS.items():
		rewritten = re.sub(rf"\b{re.escape(source)}\b", target, rewritten, flags=re.IGNORECASE)
	return re.sub(r"\s+", " ", rewritten).strip()


# 🔥 UPDATED FUNCTION
def is_domain_relevant(query: str) -> bool:
	tokens = set(content_tokens(query))

	# Must contain at least one strong legal keyword
	if not (tokens & LEGAL_KEYWORDS):
		return False

	# Reject obvious non-legal patterns
	lowered = normalize_text(query)

	non_legal_patterns = [
		"who is","who was","when did","where did",
		"charlie","actor","movie","film",
		"death","born","biography","celebrity"
	]

	if any(p in lowered for p in non_legal_patterns):
		return False

	return True


# 🔥 UPDATED FUNCTION
def is_answerable_query(query: str) -> bool:
	if not query or not query.strip():
		return False

	# If Gemini unavailable → rely on STRICT domain check
	if not HAS_GEMINI:
		return is_domain_relevant(query)

	api_key = None
	try:
		from os import getenv
		api_key = getenv("GEMINI_API_KEY")
	except Exception:
		api_key = None

	if not api_key:
		return is_domain_relevant(query)

	try:
		genai.configure(api_key=api_key)
		model = genai.GenerativeModel("models/gemini-2.5-pro")

		prompt = f"""
You are a strict classifier.

The system contains ONLY legal documents.

Reject ANY non-legal question.

Query: {query}

Answer ONLY YES or NO
"""

		response = model.generate_content(prompt)
		result = normalize_text(
			getattr(response, "text", None)
			or getattr(response, "output_text", None)
			or str(response)
		)

		if result.startswith("yes"):
			return True
		if result.startswith("no"):
			return False

		return is_domain_relevant(query)

	except Exception:
		return is_domain_relevant(query)


def rewrite_query_with_gemini(query: str) -> str:
	api_key = None
	try:
		from os import getenv
		api_key = getenv("GEMINI_API_KEY")
	except Exception:
		api_key = None

	if not api_key or not HAS_GEMINI:
		return rewrite_query_locally(query)

	try:
		genai.configure(api_key=api_key)
		model = genai.GenerativeModel("models/gemini-2.5-pro")

		prompt = (
			"Rewrite this query clearly without changing meaning.\n\n"
			f"Query: {query}"
		)

		response = model.generate_content(prompt)
		return re.sub(r"\s+", " ", (response.text or "")).strip()

	except Exception:
		return rewrite_query_locally(query)


def expand_query(query: str) -> str:
	tokens = tokenize(query)
	expanded: List[str] = []
	seen = set()

	def add(term: str):
		if term and term not in seen:
			seen.add(term)
			expanded.append(term)

	for token in tokens:
		add(token)
		for syn in CONTROLLED_SYNONYMS.get(token, []):
			add(syn)

	return " ".join(expanded)


def build_query_variants(query: str) -> List[str]:
	return list({
		normalize_text(v): v
		for v in [
			query,
			rewrite_query_with_gemini(query),
			rewrite_query_locally(query),
			expand_query(query),
		]
	}.values())


def extract_years(text: str) -> List[str]:
	return YEAR_RE.findall(text or "")


def extract_first_year(text: str) -> str | None:
	years = extract_years(text)
	return years[0] if years else None


def is_temporal_question(question: str) -> bool:
	lowered = normalize_text(question)
	return any(marker in lowered for marker in (
		"when","what year","established","enacted","introduced","passed"
	))


def keyword_overlap(left: str, right: str) -> float:
	left_tokens = set(content_tokens(left))
	right_tokens = set(content_tokens(right))
	return len(left_tokens & right_tokens) / max(len(left_tokens), 1)


def topic_match(query: str, docs: List[str]) -> bool:
	query_words = set(content_tokens(clean_text(query)))
	doc_words = set(content_tokens(clean_text(" ".join(docs))))

	overlap = query_words & doc_words

	required_overlap = 1 if len(query_words) == 1 else 2
	if len(overlap) >= required_overlap:
		return True

	query_acronyms = {token.lower() for token in re.findall(r"\b[A-Z]{2,}\b", query or "")}
	if query_acronyms & doc_words:
		return True

	return False


def sentence_split(text: str) -> List[str]:
	return [s.strip() for s in re.split(r"(?<=[.?!])\s+", text or "") if s.strip()]


def strip_leading_article(text: str) -> str:
	return re.sub(r"^(the|a|an)\s+", "", text or "", flags=re.IGNORECASE)


def is_abstain_phrase(text: str) -> bool:
	normalized = normalize_text(text)
	return any(p in normalized for p in (
		"not found",
		"could not find relevant information",
		"no relevant information",
		"abstain"
	))


def make_subject_from_doc(doc_text: str) -> str:
	head = (doc_text or "").split(".")[0]
	return strip_leading_article(head)


def sentence_support_score(question: str, sentence: str) -> float:
	overlap = keyword_overlap(question, sentence)
	score = overlap

	q_years = extract_years(question)
	s_years = extract_years(sentence)

	if q_years:
		score += 0.35 if any(y in s_years for y in q_years) else -0.2

	return max(0.0, min(1.0, score))
