#!/usr/bin/env bash
set -euo pipefail

model="${MODEL_NAME:-qwen2.5-coder:3b}"

if ! command -v ollama >/dev/null 2>&1; then
  curl --fail --show-error --silent --location https://ollama.com/install.sh | sh
fi

export OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"
export OLLAMA_NUM_PARALLEL="${OLLAMA_NUM_PARALLEL:-1}"

ollama serve >/tmp/ollama.log 2>&1 &

for attempt in {1..30}; do
  if curl --fail --silent "http://${OLLAMA_HOST}/api/tags" >/dev/null; then
    break
  fi

  if [[ "${attempt}" == "30" ]]; then
    cat /tmp/ollama.log
    echo "Ollama did not become ready." >&2
    exit 1
  fi

  sleep 2
done

ollama pull "${model}"
ollama list

