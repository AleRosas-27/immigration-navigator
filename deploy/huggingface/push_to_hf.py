"""
Push ImmigrationNavigator to a Hugging Face Space.

Run this on the EC2 box (it has the built ChromaDB index and the exact
library versions that built it). It assembles a clean copy of the app,
pins chromadb/fastembed to the versions installed here, and uploads
everything — including the vector store — to the Space.

Usage (from the repo root, inside the same Python env the app uses):
    pip install huggingface_hub
    python deploy/huggingface/push_to_hf.py --space YOUR_HF_USERNAME/immigration-navigator \
        --chroma ../immigration-navigator/chroma_db

Auth: run `huggingface-cli login` first, or set HF_TOKEN.
"""

import argparse
import shutil
import sys
import tempfile
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEPLOY_DIR = Path(__file__).resolve().parent
APP_FILES = ["src", "synonyms.py", "ui_streamlit.py", "assets"]
DEPLOY_FILES = ["Dockerfile", "start.sh", "README.md"]


def pinned_requirements() -> str:
    lines = []
    for line in (DEPLOY_DIR / "requirements.txt").read_text().splitlines():
        name = line.strip()
        if name in ("chromadb", "fastembed"):
            try:
                line = f"{name}=={version(name)}"
            except PackageNotFoundError:
                sys.exit(f"ERROR: {name} isn't installed in this Python env — "
                         "run this with the same env the app uses on EC2.")
        lines.append(line)
    return "\n".join(lines) + "\n"


def check_vector_store(chroma_path: Path) -> int:
    """Open the index with the installed chromadb to confirm it's readable."""
    import chromadb
    client = chromadb.PersistentClient(path=str(chroma_path))
    col = client.get_collection("immigration_nav_groq")
    return col.count()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--space", required=True, help="e.g. rohan/immigration-navigator")
    ap.add_argument("--chroma", required=True, help="path to the built chroma_db folder")
    args = ap.parse_args()

    chroma_path = Path(args.chroma).expanduser().resolve()
    if not chroma_path.is_dir():
        sys.exit(f"ERROR: {chroma_path} not found.")

    count = check_vector_store(chroma_path)
    print(f"Vector store OK: {count} chunks in 'immigration_nav_groq'")
    if count == 0:
        sys.exit("ERROR: collection is empty — refusing to upload.")

    reqs = pinned_requirements()
    print("Pinned versions:\n  " + "\n  ".join(
        l for l in reqs.splitlines() if l.startswith(("chromadb", "fastembed"))))

    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "space"
        stage.mkdir()
        for name in APP_FILES:
            src = REPO_ROOT / name
            if src.is_dir():
                shutil.copytree(src, stage / name,
                                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            else:
                shutil.copy2(src, stage / name)
        for name in DEPLOY_FILES:
            shutil.copy2(DEPLOY_DIR / name, stage / name)
        (stage / "requirements.txt").write_text(reqs)
        shutil.copytree(chroma_path, stage / "chroma_db")

        from huggingface_hub import HfApi
        api = HfApi()
        api.create_repo(args.space, repo_type="space", space_sdk="docker", exist_ok=True)
        print(f"Uploading to https://huggingface.co/spaces/{args.space} ...")
        api.upload_folder(
            repo_id=args.space,
            repo_type="space",
            folder_path=str(stage),
            commit_message="Deploy ImmigrationNavigator",
        )

    print("\nDone. Next: add GROQ_API_KEY as a secret in the Space settings.")
    print("The site is public by default; add an APP_PASSWORD secret to lock it.")


if __name__ == "__main__":
    main()
