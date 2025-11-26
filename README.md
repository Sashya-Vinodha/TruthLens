TruthLens — A Lightweight RAG Verification Engine

TruthLens is a Retrieval-Augmented Generation (RAG) system built with a focus on truthfulness, source attribution, and claim verification.
It retrieves documents, generates an answer with citations, and then verifies each factual claim using semantic similarity + NLI (Natural Language Inference).

This ensures the model does not hallucinate and outputs “I abstain — evidence insufficient” when the dataset does not support an answer.

TruthLens/
│
├── truthlens/
│   └── backend/
│       └── app/
│            ├── indexer.py
│            ├── retriever.py
│            ├── generator.py
│            ├── verifier.py
│            ├── fusion.py
│            ├── main.py     ← FastAPI backend
│   └── frontend/
│       └── public/
│            └── index.html  ← simple UI
│
├── scripts/
│   ├── build_index.py       ← converts docs.json → docs.pkl
│   ├── run_dev.sh
│   ├── run_dev.ps1
│
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md

