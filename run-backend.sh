#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/env.sh"

if [[ -z "${OPENAI_API_KEY:-}" || "$OPENAI_API_KEY" == *"PASTE"* || "$OPENAI_API_KEY" == *"paste"* || "$OPENAI_API_KEY" == "<"* ]]; then
    echo "ERROR: OPENAI_API_KEY is not configured. Edit $SCRIPT_DIR/env.sh with a real OpenAI API key." >&2
    exit 1
fi

if [[ -z "${MAILPILOT_API_TOKEN:-}" || "$MAILPILOT_API_TOKEN" == *"generate"* || "$MAILPILOT_API_TOKEN" == "<"* ]]; then
    echo "ERROR: MAILPILOT_API_TOKEN is not configured. Edit $SCRIPT_DIR/env.sh with a real API token." >&2
    exit 1
fi

exec "$SCRIPT_DIR/.venv-mailpilot/bin/uvicorn" app.main:app \
    --host 127.0.0.1 \
    --port 8082 \
    --workers 2
