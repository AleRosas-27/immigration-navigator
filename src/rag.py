"""
ImmigrationNavigator — RAG Pipeline
=====================================
UC Berkeley MIDS Capstone 2026

This module contains the full RAG pipeline extracted from Notebook 3.
Import this in api.py to power the backend.

Usage:
    from src.rag import ask, initialize

    initialize()  # call once at startup
    answer = ask("When do I apply for OPT?", profile)
"""

import os
import json
import uuid
import boto3
from typing import Optional

from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from fastembed import TextEmbedding
import chromadb

# ── Configuration ──────────────────────────────────────────────────────────────

# Set USE_OPENAI = True to use OpenAI embeddings + GPT-4o-mini
# Set USE_OPENAI = False to use FastEmbed + Groq Llama 3.3 70B (free)
USE_OPENAI = os.getenv("USE_OPENAI", "false").lower() == "true"

S3_BUCKET      = os.getenv("S3_BUCKET", "immigration-navigator-data")
CHROMA_PATH    = os.getenv("CHROMA_PATH", "./chroma_db")
COLLECTION_NAME = f"immigration_nav_{'openai' if USE_OPENAI else 'groq'}"

# Topic terms for relevance reranking
RELEVANT_TERMS = [
    "f-1", "f1", "opt", "stem opt", "h-1b", "h1b", "cap-gap",
    "ead", "employment authorization", "sevis", "dso", "i-765", "i-983",
]
IRRELEVANT_TERMS = [
    "j-1", "j1", "b-1", "b1", "h-2b", "l-1", "o-1",
    "adjustment of status", "naturalization", "green card",
]

# ── Module-level singletons (initialized once at startup) ──────────────────────

_embedding_model = None
_collection      = None
_llm             = None
_has_synonyms    = False

# ── Prompt ─────────────────────────────────────────────────────────────────────

PROMPT = ChatPromptTemplate.from_template("""
You are ImmigrationNavigator, an AI assistant helping international students
navigate U.S. visa processes. Answer ONLY using the provided context.
Cite every claim with [Source: label, url].
If context is insufficient, say:
"I don't have enough information. Please consult your ISO or an immigration attorney."

User Profile:
- Visa status: {visa_status}
- Degree field: {degree_field}
- Graduation date: {graduation_date}
- Employer type: {employer_type}

Context:
{context}

Question: {question}

Answer (personalized, cite every claim):
""")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_secret(secret_name: str) -> dict:
    """Load a secret from AWS Secrets Manager."""
    client = boto3.client("secretsmanager", region_name="us-east-1")
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])


def _get_embedding(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts using the configured embedding model."""
    global _embedding_model
    if USE_OPENAI:
        from langchain_openai import OpenAIEmbeddings
        model = OpenAIEmbeddings(model="text-embedding-3-small")
        return model.embed_documents(texts)
    else:
        return [e.tolist() for e in _embedding_model.embed(texts)]


def _expand_query(query: str) -> str:
    """Expand query using synonym registry if available."""
    global _has_synonyms
    if _has_synonyms:
        try:
            from synonyms import expand_query
            return expand_query(query)
        except Exception:
            pass
    return query


def _rerank(docs: list, metas: list, distances: list) -> list[tuple]:
    """
    Topic-aware reranking.
    Boosts chunks mentioning F-1/OPT/H-1B terms.
    Penalizes chunks mentioning irrelevant visa categories.
    Returns sorted list of (score, doc, meta) tuples.
    """
    reranked = []
    for doc, meta, dist in zip(docs, metas, distances):
        score      = 1 - dist
        text_lower = doc.lower()
        rel = sum(1 for t in RELEVANT_TERMS   if t in text_lower)
        irr = sum(1 for t in IRRELEVANT_TERMS if t in text_lower)
        if rel > 0:
            score *= min(1.0 + 0.1 * rel, 1.5)
        if irr > 0:
            score *= max(0.7 ** irr, 0.2)
        reranked.append((score, doc, meta))
    reranked.sort(key=lambda x: x[0], reverse=True)
    return reranked


# ── Public API ─────────────────────────────────────────────────────────────────

def initialize():
    """
    Initialize all pipeline components.
    Call this once at application startup — not on every request.

    Loads:
    - Embedding model (FastEmbed or OpenAI)
    - ChromaDB vector store
    - Groq or OpenAI LLM
    - synonyms.py query expander (optional)
    """
    global _embedding_model, _collection, _llm, _has_synonyms

    # Load API keys from environment or Secrets Manager
    if USE_OPENAI:
        if not os.getenv("OPENAI_API_KEY"):
            secrets = _get_secret("immigration-navigator/openai")
            os.environ["OPENAI_API_KEY"] = secrets["OPENAI_API_KEY"]
        from langchain_openai import ChatOpenAI
        _llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        print("Using OpenAI (text-embedding-3-small + GPT-4o-mini)")
    else:
        if not os.getenv("GROQ_API_KEY"):
            secrets = _get_secret("immigration-navigator/groq")
            os.environ["GROQ_API_KEY"] = secrets["GROQ_API_KEY"]
        _embedding_model = TextEmbedding("BAAI/bge-small-en-v1.5")
        _llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.environ["GROQ_API_KEY"],
            temperature=0
        )
        print("Using Groq (FastEmbed + Llama 3.3 70B)")

    # Connect to ChromaDB
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    _collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )
    print(f"ChromaDB: {_collection.count()} chunks in '{COLLECTION_NAME}'")

    # Load synonyms expander
    try:
        import synonyms  # noqa
        _has_synonyms = True
        print("synonyms.py loaded")
    except ImportError:
        _has_synonyms = False
        print("⚠️  synonyms.py not found — running without query expansion")


def ask(question: str, profile: dict, n_results: int = 5) -> str:
    """
    Full RAG pipeline with synonym expansion, situation-aware retrieval,
    topic reranking, and citation-enforced generation.

    Args:
        question  (str) : User's natural language question.
        profile   (dict): Keys: visa_status, degree_field,
                          graduation_date, employer_type.
        n_results (int) : Number of chunks to retrieve before reranking.

    Returns:
        str: Cited, personalized answer from the LLM.

    Raises:
        RuntimeError: If initialize() has not been called.
    """
    if _collection is None or _llm is None:
        raise RuntimeError("Pipeline not initialized. Call initialize() first.")

    # Step 1 — Synonym expansion + profile injection
    expanded = _expand_query(question)
    enriched = (
        f"{expanded} | "
        f"visa: {profile.get('visa_status', '')} | "
        f"degree: {profile.get('degree_field', '')} | "
        f"employer: {profile.get('employer_type', '')}"
    )

    # Step 2 — Embed and retrieve
    embeddings = _get_embedding([enriched])
    results = _collection.query(
        query_embeddings=embeddings,
        n_results=n_results,
        include=["documents", "metadatas", "distances"]
    )

    # Step 3 — Topic reranking
    reranked = _rerank(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    )

    # Step 4 — Build context
    context = "\n\n".join([
        f"[Source: {meta['label']}, {meta.get('url', '')}]\n{doc}"
        for _, doc, meta in reranked
    ])

    # Step 5 — Generate cited answer
    chain    = PROMPT | _llm
    response = chain.invoke({
        "context":         context,
        "question":        question,
        "visa_status":     profile.get("visa_status",     "F-1"),
        "degree_field":    profile.get("degree_field",    "Not specified"),
        "graduation_date": profile.get("graduation_date", "Not specified"),
        "employer_type":   profile.get("employer_type",   "Not specified"),
    })
    return response.content
