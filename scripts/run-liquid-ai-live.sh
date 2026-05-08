#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL_NAME="${LIQUID_OLLAMA_MODEL:-liquidai-lfm2-transcript:q4km}"
MODELFILE="${LIQUID_MODELFILE:-$ROOT_DIR/Modelfile.liquidai-lfm2-transcript}"
OLLAMA_MODELS="${OLLAMA_MODELS:-/Volumes/qbitOS/03.models/01-ollama}"
OLLAMA_ORIGIN_LIST="${OLLAMA_ORIGINS:-http://localhost:4321,http://127.0.0.1:4321,http://localhost:4322,http://127.0.0.1:4322}"
OLLAMA_LOG="${LIQUID_OLLAMA_LOG:-$ROOT_DIR/.liquid-ai-ollama.log}"

export OLLAMA_MODELS

if ! command -v ollama >/dev/null 2>&1; then
	echo "error: ollama is not installed or not on PATH" >&2
	exit 1
fi

if ! ollama list >/dev/null 2>&1; then
	echo "Starting Ollama with browser origins for the Train tuning desk..."
	OLLAMA_ORIGINS="$OLLAMA_ORIGIN_LIST" OLLAMA_MODELS="$OLLAMA_MODELS" ollama serve >"$OLLAMA_LOG" 2>&1 &
	sleep 3
fi

if [[ "${LIQUID_RECREATE_MODEL:-0}" == "1" ]] || ! ollama list | awk -v model="$MODEL_NAME" '$1 == model { found = 1 } END { exit found ? 0 : 1 }'; then
	echo "Creating $MODEL_NAME from $MODELFILE ..."
	ollama create "$MODEL_NAME" -f "$MODELFILE"
fi

echo "LiquidAI model ready: $MODEL_NAME"
echo "Open Train at http://localhost:4321/models/liquid-ai/ after Astro starts."
echo

LIQUID_OLLAMA_MODEL="$MODEL_NAME" npm run dev
