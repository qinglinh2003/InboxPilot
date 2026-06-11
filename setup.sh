#!/usr/bin/env bash
# ============================================================================
# MailPilot — One-click setup after git clone
#
# Usage:
#   bash configure.sh   # first: generate env.sh
#   bash setup.sh       # then: install deps + verify
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
echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║        MailPilot  —  Setup Script        ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""

# ── 0. Source env.sh (or create it interactively) ──────────────────────────
if [[ ! -f env.sh ]]; then
    warn "env.sh not found. Running configure.sh first..."
    echo ""
    bash "$SCRIPT_DIR/configure.sh"
fi

info "Loading environment from env.sh..."
source "$SCRIPT_DIR/env.sh"
ok "Environment loaded."

# ── 1. Check prerequisites ────────────────────────────────────────────────
echo ""
info "Checking prerequisites..."

# Python >= 3.11
if ! command -v python3 &>/dev/null; then
    fail "python3 not found. Please install Python 3.11+."
fi
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
if (( PY_MAJOR < 3 || (PY_MAJOR == 3 && PY_MINOR < 11) )); then
    fail "Python 3.11+ required, but found $PY_VER"
fi
ok "Python $PY_VER"

# Node >= 18
if ! command -v node &>/dev/null; then
    fail "node not found. Please install Node.js 18+."
fi
NODE_VER=$(node -v | sed 's/^v//')
NODE_MAJOR=$(echo "$NODE_VER" | cut -d. -f1)
if (( NODE_MAJOR < 18 )); then
    fail "Node.js 18+ required, but found $NODE_VER"
fi
ok "Node.js $NODE_VER"

# npm
if ! command -v npm &>/dev/null; then
    fail "npm not found. It usually ships with Node.js."
fi
ok "npm $(npm -v)"

# ── 2. Install backend (Python) ───────────────────────────────────────────
echo ""
info "Installing backend dependencies..."
cd "$SCRIPT_DIR/backend"

python3 -m pip install --quiet --upgrade pip
python3 -m pip install --quiet -e ".[dev]"
ok "Backend dependencies installed."

cd "$SCRIPT_DIR"

# ── 3. Install frontend (Node) ────────────────────────────────────────────
info "Installing frontend dependencies..."
cd "$SCRIPT_DIR/outlook-addin"

npm install --silent 2>/dev/null || npm install
ok "Frontend dependencies installed."

# Install HTTPS dev certs (required by Outlook Add-in)
info "Installing HTTPS dev certificates for Outlook Add-in..."
npx office-addin-dev-certs install 2>/dev/null && ok "HTTPS certificates ready." \
    || warn "Could not auto-install certs. Run manually: npx office-addin-dev-certs install"

cd "$SCRIPT_DIR"

# ── 4. Quick sanity check ─────────────────────────────────────────────────
echo ""
info "Running backend tests..."
cd "$SCRIPT_DIR/backend"

if python3 -m pytest tests/ -q --tb=short 2>/dev/null; then
    ok "All backend tests passed."
else
    warn "Some tests failed. Check output above."
fi

cd "$SCRIPT_DIR"

# ── Done ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          Setup complete!                 ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo "  Start both servers:  bash start.sh"
echo "  Or Docker deploy:    bash deploy.sh"
echo ""
