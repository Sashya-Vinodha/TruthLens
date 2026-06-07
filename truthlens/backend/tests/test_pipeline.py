import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app import generator, main, retriever, utils, verifier


def test_query_normalization_handles_company_act():
    expanded = utils.expand_query("when was the company act established?")

    assert "companies" in expanded
    assert "act" in expanded
    assert "established" in expanded or "enacted" in expanded


def test_topic_match_allows_short_queries():
    assert utils.topic_match("sebi role", ["The Securities and Exchange Board of India (SEBI) regulates the securities market and protects the interests of investors in India."])


def test_generator_extracts_year_from_grounded_document():
    docs = [
        {
            "id": "DOC_0",
            "text": "The Companies Act, 2013, governs the incorporation, responsibilities, and dissolution of companies in India.",
        }
    ]

    assert generator.generate_answer("when was the company act established?", docs) == "The Companies Act, 2013, governs the incorporation, responsibilities, and dissolution of companies in India."


def test_generator_corrects_wrong_mfa_assumption():
    docs = [
        {
            "id": "DOC_52",
            "text": "Multi-factor authentication (MFA) is mandatory for all taxpayers accessing the GST portal as of April 1, 2025.",
        }
    ]

    answer = generator.generate_answer("Is MFA required on January 30?", docs)

    assert answer.startswith("No, that is incorrect.")
    assert "April 1, 2025" in answer


def test_verifier_accepts_grounded_year_answer():
    docs = [
        {
            "id": "DOC_0",
            "text": "The Companies Act, 2013, governs the incorporation, responsibilities, and dissolution of companies in India.",
        }
    ]

    result = verifier.Verifier().verify("Companies Act was established in 2013.", docs)

    assert result["overall_support"] >= 0.55
    assert result["claims"][0]["supported"] is True


def test_main_returns_grounded_answer(monkeypatch):
    docs = [
        {
            "id": "DOC_0",
            "text": "The Companies Act, 2013, governs the incorporation, responsibilities, and dissolution of companies in India.",
        }
    ]

    monkeypatch.setattr(retriever, "retrieve", lambda question, k=3: docs)

    response = main.query(main.QueryRequest(question="when was the company act established?", k=3))

    assert response["answer"] == "The Companies Act, 2013, governs the incorporation, responsibilities, and dissolution of companies in India."
    assert response["abstain"] is False
    assert response["confidence"] > 0.0


def test_main_answers_valid_mfa_query_after_retrieval(monkeypatch):
    docs = [
        {
            "id": "DOC_52",
            "text": "Multi-factor authentication (MFA) is mandatory for all taxpayers accessing the GST portal as of April 1, 2025.",
        }
    ]

    monkeypatch.setattr(retriever, "retrieve", lambda question, k=3: docs)

    response = main.query(main.QueryRequest(question="tell me about MFA", k=3))

    assert response["abstain"] is False
    assert "MFA" in response["answer"]
    assert response["retrieved_docs"]


def test_main_corrects_wrong_assumption_after_retrieval(monkeypatch):
    docs = [
        {
            "id": "DOC_52",
            "text": "Multi-factor authentication (MFA) is mandatory for all taxpayers accessing the GST portal as of April 1, 2025.",
        }
    ]

    monkeypatch.setattr(retriever, "retrieve", lambda question, k=3: docs)

    response = main.query(main.QueryRequest(question="Is MFA required on January 30?", k=3))

    assert response["abstain"] is False
    assert response["answer"].startswith("No, that is incorrect.")
    assert "April 1, 2025" in response["answer"]


def test_main_abstains_on_unsupported_answer(monkeypatch):
    docs = [
        {
            "id": "DOC_0",
            "text": "The Companies Act, 2013, governs the incorporation, responsibilities, and dissolution of companies in India.",
        }
    ]

    monkeypatch.setattr(retriever, "retrieve", lambda question, k=3: docs)
    monkeypatch.setattr(generator, "generate_answer", lambda question, docs: "Companies Act was established in 2014.")

    response = main.query(main.QueryRequest(question="when was the company act established?", k=3))

    assert response["abstain"] is True
    assert response["answer"] == "I couldn't find relevant information in the dataset."


def test_retriever_ignores_misleading_year_signals(monkeypatch):
    docs = [
        {
            "id": "DOC_0",
            "text": "The 2020 Bill discusses unrelated amendments and transition rules.",
        },
        {
            "id": "DOC_1",
            "text": "The Companies Act, 2013, governs the incorporation, responsibilities, and dissolution of companies in India.",
        },
    ]

    monkeypatch.setattr(retriever, "DOCS", docs)
    monkeypatch.setattr(retriever, "_BM25", None)
    monkeypatch.setattr(retriever, "_DOC_EMBEDDINGS", None)
    monkeypatch.setattr(retriever, "_EMBEDDER", None)
    monkeypatch.setattr(retriever, "_get_embedder", lambda: None)

    ranked = retriever.retrieve("when was the company act established?", k=2)

    assert ranked[0]["id"] == "DOC_1"
    assert ranked[0]["text"].startswith("The Companies Act, 2013")


def test_main_abstains_only_after_retrieval_when_topic_mismatch(monkeypatch):
    docs = [
        {
            "id": "DOC_0",
            "text": "The Companies Act, 2013, governs the incorporation, responsibilities, and dissolution of companies in India.",
        }
    ]

    called = {"retrieved": False}

    def fake_retrieve(question, k=3):
        called["retrieved"] = True
        return docs

    monkeypatch.setattr(retriever, "retrieve", fake_retrieve)
    monkeypatch.setattr(main, "topic_match", lambda question, doc_texts: False)

    response = main.query(main.QueryRequest(question="talk about cricket", k=3))

    assert called["retrieved"] is True
    assert response["abstain"] is True
    assert response["answer"] == "I couldn't find relevant information in the dataset."
    assert response["confidence"] == 0.0
    assert response["retrieved_docs"]