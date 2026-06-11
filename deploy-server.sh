#!/usr/bin/env bash
# ============================================================================
# MailPilot — One-click server deployment
#
# Deploys MailPilot to any Linux server with nginx + TLS already configured.
# Handles first-time setup and re-deploys (code update → rebuild → restart).
#
# Prerequisites on the target server:
#   - Python 3.11+
#   - Node.js 18+ and npm
#   - nginx (running, with TLS configured for your domain)
#   - systemd
#
# Usage:
#   First time:   bash deploy-server.sh
#   Re-deploy:    bash deploy-server.sh --update
#   Uninstall:    bash deploy-server.sh --uninstall
#   Status:       bash deploy-server.sh --status
# ============================================================================
set -euo pipefail

# ── Colors & helpers ─────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()      { echo -e "${GREEN}[ OK ]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()    { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }
section() { echo ""; echo -e "${BOLD}── $* ──${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Cross-platform sed in-place
sedi() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "$@"
    else
        sed -i "$@"
    fi
}

# ── Config file (persists settings across re-deploys) ────────────────────────
DEPLOY_CONF="$SCRIPT_DIR/.deploy-server.conf"

save_config() {
    cat > "$DEPLOY_CONF" <<CONF
# MailPilot server deployment config — auto-generated, do not commit
DEPLOY_DOMAIN="$DEPLOY_DOMAIN"
DEPLOY_PATH="$DEPLOY_PATH"
DEPLOY_BACKEND_PORT="$DEPLOY_BACKEND_PORT"
DEPLOY_WEBROOT="$DEPLOY_WEBROOT"
DEPLOY_SERVICE_NAME="$DEPLOY_SERVICE_NAME"
DEPLOY_NGINX_CONF="$DEPLOY_NGINX_CONF"
DEPLOY_WORKERS="$DEPLOY_WORKERS"
CONF
    ok "Config saved to .deploy-server.conf"
}

load_config() {
    if [[ -f "$DEPLOY_CONF" ]]; then
        source "$DEPLOY_CONF"
        return 0
    fi
    return 1
}

# ── Subcommands ──────────────────────────────────────────────────────────────
ACTION="${1:-deploy}"

case "$ACTION" in
    --status)
        section "MailPilot Status"
        load_config 2>/dev/null || { info "No deployment config found."; exit 0; }
        echo "  Domain:      https://${DEPLOY_DOMAIN}${DEPLOY_PATH}"
        echo "  Backend:     127.0.0.1:${DEPLOY_BACKEND_PORT}"
        echo "  Service:     ${DEPLOY_SERVICE_NAME}"
        echo "  Web root:    ${DEPLOY_WEBROOT}"
        echo "  nginx conf:  ${DEPLOY_NGINX_CONF}"
        echo ""
        if systemctl is-active --quiet "${DEPLOY_SERVICE_NAME}" 2>/dev/null; then
            ok "Backend service is running"
        else
            warn "Backend service is NOT running"
        fi
        curl -sf "https://${DEPLOY_DOMAIN}${DEPLOY_PATH}api/health" \
            && ok "API health check passed" \
            || warn "API health check failed"
        exit 0
        ;;
    --uninstall)
        section "Uninstall MailPilot"
        load_config 2>/dev/null || fail "No deployment config found."
        echo "This will:"
        echo "  - Stop and disable systemd service: ${DEPLOY_SERVICE_NAME}"
        echo "  - Remove nginx config: ${DEPLOY_NGINX_CONF}"
        echo "  - Remove web root: ${DEPLOY_WEBROOT}"
        echo "  (env.sh, venv, and code are NOT removed)"
        echo ""
        read -rp "  Continue? [y/N] " confirm
        [[ "${confirm,,}" == "y" ]] || exit 0
        sudo systemctl stop "${DEPLOY_SERVICE_NAME}" 2>/dev/null || true
        sudo systemctl disable "${DEPLOY_SERVICE_NAME}" 2>/dev/null || true
        sudo rm -f "/etc/systemd/system/${DEPLOY_SERVICE_NAME}.service"
        sudo systemctl daemon-reload
        sudo rm -f "${DEPLOY_NGINX_CONF}"
        sudo rm -rf "${DEPLOY_WEBROOT}"
        sudo nginx -t && sudo systemctl reload nginx
        rm -f "$DEPLOY_CONF"
        ok "MailPilot uninstalled. Reload your nginx config if needed."
        exit 0
        ;;
    --update)
        info "Re-deploying (update mode)..."
        load_config 2>/dev/null || fail "No deployment config. Run 'bash deploy-server.sh' first."
        ;;
    deploy|"")
        ACTION="deploy"
        ;;
    *)
        echo "Usage: bash deploy-server.sh [--update | --status | --uninstall]"
        exit 1
        ;;
esac

# ============================================================================
# STEP 0: Preflight checks
# ============================================================================
section "Preflight Checks"

# Python
PYTHON=""
for cmd in python3.12 python3.11 python3; do
    if command -v "$cmd" &>/dev/null; then
        PY_VER=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
        PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
        if [[ "$PY_MAJOR" -ge 3 && "$PY_MINOR" -ge 11 ]]; then
            PYTHON="$cmd"
            break
        fi
    fi
done
[[ -n "$PYTHON" ]] && ok "Python: $($PYTHON --version)" || fail "Python 3.11+ required"

# Node
command -v node &>/dev/null || fail "Node.js 18+ required (apt install nodejs)"
NODE_VER=$(node -v | tr -d 'v' | cut -d. -f1)
[[ "$NODE_VER" -ge 18 ]] && ok "Node.js: $(node -v)" || fail "Node.js 18+ required (found $(node -v))"

# npm
command -v npm &>/dev/null && ok "npm: $(npm -v)" || fail "npm required"

# nginx
command -v nginx &>/dev/null && ok "nginx: $(nginx -v 2>&1 | cut -d/ -f2)" || fail "nginx required"

# systemd
command -v systemctl &>/dev/null && ok "systemd available" || fail "systemd required"

# ============================================================================
# STEP 1: Interactive configuration (first deploy only)
# ============================================================================
if [[ "$ACTION" == "deploy" ]] && ! load_config 2>/dev/null; then
    section "Server Configuration"

    # Domain
    echo ""
    read -rp "  Domain name (e.g. example.com): " DEPLOY_DOMAIN
    [[ -n "$DEPLOY_DOMAIN" ]] || fail "Domain is required"

    # URL path
    read -rp "  URL path (default: /mailpilot/): " DEPLOY_PATH
    DEPLOY_PATH="${DEPLOY_PATH:-/mailpilot/}"
    # Ensure leading and trailing slashes
    [[ "$DEPLOY_PATH" == /* ]] || DEPLOY_PATH="/$DEPLOY_PATH"
    [[ "$DEPLOY_PATH" == */ ]] || DEPLOY_PATH="$DEPLOY_PATH/"

    # Backend port
    read -rp "  Backend port (default: 8082): " DEPLOY_BACKEND_PORT
    DEPLOY_BACKEND_PORT="${DEPLOY_BACKEND_PORT:-8082}"

    # Workers
    read -rp "  Uvicorn workers (default: 2): " DEPLOY_WORKERS
    DEPLOY_WORKERS="${DEPLOY_WORKERS:-2}"

    # Web root
    DEFAULT_WEBROOT="/var/www/${DEPLOY_DOMAIN}${DEPLOY_PATH}"
    read -rp "  Web root (default: ${DEFAULT_WEBROOT}): " DEPLOY_WEBROOT
    DEPLOY_WEBROOT="${DEPLOY_WEBROOT:-$DEFAULT_WEBROOT}"

    # Service name
    DEPLOY_SERVICE_NAME="mailpilot"

    # nginx config path
    DEPLOY_NGINX_CONF="/etc/nginx/snippets/mailpilot.conf"

    save_config
else
    load_config
    ok "Loaded config: https://${DEPLOY_DOMAIN}${DEPLOY_PATH}"
fi

ORIGIN="https://${DEPLOY_DOMAIN}"
BASE_URL="${ORIGIN}${DEPLOY_PATH}"

# ============================================================================
# STEP 2: Environment variables (env.sh)
# ============================================================================
section "Environment Variables"

if [[ ! -f env.sh ]]; then
    info "Running configure.sh to create env.sh..."
    bash configure.sh

    # Override for server mode
    sedi "s|MAILPILOT_ALLOWED_ORIGIN=\".*\"|MAILPILOT_ALLOWED_ORIGIN=\"${ORIGIN}\"|" env.sh
    ok "CORS origin set to ${ORIGIN}"
else
    ok "env.sh already exists"
fi

source env.sh

# Validate critical vars
[[ -n "${OPENAI_API_KEY:-}" && "$OPENAI_API_KEY" != *"paste"* && "$OPENAI_API_KEY" != "<"* ]] \
    || fail "OPENAI_API_KEY not configured in env.sh"
[[ -n "${MAILPILOT_API_TOKEN:-}" && "$MAILPILOT_API_TOKEN" != *"generate"* && "$MAILPILOT_API_TOKEN" != "<"* ]] \
    || fail "MAILPILOT_API_TOKEN not configured in env.sh"
ok "API keys validated"

# ============================================================================
# STEP 3: Python virtual environment + backend dependencies
# ============================================================================
section "Backend Setup"

VENV_DIR="$SCRIPT_DIR/.venv-mailpilot"

if [[ ! -d "$VENV_DIR" ]]; then
    info "Creating Python virtual environment..."
    $PYTHON -m venv "$VENV_DIR"
fi

info "Installing backend dependencies..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -e "./backend"
ok "Backend dependencies installed"

# Ensure data directory exists
mkdir -p "$SCRIPT_DIR/data"

# ============================================================================
# STEP 4: Build frontend
# ============================================================================
section "Frontend Build"

cd "$SCRIPT_DIR/outlook-addin"

info "Installing Node dependencies..."
npm install --silent 2>/dev/null || npm install

info "Building frontend (base=${DEPLOY_PATH})..."
VITE_BACKEND_URL="${BASE_URL%/}" \
VITE_API_TOKEN="$MAILPILOT_API_TOKEN" \
NODE_ENV=production \
    npx vite build --base "$DEPLOY_PATH"

ok "Frontend built → outlook-addin/dist/"
cd "$SCRIPT_DIR"

# ============================================================================
# STEP 5: Generate Outlook manifest
# ============================================================================
section "Outlook Manifest"

TIMESTAMP=$(date +%Y%m%d-%H%M)
MANIFEST_OUT="$SCRIPT_DIR/outlook-addin/dist/manifest.xml"

cat > "$MANIFEST_OUT" <<MANIFEST
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<!--
  MailPilot manifest — auto-generated by deploy-server.sh
  Domain: ${DEPLOY_DOMAIN}
  Path:   ${DEPLOY_PATH}
  Built:  ${TIMESTAMP}
-->
<OfficeApp
  xmlns="http://schemas.microsoft.com/office/appforoffice/1.1"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xmlns:bt="http://schemas.microsoft.com/office/officeappbasictypes/1.0"
  xmlns:mailappor="http://schemas.microsoft.com/office/mailappversionoverrides/1.0"
  xsi:type="MailApp"
>
  <Id>8c81a8b9-0f41-4c28-9f52-5b6e2e04f1df</Id>
  <Version>1.0.4</Version>
  <ProviderName>MailPilot</ProviderName>
  <DefaultLocale>en-US</DefaultLocale>
  <DisplayName DefaultValue="MailPilot" />
  <Description DefaultValue="AI-powered email summarization and categorization for Outlook." />
  <IconUrl DefaultValue="${BASE_URL}assets/icon-32.png" />
  <HighResolutionIconUrl DefaultValue="${BASE_URL}assets/icon-64.png" />
  <SupportUrl DefaultValue="https://github.com/qinglinh2003/InboxPilot" />

  <AppDomains>
    <AppDomain>${ORIGIN}</AppDomain>
  </AppDomains>

  <Hosts>
    <Host Name="Mailbox" />
  </Hosts>

  <Requirements>
    <Sets>
      <Set Name="Mailbox" MinVersion="1.3" />
    </Sets>
  </Requirements>

  <FormSettings>
    <Form xsi:type="ItemRead">
      <DesktopSettings>
        <SourceLocation DefaultValue="${BASE_URL}index.html?v=${TIMESTAMP}" />
        <RequestedHeight>450</RequestedHeight>
      </DesktopSettings>
    </Form>
  </FormSettings>

  <Permissions>ReadItem</Permissions>

  <Rule xsi:type="RuleCollection" Mode="Or">
    <Rule xsi:type="ItemIs" ItemType="Message" FormType="Read" />
  </Rule>

  <DisableEntityHighlighting>true</DisableEntityHighlighting>

  <VersionOverrides
    xmlns="http://schemas.microsoft.com/office/mailappversionoverrides"
    xsi:type="VersionOverridesV1_0"
  >
    <Requirements>
      <bt:Sets DefaultMinVersion="1.3">
        <bt:Set Name="Mailbox" />
      </bt:Sets>
    </Requirements>

    <Hosts>
      <Host xsi:type="MailHost">
        <DesktopFormFactor>
          <FunctionFile resid="commandsUrl" />
          <ExtensionPoint xsi:type="MessageReadCommandSurface">
            <OfficeTab id="TabDefault">
              <Group id="mailpilotGroup">
                <Label resid="groupLabel" />
                <Control xsi:type="Button" id="summarizeButton">
                  <Label resid="buttonLabel" />
                  <Supertip>
                    <Title resid="buttonLabel" />
                    <Description resid="buttonDesc" />
                  </Supertip>
                  <Icon>
                    <bt:Image size="16" resid="icon16" />
                    <bt:Image size="32" resid="icon32" />
                    <bt:Image size="80" resid="icon80" />
                  </Icon>
                  <Action xsi:type="ShowTaskpane">
                    <SourceLocation resid="taskpaneUrl" />
                  </Action>
                </Control>
              </Group>
            </OfficeTab>
          </ExtensionPoint>
        </DesktopFormFactor>
      </Host>
    </Hosts>

    <Resources>
      <bt:Images>
        <bt:Image id="icon16" DefaultValue="${BASE_URL}assets/icon-16.png" />
        <bt:Image id="icon32" DefaultValue="${BASE_URL}assets/icon-32.png" />
        <bt:Image id="icon80" DefaultValue="${BASE_URL}assets/icon-80.png" />
      </bt:Images>
      <bt:Urls>
        <bt:Url id="taskpaneUrl" DefaultValue="${BASE_URL}index.html?v=${TIMESTAMP}" />
        <bt:Url id="commandsUrl" DefaultValue="${BASE_URL}commands.html?v=${TIMESTAMP}" />
      </bt:Urls>
      <bt:ShortStrings>
        <bt:String id="groupLabel" DefaultValue="MailPilot" />
        <bt:String id="buttonLabel" DefaultValue="Summarize" />
      </bt:ShortStrings>
      <bt:LongStrings>
        <bt:String id="buttonDesc" DefaultValue="Summarize this email with AI and get category suggestions." />
      </bt:LongStrings>
    </Resources>
  </VersionOverrides>
</OfficeApp>
MANIFEST

ok "Manifest generated → ${BASE_URL}manifest.xml"

# ============================================================================
# STEP 6: Deploy frontend to web root
# ============================================================================
section "Deploy Frontend"

sudo mkdir -p "$DEPLOY_WEBROOT"
# Clean old files to avoid stale JS bundles
sudo rm -rf "${DEPLOY_WEBROOT:?}"/*
sudo cp -r "$SCRIPT_DIR/outlook-addin/dist/"* "$DEPLOY_WEBROOT/"
sudo chown -R www-data:www-data "$DEPLOY_WEBROOT" 2>/dev/null \
    || sudo chown -R nginx:nginx "$DEPLOY_WEBROOT" 2>/dev/null \
    || true
ok "Frontend deployed to ${DEPLOY_WEBROOT}"

# ============================================================================
# STEP 7: Generate nginx config snippet
# ============================================================================
section "nginx Configuration"

NGINX_SNIPPET="/tmp/mailpilot-nginx-$$.conf"
# Strip trailing slash from DEPLOY_PATH for alias directive
PATH_NOSLASH="${DEPLOY_PATH%/}"

cat > "$NGINX_SNIPPET" <<NGINX
# MailPilot — auto-generated by deploy-server.sh
# Include this file inside your domain's TLS server block:
#   include ${DEPLOY_NGINX_CONF};

# Backend API (reverse proxy to uvicorn)
location ^~ ${DEPLOY_PATH}api/ {
    proxy_pass http://127.0.0.1:${DEPLOY_BACKEND_PORT}/api/;
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_read_timeout 120s;  # LLM calls can be slow
}

# Frontend static files
location ^~ ${DEPLOY_PATH} {
    alias ${DEPLOY_WEBROOT};
    try_files \$uri \$uri/ ${DEPLOY_PATH}index.html;

    # Do NOT set X-Frame-Options or CSP frame-ancestors here.
    # Outlook loads the task pane in an iframe; restrictive headers
    # cause silent load failures in managed Microsoft 365 tenants.

    add_header X-Content-Type-Options "nosniff" always;
    add_header Cache-Control "no-cache, no-store, must-revalidate" always;
    add_header Pragma "no-cache" always;
}
NGINX

# Install the snippet
sudo mkdir -p "$(dirname "$DEPLOY_NGINX_CONF")"
sudo cp "$NGINX_SNIPPET" "$DEPLOY_NGINX_CONF"
rm -f "$NGINX_SNIPPET"

ok "nginx config → ${DEPLOY_NGINX_CONF}"

# Check if the snippet is included in any server block
if ! sudo grep -rq "include.*mailpilot" /etc/nginx/sites-enabled/ /etc/nginx/conf.d/ 2>/dev/null; then
    warn "You need to add this line inside your domain's TLS server block:"
    echo ""
    echo -e "    ${CYAN}include ${DEPLOY_NGINX_CONF};${NC}"
    echo ""
    echo "  Example location: /etc/nginx/sites-enabled/${DEPLOY_DOMAIN}"
    echo "  Add the include line inside the 'server { ... }' block that"
    echo "  handles HTTPS for ${DEPLOY_DOMAIN}."
    echo ""
    read -rp "  Press Enter after you've added it (or 's' to skip): " skip
    if [[ "${skip,,}" == "s" ]]; then
        warn "Skipped nginx include. Add it manually later."
    fi
fi

# Test and reload nginx
if sudo nginx -t 2>/dev/null; then
    sudo systemctl reload nginx
    ok "nginx config valid and reloaded"
else
    fail "nginx config test failed. Check ${DEPLOY_NGINX_CONF} and your server block."
fi

# ============================================================================
# STEP 8: Create run-backend.sh (if not exists or outdated)
# ============================================================================
section "Backend Launcher"

cat > "$SCRIPT_DIR/run-backend.sh" <<'LAUNCHER'
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/env.sh"

if [[ -z "${OPENAI_API_KEY:-}" || "$OPENAI_API_KEY" == *"PASTE"* || "$OPENAI_API_KEY" == *"paste"* || "$OPENAI_API_KEY" == "<"* ]]; then
    echo "ERROR: OPENAI_API_KEY is not configured. Edit $SCRIPT_DIR/env.sh" >&2
    exit 1
fi

if [[ -z "${MAILPILOT_API_TOKEN:-}" || "$MAILPILOT_API_TOKEN" == *"generate"* || "$MAILPILOT_API_TOKEN" == "<"* ]]; then
    echo "ERROR: MAILPILOT_API_TOKEN is not configured. Edit $SCRIPT_DIR/env.sh" >&2
    exit 1
fi

LAUNCHER

# Append the dynamic parts (port and workers from config)
cat >> "$SCRIPT_DIR/run-backend.sh" <<LAUNCHER_DYN
exec "\$SCRIPT_DIR/.venv-mailpilot/bin/uvicorn" app.main:app \\
    --host 127.0.0.1 \\
    --port ${DEPLOY_BACKEND_PORT} \\
    --workers ${DEPLOY_WORKERS}
LAUNCHER_DYN

chmod +x "$SCRIPT_DIR/run-backend.sh"
ok "run-backend.sh updated (port=${DEPLOY_BACKEND_PORT}, workers=${DEPLOY_WORKERS})"

# ============================================================================
# STEP 9: systemd service
# ============================================================================
section "systemd Service"

SERVICE_FILE="/etc/systemd/system/${DEPLOY_SERVICE_NAME}.service"
CURRENT_USER="$(whoami)"
CURRENT_GROUP="$(id -gn)"

sudo tee "$SERVICE_FILE" > /dev/null <<SERVICE
[Unit]
Description=MailPilot Backend (FastAPI + uvicorn)
After=network.target

[Service]
Type=simple
User=${CURRENT_USER}
Group=${CURRENT_GROUP}
WorkingDirectory=${SCRIPT_DIR}/backend
ExecStart=${SCRIPT_DIR}/run-backend.sh
Restart=on-failure
RestartSec=5
Environment=PATH=${VENV_DIR}/bin:/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable "${DEPLOY_SERVICE_NAME}" --quiet
sudo systemctl restart "${DEPLOY_SERVICE_NAME}"

# Wait for health check
sleep 2
if systemctl is-active --quiet "${DEPLOY_SERVICE_NAME}"; then
    ok "Backend service started"
else
    warn "Service may have failed. Check: sudo journalctl -u ${DEPLOY_SERVICE_NAME} -n 30"
fi

# ============================================================================
# STEP 10: Verify deployment
# ============================================================================
section "Verification"

ERRORS=0

# Health check
if curl -sf "https://${DEPLOY_DOMAIN}${DEPLOY_PATH}api/health" > /dev/null 2>&1; then
    ok "API health check:    https://${DEPLOY_DOMAIN}${DEPLOY_PATH}api/health"
else
    # Try localhost directly
    if curl -sf "http://127.0.0.1:${DEPLOY_BACKEND_PORT}/api/health" > /dev/null 2>&1; then
        ok "Backend running on :${DEPLOY_BACKEND_PORT} (nginx proxy may need setup)"
    else
        warn "API health check failed"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Frontend
if curl -sf "https://${DEPLOY_DOMAIN}${DEPLOY_PATH}" > /dev/null 2>&1; then
    ok "Frontend:            https://${DEPLOY_DOMAIN}${DEPLOY_PATH}"
else
    warn "Frontend not accessible"
    ERRORS=$((ERRORS + 1))
fi

# Manifest
if curl -sf "https://${DEPLOY_DOMAIN}${DEPLOY_PATH}manifest.xml" > /dev/null 2>&1; then
    ok "Manifest:            https://${DEPLOY_DOMAIN}${DEPLOY_PATH}manifest.xml"
else
    warn "Manifest not accessible"
    ERRORS=$((ERRORS + 1))
fi

# Icons
if curl -sf "https://${DEPLOY_DOMAIN}${DEPLOY_PATH}assets/icon-32.png" > /dev/null 2>&1; then
    ok "Icons:               accessible"
else
    warn "Icon assets not accessible"
    ERRORS=$((ERRORS + 1))
fi

# ============================================================================
# Done
# ============================================================================
echo ""
if [[ "$ERRORS" -eq 0 ]]; then
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              MailPilot deployed successfully!                ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
else
    echo -e "${YELLOW}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║         MailPilot deployed with ${ERRORS} warning(s)                ║${NC}"
    echo -e "${YELLOW}╚══════════════════════════════════════════════════════════════╝${NC}"
fi

echo ""
echo "  App:       https://${DEPLOY_DOMAIN}${DEPLOY_PATH}"
echo "  API:       https://${DEPLOY_DOMAIN}${DEPLOY_PATH}api/health"
echo "  Manifest:  https://${DEPLOY_DOMAIN}${DEPLOY_PATH}manifest.xml"
echo ""
echo "  Install in Outlook Web:"
echo "    1. Open https://outlook.office365.com/mail/"
echo "    2. Apps → My add-ins → Custom Add-ins → Add from URL"
echo "    3. Paste: https://${DEPLOY_DOMAIN}${DEPLOY_PATH}manifest.xml"
echo ""
echo "  Commands:"
echo "    bash deploy-server.sh --status     # check service status"
echo "    bash deploy-server.sh --update     # re-deploy after code changes"
echo "    bash deploy-server.sh --uninstall  # remove everything"
echo "    sudo journalctl -u ${DEPLOY_SERVICE_NAME} -f   # tail logs"
echo ""
