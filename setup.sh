#!/usr/bin/env bash
# one-time setup: python deps, local model, .env with a fresh audit key
set -euo pipefail
cd "$(dirname "$0")"

command -v uv >/dev/null || { echo "need uv: https://docs.astral.sh/uv/"; exit 1; }
command -v ollama >/dev/null || { echo "need ollama: https://ollama.com (Arch: pacman -S ollama-cuda)"; exit 1; }

uv sync
ollama pull qwen2.5:3b
# warm the NER model cache so the demo runs offline
uv run python -c "from flowguard.detect import _gliner; _gliner()"

if [ ! -f .env ]; then
  key=$(uv run python -c "import secrets; print(secrets.token_hex(32))")
  sed "s/^AUDIT_HMAC_KEY=.*/AUDIT_HMAC_KEY=$key/" .env.example > .env
  echo "wrote .env with a new audit key"
fi
echo "done. start with: uv run flowguard"
