# TruthLens: Domain-Locked Compliance Verification System

## 1. High-Impact Introduction

TruthLens is a **Domain-Locked Compliance Verification System** engineered to deliver high-fidelity, verifiable answers for mission-critical legal and regulatory queries. The system implements a strict **"abstain-over-hallucinate"** logic, prioritizing factual accuracy and reliability over the unconstrained, generalized outputs of standard Large Language Models (LLMs).

By locking the knowledge domain to a curated corpus—currently encompassing **Indian Corporate Law, SEBI Regulations, and Labour Law**—TruthLens mitigates the risk of factual hallucination, a critical failure mode in regulated industries. It is not a general-purpose chatbot; it is a specialized verification engine designed for enterprise-grade compliance and risk management.

## 2. Architecture Breakdown

TruthLens employs a multi-stage programmatic pipeline to ensure every output is grounded in and validated against source documentation.

```
Query Ingestion -> Document Chunking -> Embedding & Vector Search -> Context Retrieval -> LLM Generation -> NLI Verification -> Output or Abstain
```

1.  **Query Ingestion & Pre-processing**: The system ingests a user's natural language query and normalizes it for downstream processing.
2.  **Document Chunking & Embedding**: The domain-specific legal corpus is parsed, chunked into manageable segments, and converted into high-dimensional vectors using a sentence transformer model. These embeddings are stored in a FAISS vector index for efficient similarity search.
3.  **Context Retrieval (RAG)**: The user's query is embedded and used to perform a vector search against the index, retrieving the most relevant document chunks that serve as the foundational context.
4.  **LLM Generation**: The retrieved context and the original query are passed to a generative LLM (e.g., Gemini 2.5 Pro), which synthesizes a preliminary answer. This step is strictly constrained by the retrieved context.
5.  **NLI Verification Layer**: This is the core of TruthLens's safety mechanism. The generated answer is treated as a "hypothesis." We use a Natural Language Inference (NLI) model to check for **semantic entailment** between the hypothesis and the source context.
    *   If the NLI model predicts **"entailment,"** the answer is considered factually consistent and is returned to the user.
    *   If the model predicts **"contradiction"** or **"neutral,"** the answer is deemed unverifiable. The system **abstains** from responding and flags the query for review, preventing the propagation of potentially incorrect information.
6.  **Output or Abstain**: The final, verified answer is delivered, or the system explicitly abstains, ensuring that no unverified information reaches the end-user.

## 3. Performance Metrics

System performance was evaluated on a test suite of 150 hand-authored compliance queries, designed to probe both in-domain knowledge and out-of-domain robustness.

| Metric | Value | Description |
| :--- | :--- | :--- |
| **In-Domain Accuracy** | `87%` | Percentage of correct, verified answers for queries within the legal corpus. |
| **Out-of-Domain Abstain Rate** | `94%` | Percentage of queries outside the corpus where the system correctly abstained. |
| **False Positive Rate (Hallucination)** | `<3%` | Rate at which the system provided an incorrect answer instead of abstaining. |
| **Average Latency** | `1.2s` | Average time from query submission to receiving a verified response or abstention. |

These metrics underscore the system's reliability and its deliberate design to fail safely.

## 4. Production Tooling & Enterprise Readiness

TruthLens is engineered with production-grade practices to ensure stability, maintainability, and scalability.

*   **Containerization**: The entire application stack (frontend, backend, vector database) is fully containerized using **Docker** and orchestrated with `docker-compose`. This guarantees consistent, reproducible deployments across development, staging, and production environments.
*   **Pre-Commit Hooks**: We enforce code quality and consistency automatically before any code is committed. Our pre-commit hooks run `black` for formatting, `flake8` for linting, and `isort` for import sorting, minimizing trivial errors and standardizing the codebase.
*   **CI/CD Workflow**: A robust Continuous Integration and Continuous Deployment (CI/CD) pipeline is configured using GitHub Actions. On every push to `main` or pull request, the pipeline automatically:
    1.  Builds Docker images.
    2.  Runs the full test suite (`pytest`).
    3.  Performs a security scan on dependencies.
    4.  (On merge) Deploys the updated containers to the target environment.

This automated workflow ensures that all changes are validated and deployed systematically, reflecting a mature approach to software development and AI systems engineering.
