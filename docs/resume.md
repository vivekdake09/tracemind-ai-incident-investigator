# TraceMind — Résumé Entry

**Project Title:** TraceMind — AI Production Incident Investigator  
**One-Sentence Description:** A grounded Retrieval-Augmented Generation (RAG) diagnostic engine and Streamlit developer console that investigates production application failures by cross-referencing application logs, traces, and runbooks against historical incidents.

---

### Résumé Bullet Points (GenAI Engineer / AI Systems Focus)

- **Architected an Evidence-Grounded Incident Investigator:** Built an end-to-end RAG system in Python using ChromaDB vector search and `sentence-transformers/all-MiniLM-L6-v2` dense embeddings across 8 synthetic incident postmortems and 5 engineering runbooks; implemented code-level citation validation that rejects hallucinated IDs, achieving **100.0% evidence support rate** and **100.0% Recall@5** on a 7-scenario benchmark.
- **Implemented Structured Outputs & Safe Tool Execution:** Engineered strict Pydantic schemas enforcing up to three ranked root-cause hypotheses with qualitative confidence levels (High/Medium/Low), pairing Groq LLM inference with a whitelisted diagnostic dispatch engine (error signatures, config keys, regex matching) verified by a 27-test automated `pytest` suite with **100.0% schema validity**.
- **Engineered Production Safety & Benchmarking Harness:** Developed client-side credential scrubbing (redacting Bearer tokens, DB connection strings, and passwords before transmission), prompt boundary fences against injection, and an automated evaluation suite measuring **100.0% Top-1 diagnosis accuracy** and **100.0% abstention accuracy** on uncatalogued failure scenarios.

---

*Note on Portfolio Scope: Built as an open-source portfolio project and personal engineering demonstration using synthetic incident postmortems and controlled evaluation benchmarks.*
