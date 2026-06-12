# ImmigrationNavigator — Merged Pipeline

UC Berkeley MIDS Capstone 2026
Team: Ale, Clover, Duc, Rohan

---

## Notebooks

| Notebook | Description | Based on |
|----------|-------------|----------|
| `1_data_collection.ipynb` | Scrape USCIS + AFM + Visa Bulletin + Federal Register → S3 | Clover's section parser + Ale's multi-source scraper |
| `2_eda.ipynb` | Token distributions, topic coverage, synonym analysis | Clover |
| `3_rag_pipeline.ipynb` | Chunking, embeddings, ChromaDB, RAG + benchmark | Both |
| `4_mvp_app.ipynb` | Gradio conversational UI | Ale |

## Files

| File | Description |
|------|-------------|
| `synonyms.py` | Query expansion: user terms → legal equivalents → forms | 

## Model Configuration

In Notebooks 3 and 4, set `USE_OPENAI` flag:

```python
USE_OPENAI = False  # Groq (free): FastEmbed + Llama 3.3 70B
USE_OPENAI = True   # OpenAI ($5): text-embedding-3-small + GPT-4o-mini
```

Run the benchmark in Notebook 3 Cell 9 with both settings and compare.

## Run Order

1. `1_data_collection.ipynb` — builds corpus in S3
2. `2_eda.ipynb` — optional, explore corpus
3. `3_rag_pipeline.ipynb` — builds vector store + benchmark
4. `4_mvp_app.ipynb` — launches Gradio UI

## AWS Requirements

- SageMaker JupyterLab space
- S3 bucket: `immigration-navigator-data`
- Secrets Manager: `immigration-navigator/groq` (and optionally `immigration-navigator/openai`)
- IAM role with S3 + Secrets Manager access
