#!/usr/bin/env bash
# ============================================================================
# MailPilot — Start backend + frontend (local dev mode)
#
# Sources env.sh, then launches both servers.
# Press Ctrl+C to stop both.
#
# Usage:  bash start.sh
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'

# ── Load environment ──────────────────────────────────────────────────────
if [[ ! -f env.sh ]]; then
    echo -e "${RED}[ERROR]${NC} env.sh not found. Run 'bash configure.sh' first."
    exit 1
fi

source "$SCRIPT_DIR/env.sh"
echo -e "${CYAN}[INFO]${NC}  Environment loaded from env.sh"

# ── Trap: clean shutdown ──────────────────────────────────────────────────
cleanup() {
    echo ""
    echo -e "${CYAN}[INFO]${NC}  Shutting down..."
    kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
    echo -e "${GREEN}[ OK ]${NC}  All servers stopped."
}
trap cleanup EXIT INT TERM

# ── Start backend ─────────────────────────────────────────────────────────
echo -e "${CYAN}[INFO]${NC}  Starting backend on http://localhost:8000 ..."
cd "$SCRIPT_DIR/backend"
python3 -m uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# ── Start frontend ────────────────────────────────────────────────────────
echo -e "${CYAN}[INFO]${NC}  Starting frontend on https://localhost:3000 ..."
cd "$SCRIPT_DIR/outlook-addin"
npm run dev &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}══════════════════════════════════════════${NC}"
echo -e "${GREEN}  Backend:   http://localhost:8000${NC}"
echo -e "${GREEN}  Frontend:  https://localhost:3000${NC}"
echo -e "${GREEN}  Press Ctrl+C to stop both servers.${NC}"
echo -e "${GREEN}══════════════════════════════════════════${NC}"
echo ""

# Wait for either process to exit
wait -n "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
