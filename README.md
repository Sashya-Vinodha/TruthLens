# 🔍 TruthLens — Verified AI, Not Just Generated AI

## 🚀 Overview
TruthLens is a domain-specific AI system designed to verify information instead of blindly generating answers.  
Unlike typical AI models that may hallucinate, TruthLens only responds when it finds relevant and supported evidence in its dataset.

---

## 🧠 Key Idea
> “An AI system should know when NOT to answer.”

TruthLens ensures reliability by combining:
- Retrieval of relevant documents
- Topic relevance filtering
- Evidence-based answer generation
- Strict verification before responding

If sufficient support is not found, the system abstains instead of guessing.

---

## ⚙️ How It Works

1. Query Processing
   - Cleans and normalizes user input
   - Handles variations, casing, and noise

2. Retrieval (RAG)
   - Fetches relevant documents from a curated dataset

3. Topic Matching
   - Ensures the query is actually related to retrieved content

4. Answer Generation
   - Generates response ONLY from retrieved context

5. Verification Layer
   - Validates claims using evidence
   - Assigns confidence score

6. Final Decision
   - Answer OR Abstain

---

## 📊 Features

- ✅ No hallucination responses  
- ✅ Domain-specific intelligence  
- ✅ Handles paraphrased queries  
- ✅ Corrects wrong assumptions  
- ✅ Robust to noisy inputs  
- ✅ Confidence-based output  
- ❌ Refuses out-of-domain queries  

---

## 📚 Dataset

The system uses a controlled dataset focused on:
- Indian Corporate Laws (Companies Act, CSR, etc.)
- Financial Regulations (SEBI, compliance rules)
- Labour Laws (Gratuity, Wages, etc.)

### Why a Limited Dataset?
- Runs efficiently on local systems  
- Reduces irrelevant noise  
- Improves accuracy and reliability  
- Avoids hallucinated responses  

---

## 🧪 Example Behaviors

| Query Type | Example | Output |
|----------|--------|--------|
| Valid | What is SEBI? | ✅ Answer |
| Paraphrase | Role of SEBI | ✅ Answer |
| Wrong assumption | Is Companies Act from 2020? | ✅ Corrected |
| Out-of-domain | Who is Elon Musk? | ❌ Abstain |

---

## 🛠️ Tech Stack

- Backend: FastAPI  
- Frontend: React (Vite)  
- Retrieval: Sentence-BERT / embeddings  
- Verification: NLI-based validation  
- Architecture: RAG + Guardrails  

---

## 💡 Real-World Applications

- Corporate compliance verification  
- Legal and regulatory research  
- Financial decision support  
- Education and learning systems  

TruthLens helps reduce manual effort and ensures accurate, evidence-based decisions.

---

## 🔮 Future Scope

- Scale to cloud infrastructure (AWS, etc.)
- Integrate larger domain-specific datasets
- Use vector databases (FAISS / Pinecone)
- Deploy as API or enterprise tool
- Extend to domains like healthcare & finance

---

## 🎯 Goal

To build AI systems that are:
> Not just intelligent — but trustworthy

---
