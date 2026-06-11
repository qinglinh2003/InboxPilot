#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/env.sh"

exec "$SCRIPT_DIR/.venv-mailpilot/bin/uvicorn" app.main:app \
    --host 127.0.0.1 \
    --port 8082 \
    --workers 2
