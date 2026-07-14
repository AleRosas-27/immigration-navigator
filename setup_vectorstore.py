"""
ImmigrationNavigator — Vector Store Setup
===========================================
UC Berkeley MIDS Capstone 2026

One-time script to populate ChromaDB with embeddings.
Run this once after cloning the repo on a new machine (e.g. EC2).

The pipeline is idempotent — if the collection already has chunks,
it skips re-embedding (same guard used in Notebook 3).

Usage:
    python3 setup_vectorstore.py
"""

import os
import re
import json
import uuid
import boto3
from datetime import datetime

from langchain.schema import Document

# ── Configuration — matches src/rag.py ──────────────────────────────────────
USE_OPENAI       = os.getenv("USE_OPENAI", "false").lower() == "true"
S3_BUCKET        = os.getenv("S3_BUCKET", "immigration-navigator-data")
CHROMA_PATH      = os.getenv("CHROMA_PATH", "./chroma_db")
COLLECTION_NAME  = f"immigration_nav_{'openai' if USE_OPENAI else 'groq'}"


def get_secret(secret_name: str) -> dict:
    """Load a secret from AWS Secrets Manager."""
    client = boto3.client("secretsmanager", region_name="us-east-1")
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])


def clean_text(text: str) -> str:
    """Remove USCIS navigation boilerplate from scraped HTML text."""
    patterns = [
        r'Policy Manual\s*\n.*?Feedback',
        r'USCIS-PM\s*\n.*?Volume \d+.*?\n',
        r'Affected Sections.*?Volume \d+.*?\n',
        r'Skip to main content.*?secure websites\.',
        r'Countdown to America.*?Minutes',
        r'An official website.*?HTTPS',
        r'\d+\s*USCIS-PM\s*-\s*\n',
        r'Contents\s*\nUpdates\s*\nINA\s*\n8 CFR',
        r'8 CFR \d+\.\d+.*?\n',
        r'INA \d+.*?\n',
    ]
    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
    lines = [l for l in text.split('\n') if len(l.split()) >= 4]
    text = '\n'.join(lines)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def main():
    print(f"Setting up vector store: {COLLECTION_NAME}")
    print(f"  USE_OPENAI  : {USE_OPENAI}")
    print(f"  S3_BUCKET   : {S3_BUCKET}")
    print(f"  CHROMA_PATH : {CHROMA_PATH}")
    print()

    # ── Step 1 — Load API keys ────────────────────────────────────────────
    if USE_OPENAI:
        if not os.getenv("OPENAI_API_KEY"):
            secrets = get_secret("immigration-navigator/openai")
            os.environ["OPENAI_API_KEY"] = secrets["OPENAI_API_KEY"]
    else:
        if not os.getenv("GROQ_API_KEY"):
            secrets = get_secret("immigration-navigator/groq")
            os.environ["GROQ_API_KEY"] = secrets["GROQ_API_KEY"]

    # ── Step 2 — Load corpus from S3 ──────────────────────────────────────
    print("Loading corpus from S3...")
    s3 = boto3.client("s3", region_name="us-east-1")
    response = s3.get_object(Bucket=S3_BUCKET, Key="raw_docs.json")
    all_docs = json.loads(response["Body"].read().decode("utf-8"))
    good_docs = [d for d in all_docs if d["word_count"] > 200]
    print(f"  Loaded {len(all_docs)} docs, {len(good_docs)} ready for RAG")

    # Fix mislabeled docs from older corpus versions
    label_fixes = {
        "opt_overview": "adj_status_overview",
        "opt_chapter1": "adj_status_ch1",
        "opt_chapter2": "adj_status_ch2",
        "opt_chapter3": "adj_status_ch3",
        "opt_chapter4": "adj_status_ch4",
        "opt_chapter5": "adj_status_ch5",
        "f1_chapter5":  "opt_and_stem_opt",
    }
    for d in good_docs:
        if d["label"] in label_fixes:
            d["label"] = label_fixes[d["label"]]

    # ── Step 3 — Clean and chunk ───────────────────────────────────────────
    print("Cleaning and chunking...")
    lc_docs = []
    for d in good_docs:
        clean = clean_text(d["text"])
        if len(clean.split()) > 100:
            lc_docs.append(Document(
                page_content=clean,
                metadata={"source": d["source"], "label": d["label"], "url": d.get("url", "")}
            ))

    try:
        from llama_index.core.node_parser import SentenceSplitter as LlamaSplitter
        from llama_index.core import Document as LlamaDoc
        splitter = LlamaSplitter(chunk_size=512, chunk_overlap=64)
        llama_docs = [LlamaDoc(text=d.page_content, metadata=d.metadata) for d in lc_docs]
        nodes = splitter.get_nodes_from_documents(llama_docs)
        chunks = [Document(page_content=n.text, metadata=n.metadata) for n in nodes]
        print("  Using LlamaIndex SentenceSplitter")
    except ImportError:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800, chunk_overlap=150,
            separators=["\n\n", "\n", ". ", " "]
        )
        chunks = splitter.split_documents(lc_docs)
        print("  Using LangChain RecursiveCharacterTextSplitter (fallback)")

    chunks = [c for c in chunks if len(c.page_content.split()) > 50]
    print(f"  {len(chunks)} chunks ready (avg "
          f"{sum(len(c.page_content.split()) for c in chunks) // len(chunks)} words)")

    # ── Step 4 — Embed and insert into ChromaDB ───────────────────────────
    print("\nInitializing embedding model...")
    if USE_OPENAI:
        from langchain_openai import OpenAIEmbeddings
        embed_fn = OpenAIEmbeddings(model="text-embedding-3-small")
        def get_embedding(texts): return embed_fn.embed_documents(texts)
    else:
        from fastembed import TextEmbedding
        embed_model = TextEmbedding("BAAI/bge-small-en-v1.5")
        def get_embedding(texts): return [e.tolist() for e in embed_model.embed(texts)]

    import chromadb
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    if collection.count() > 0:
        print(f"\nCollection already has {collection.count()} chunks — skipping insert.")
        print("Delete the chroma_db folder and re-run if you want to rebuild from scratch.")
        return

    print(f"\nEmbedding and inserting {len(chunks)} chunks...")
    BATCH_SIZE = 50
    docs_text = [c.page_content for c in chunks]
    docs_meta = [c.metadata for c in chunks]
    ids = [str(uuid.uuid4()) for _ in chunks]

    for i in range(0, len(chunks), BATCH_SIZE):
        embeddings = get_embedding(docs_text[i:i + BATCH_SIZE])
        collection.add(
            documents=docs_text[i:i + BATCH_SIZE],
            embeddings=embeddings,
            metadatas=docs_meta[i:i + BATCH_SIZE],
            ids=ids[i:i + BATCH_SIZE]
        )
        if (i // BATCH_SIZE) % 5 == 0:
            print(f"  {min(i + BATCH_SIZE, len(chunks))}/{len(chunks)} chunks")

    print(f"\nDone — {collection.count()} chunks in '{COLLECTION_NAME}'")
    print(f"Vector store saved to: {CHROMA_PATH}")


if __name__ == "__main__":
    main()
