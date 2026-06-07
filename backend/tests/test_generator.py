import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
	sys.path.insert(0, str(BACKEND_ROOT))

from app import generator


def test_generate_answer_corrects_wrong_year_assumption():
	docs = [
		{
			"id": "DOC_0",
			"text": "MFA is mandatory from April 1, 2025.",
		}
	]

	answer = generator.generate_answer("Is MFA required from January 30?", docs)

	assert answer.startswith("No, that is incorrect.")
	assert "April 1, 2025" in answer


def test_generate_answer_corrects_required_vs_optional_assumption():
	docs = [
		{
			"id": "DOC_0",
			"text": "Labour charges are mandatory.",
		}
	]

	answer = generator.generate_answer("Are labour charges optional?", docs)

	assert answer == "No, that is incorrect. Labour charges are mandatory."


def test_generate_answer_still_answers_normally_for_factual_question():
	docs = [
		{
			"id": "DOC_0",
			"text": "GST is a value-added tax levied on most goods and services.",
		}
	]

	answer = generator.generate_answer("What is GST?", docs)

	assert answer == "GST is a value-added tax levied on most goods and services."
