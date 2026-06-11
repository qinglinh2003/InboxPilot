#!/usr/bin/env bash
# ============================================================================
# MailPilot — Docker Compose deployment
#
# Sources env.sh, generates TLS certs if missing, then runs docker compose.
# No live Node/Python shells needed — everything runs in containers.
#
# Usage:
#   bash deploy.sh              # build & start (foreground)
#   bash deploy.sh --detach     # build & start (background)
#   bash deploy.sh down         # stop everything
#   bash deploy.sh logs         # tail logs
# ============================================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[ OK ]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Load environment ──────────────────────────────────────────────────────
if [[ ! -f env.sh ]]; then
    fail "env.sh not found. Run 'bash configure.sh' first (choose Docker mode)."
fi

source "$SCRIPT_DIR/env.sh"
ok "Environment loaded from env.sh"

# ── Generate .env for docker compose ─────────────────────────────────────
# Docker Compose automatically reads .env in the project directory.
# This lets "docker compose up" work even without "bash deploy.sh".
info "Generating .env from env.sh for Docker Compose..."
cat > "$SCRIPT_DIR/.env" <<DOTENV
# Auto-generated from env.sh by deploy.sh — do not edit manually.
# To change values, edit env.sh and re-run: bash deploy.sh
OPENAI_API_KEY=${OPENAI_API_KEY}
MAILPILOT_API_TOKEN=${MAILPILOT_API_TOKEN}
DEFAULT_MODEL=${DEFAULT_MODEL:-gpt-4o-mini}
ESCALATION_MODEL=${ESCALATION_MODEL:-gpt-4o}
DOTENV
ok ".env generated (docker compose will read it automatically)"

# ── Shortcut sub-commands ─────────────────────────────────────────────────
ACTION="${1:-up}"

if [[ "$ACTION" == "down" ]]; then
    info "Stopping containers..."
    docker compose down
    ok "Containers stopped."
    exit 0
fi

if [[ "$ACTION" == "logs" ]]; then
    docker compose logs -f
    exit 0
fi

# ── Validate required vars ────────────────────────────────────────────────
info "Validating configuration..."

if [[ -z "${OPENAI_API_KEY:-}" ]] || [[ "$OPENAI_API_KEY" == *"paste"* ]]; then
    fail "OPENAI_API_KEY not set. Edit env.sh or re-run 'bash configure.sh'."
fi

if [[ -z "${MAILPILOT_API_TOKEN:-}" ]] || [[ "$MAILPILOT_API_TOKEN" == *"generate"* ]]; then
    fail "MAILPILOT_API_TOKEN not set. Edit env.sh or re-run 'bash configure.sh'."
fi

ok "Configuration looks good."

# ── Check Docker ──────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    fail "docker not found. Install Docker: https://docs.docker.com/get-docker/"
fi

if ! docker compose version &>/dev/null; then
    fail "docker compose not available. Install Docker Compose v2."
fi

ok "Docker $(docker --version | sed 's/.*version \([0-9.]*\).*/\1/')"

# ── Generate TLS certs if missing ─────────────────────────────────────────
if [[ ! -f certs/cert.pem ]] || [[ ! -f certs/key.pem ]]; then
    info "TLS certificates not found. Generating self-signed certs..."
    bash "$SCRIPT_DIR/docker/generate-certs.sh"
    ok "Certificates generated in certs/"
    echo ""
    warn "To suppress browser warnings, trust the certificate:"
    echo "    macOS:   sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain certs/cert.pem"
    echo "    Linux:   sudo cp certs/cert.pem /usr/local/share/ca-certificates/mailpilot.crt && sudo update-ca-certificates"
    echo ""
fi

# ── Build & launch ────────────────────────────────────────────────────────
DETACH_FLAG=""
if [[ "${1:-}" == "--detach" ]] || [[ "${2:-}" == "--detach" ]]; then
    DETACH_FLAG="-d"
fi

info "Building and starting containers..."
echo ""

docker compose up --build $DETACH_FLAG

if [[ -n "$DETACH_FLAG" ]]; then
    echo ""
    ok "MailPilot is running in the background."
    echo ""
    echo "  App:    https://localhost"
    echo "  API:    https://localhost/api/health"
    echo "  Logs:   bash deploy.sh logs"
    echo "  Stop:   bash deploy.sh down"
    echo ""
fi
