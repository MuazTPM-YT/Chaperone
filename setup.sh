#!/usr/bin/env bash
# one-time setup: python deps, local model, .env with a fresh audit key
set -euo pipefail
cd "$(dirname "$0")"

command -v uv >/dev/null || { echo "need uv: https://docs.astral.sh/uv/"; exit 1; }
command -v ollama >/dev/null || { echo "need ollama: https://ollama.com (Arch: pacman -S ollama-cuda)"; exit 1; }
command -v npm >/dev/null || { echo "need Node.js 20.9 or newer with npm: https://nodejs.org"; exit 1; }
node -e 'const [a, b] = process.versions.node.split(".").map(Number); process.exit(a > 20 || (a === 20 && b >= 9) ? 0 : 1)' \
  || { echo "need Node.js 20.9 or newer, found $(node -v)"; exit 1; }
# installed is not running: pull needs the server
ollama list >/dev/null 2>&1 || {
  echo "ollama is installed but not running. Start it, then run ./setup.sh again:"
  echo "  Linux (service): sudo systemctl start ollama"
  echo "  Linux (no service) or macOS: ollama serve   (in another terminal), or open the Ollama app"
  exit 1
}

uv sync --frozen
ollama pull qwen2.5:3b
# warm the NER model cache so the demo runs offline
uv run --frozen python -c "from chaperone.detect import _gliner; _gliner()"
# the page: built once into web/out, which the gateway serves; nothing from Node runs after this
(cd web && npm ci && npm run build)

if [ ! -f .env ]; then
  key=$(uv run --frozen python -c "import secrets; print(secrets.token_hex(32))")
  sed "s/^AUDIT_HMAC_KEY=.*/AUDIT_HMAC_KEY=$key/" .env.example > .env
  echo "wrote .env with a new audit key"
fi
echo "done. start with: uv run --frozen python -m chaperone"
