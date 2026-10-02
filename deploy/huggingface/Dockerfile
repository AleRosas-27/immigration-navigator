# ImmigrationNavigator — Hugging Face Spaces (Docker) image
# Runs FastAPI (internal, port 8000) and Streamlit (public, port 7860) in one
# container, replacing the systemd + Nginx setup on EC2.

FROM python:3.11-slim

# Hugging Face runs Spaces as user 1000, so everything the app writes to
# (ChromaDB's sqlite file, Streamlit's config, the model cache) must be owned by it.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/home/user/app \
    USE_OPENAI=false \
    CHROMA_PATH=/home/user/app/chroma_db \
    FASTEMBED_CACHE_PATH=/home/user/fastembed_cache \
    API_URL=http://localhost:8000/ask \
    APP_PASSWORD= \
    ANONYMIZED_TELEMETRY=False

WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Download the embedding model at build time so the first visitor
# doesn't wait for it (same model the ChromaDB index was built with)
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')"

COPY --chown=user . .
RUN chmod +x start.sh

EXPOSE 7860
CMD ["./start.sh"]
