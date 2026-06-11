#!/usr/bin/env bash
# ============================================================================
# MailPilot — Interactive environment configuration
#
# Generates env.sh from env.sh.example with your real values.
# Safe to re-run: will not overwrite an existing env.sh without confirmation.
#
# Usage:  bash configure.sh
# ============================================================================
set -euo pipefail

# ── Colors & helpers ───────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[ OK ]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   MailPilot  —  Environment Configuration    ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ── Guard: don't silently overwrite ────────────────────────────────────────
if [[ -f env.sh ]]; then
    warn "env.sh already exists."
    read -rp "  Overwrite? [y/N] " confirm
    if [[ "${confirm,,}" != "y" ]]; then
        info "Keeping existing env.sh. Edit it manually if needed."
        exit 0
    fi
fi

if [[ ! -f env.sh.example ]]; then
    fail "env.sh.example not found. Are you in the project root (code/)?"
fi

cp env.sh.example env.sh

# ── 1. OpenAI API Key ─────────────────────────────────────────────────────
echo ""
info "Step 1/3: OpenAI API Key"
echo "  Get one at: https://platform.openai.com/api-keys"
echo ""
read -rp "  Enter your OpenAI API key (sk-...): " OPENAI_KEY

if [[ -z "$OPENAI_KEY" ]]; then
    warn "No key entered. You'll need to edit env.sh manually."
else
    # Use | as sed delimiter to avoid conflicts with key characters
    sed -i "s|<paste-your-openai-api-key-here>|${OPENAI_KEY}|" env.sh
    ok "OpenAI API key saved."
fi

# ── 2. API Token (auto-generated) ─────────────────────────────────────────
echo ""
info "Step 2/3: API Token (auto-generated)"

if command -v openssl &>/dev/null; then
    TOKEN=$(openssl rand -hex 32)
elif command -v python3 &>/dev/null; then
    TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(32))")
else
    fail "Need openssl or python3 to generate a random token."
fi

sed -i "s|<generate-a-random-token-and-paste-here>|${TOKEN}|" env.sh
ok "API token generated: ${TOKEN:0:8}...${TOKEN: -8} (64 hex chars)"

# ── 3. Deployment mode ────────────────────────────────────────────────────
echo ""
info "Step 3/3: Deployment mode"
echo "  [1] Local dev  — Vite dev server on :3000 + uvicorn on :8000"
echo "  [2] Docker     — nginx on :443 (everything in containers)"
echo ""
read -rp "  Choose [1/2] (default: 1): " MODE
MODE="${MODE:-1}"

if [[ "$MODE" == "2" ]]; then
    sed -i 's|MAILPILOT_ALLOWED_ORIGIN="https://localhost:3000"|MAILPILOT_ALLOWED_ORIGIN="https://localhost"|' env.sh
    sed -i 's|DATABASE_URL="sqlite+aiosqlite:///./mailpilot.db"|DATABASE_URL="sqlite+aiosqlite:///./data/mailpilot.db"|' env.sh
    ok "Configured for Docker deployment (origin=https://localhost)."
else
    ok "Configured for local dev (origin=https://localhost:3000)."
fi

# ── Done ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         env.sh created successfully          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "  To review or edit:   vim env.sh"
echo "  To source manually:  source env.sh"
echo ""
echo "  Next:"
if [[ "$MODE" == "2" ]]; then
    echo "    bash deploy.sh"
else
    echo "    bash setup.sh     # first time: install dependencies"
    echo "    bash start.sh     # start both servers"
fi
echo ""
