#!/usr/bin/env bash
# Start the API in the background, wait until it's healthy, then run the UI.
set -e

if [ -z "$GROQ_API_KEY" ]; then
  echo "ERROR: GROQ_API_KEY is not set. Add it under Space Settings → Variables and secrets."
  exit 1
fi

uvicorn src.api:app --host 127.0.0.1 --port 8000 &
API_PID=$!

echo "Waiting for API to load the RAG pipeline..."
for i in $(seq 1 90); do
  if python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)" 2>/dev/null; then
    echo "API is up."
    break
  fi
  if ! kill -0 "$API_PID" 2>/dev/null; then
    echo "ERROR: API process exited during startup — see logs above."
    exit 1
  fi
  sleep 2
done

exec streamlit run ui_streamlit.py \
  --server.port 7860 \
  --server.address 0.0.0.0 \
  --server.headless true \
  --server.enableXsrfProtection false \
  --browser.gatherUsageStats false
