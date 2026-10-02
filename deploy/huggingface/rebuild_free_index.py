"""
Build a free (FastEmbed) copy of the vector store from an existing one.

Reads every chunk's text + metadata from the OpenAI-embedded collection and
re-embeds it with FastEmbed (BAAI/bge-small-en-v1.5, the model src/rag.py uses
when USE_OPENAI=false) into a NEW folder. The original chroma_db — and the
live site using it — is never modified.

Usage:
    python deploy/huggingface/rebuild_free_index.py \
        --source ~/immigration-navigator/chroma_db --dest ~/chroma_db_hf
"""

import argparse
import sys
from pathlib import Path

import chromadb
from fastembed import TextEmbedding

SOURCE_COLLECTION = "immigration_nav_openai"
DEST_COLLECTION = "immigration_nav_groq"
BATCH = 64


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--dest", required=True)
    args = ap.parse_args()

    src_path = Path(args.source).expanduser().resolve()
    dest_path = Path(args.dest).expanduser().resolve()
    if dest_path == src_path:
        sys.exit("ERROR: --dest must be a different folder than --source.")
    if dest_path.exists() and any(dest_path.iterdir()):
        sys.exit(f"ERROR: {dest_path} already exists and isn't empty — "
                 "delete it or choose another --dest.")

    src = chromadb.PersistentClient(path=str(src_path)).get_collection(SOURCE_COLLECTION)
    total = src.count()
    print(f"Source: {total} chunks in '{SOURCE_COLLECTION}' (read-only)")

    data = src.get(include=["documents", "metadatas"])
    ids, docs, metas = data["ids"], data["documents"], data["metadatas"]
    if len(ids) != total or any(d is None for d in docs):
        sys.exit("ERROR: couldn't read every chunk's text from the source.")

    model = TextEmbedding("BAAI/bge-small-en-v1.5")
    dest = chromadb.PersistentClient(path=str(dest_path)).get_or_create_collection(
        DEST_COLLECTION, metadata={"hnsw:space": "cosine"})

    for i in range(0, total, BATCH):
        batch_docs = docs[i:i + BATCH]
        dest.add(
            ids=ids[i:i + BATCH],
            documents=batch_docs,
            metadatas=metas[i:i + BATCH],
            embeddings=[e.tolist() for e in model.embed(batch_docs)],
        )
        done = min(i + BATCH, total)
        if done % (BATCH * 8) == 0 or done == total:
            print(f"  {done}/{total}")

    print(f"\nDone — {dest.count()} chunks in '{DEST_COLLECTION}' at {dest_path}")
    if dest.count() != total:
        sys.exit("ERROR: chunk count doesn't match the source.")


if __name__ == "__main__":
    main()
