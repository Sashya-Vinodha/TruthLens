# TruthLens: Enterprise-Grade Retrieval-Augmented Verification (RAG+V)

> **Research Publication Impact:** This architecture expands on the foundational real-time system paradigms published in my peer-reviewed paper: *"Development of a Multi-Module AI Infotainment System for Real-Time Assistance and Control"* (International Journal, Issue - May 2026).

TruthLens is an advanced RAG Guardrail and factual verification system designed to reduce hallucinations and enforce strict epistemic boundaries in Large Language Model (LLM) pipelines. 

**TruthLens was developed to address a critical limitation of modern LLM systems: the tendency to generate confident answers even when supporting evidence is weak, missing, or entirely outside the system's knowledge boundary.**

**Unlike standard RAG architectures that blindly trust the generator layer, TruthLens treats generated answers as unverified hypotheses.** It evaluates generations against retrieved documents using an independent **Natural Language Inference (NLI)** verification engine before passing responses to the application layer.

---

## 🏗️ Core Architectural Features

### 1. Natural Language Inference (NLI) Verifier Engine
* **Semantic Cross-Examination:** Evaluates the LLM's generated response against retrieved reference documents.
* **Cross-Encoder Alignment:** Uses an external Cross-Encoder NLI model to assign classification scores for `ENTAILMENT`, `NEUTRAL`, and `CONTRADICTION` against the source text.

### 2. Four-Level Stratified Evidence Taxonomy
TruthLens moves away from simplistic binary "correct/incorrect" flags, implementing an enterprise-grade taxonomy that classifies the exact nature of the response generation:
* 🎯 **Direct Evidence:** Explicit, verbatim, or near-verbatim textual backing within the dataset.
* 🔗 **Inferred From Sources:** The answer is synthetically accurate, representing a valid logical abstraction or cross-document reasoning.
* ⚠️ **Contradicted / Unsupported:** Conflicting facts or unbacked claims detected; automatically triggers a secure system fallback.
* ⚪ **Out Of Corpus:** The engine detects that the query targets concepts completely outside the active knowledge domain, triggering a graceful refusal.

### 3. Epistemic Humility (Corpus Boundary Enforcement)
* **Corpus Boundary Enforcement:** Prevents out-of-domain hallucinations through semantic topic matching and retrieval boundary checks. 
* **Automatic Fallback:** Automatically abstains when user queries fall outside the active knowledge domain, dynamically dropping irrelevant source tracking.

### 4. Deterministic Audit Trail UI
* A responsive, scannable React frontend that visualizes safety badges (`Safe (Boundary Enforced)`, `Safe (No Contradictions)`, `Blocked`).
* Renders exact reference documentation snippets to ensure human-in-the-loop auditability.

---

### Architecture Flow

```mermaid
graph TD
    A[User Query] --> B(Retriever: FAISS + BGE Embeddings)
    B --> C(Cross-Encoder Reranker)
    C --> D[Top-K Evidence Chunks]
    D --> E(Gemini API Generator)
    E --> F[Generated Response]
    F --> G{NLI Verifier Engine}
    G -->|CONTRADICTION| H[🛑 Blocked]
    G -->|OUT OF CORPUS| I[⚪ Abstain / Refuse]
    G -->|SUPPORTED| J[🟢 Return Validated Answer]
    H --> K((React Audit UI))
    I --> K
    J --> K
```

## 🛠️ Tech Stack

**Backend & Verification Engine:**
* FastAPI (Python)
* FAISS Vector Search
* SentenceTransformers & BGE-Large Embeddings
* Cross-Encoder Reranking
* NLI Verification Layer

**Frontend UI:**
* React (JavaScript) & TailwindCSS
* Markdown Rendering
* Evidence Classification UI

**LLM Core:**
* Gemini API
* Retrieval-Augmented Generation (RAG) Pipeline

---

## 🚀 Rapid Verification Benchmarks (The UI Test)

The system routing logic handles three distinct epistemic states:

### Test A: Direct & Synthesized Knowledge (NIST Frameworks)
* **Query:** *"What are the seven trustworthiness characteristics of AI systems?"*
* **System Action:** Retrieves documentation, evaluates alignment score thresholds, and outputs a `🟢 Safe` + `🔗 Inferred From Sources` or `🎯 Direct Evidence` token payload.

### Test B: Strict Boundary Enforcement (Off-Topic Mitigation)
* **Query:** *"What are the SEC compliance regulations for using AI in cryptocurrency trading?"*
* **System Action:** Intercepts out-of-corpus parameters, flags `final_abstain = True`, and updates the response layout to `⚪ Out Of Corpus` with clean audit-trail dismissal.

### Test C: Hallucination & Contradiction Blocking
* **Query:** *"According to the documents, is it acceptable for an AI system to bypass safety protocols to improve performance?"*
* **System Action:** NLI Verifier extracts claims, detects a logical `CONTRADICTION` against the retrieved NIST guidelines, triggers the secure fallback protocol, and renders a `🛑 Blocked (Hallucination Detected)` state.