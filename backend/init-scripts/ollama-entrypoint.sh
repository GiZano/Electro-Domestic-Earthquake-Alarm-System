#!/bin/sh
# Ollama container entrypoint.
# Starts the Ollama server and ensures the configured model is present locally.
# `ollama pull` is a no-op when the model already exists in the volume, so this
# is safe to run on every container start.
set -e

ollama serve &
SERVER_PID=$!

# Wait for the server socket to come up before pulling the model.
until ollama list >/dev/null 2>&1; do
  sleep 1
done

echo "[Ollama] Pulling model: ${OLLAMA_MODEL}"
ollama pull "${OLLAMA_MODEL}"
echo "[Ollama] Model ready: ${OLLAMA_MODEL}"

wait "${SERVER_PID}"
