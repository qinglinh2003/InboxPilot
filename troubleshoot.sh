#!/usr/bin/env bash
# ── MailPilot macOS Troubleshooting Script ──────────────
# Run: bash troubleshoot.sh
# Diagnoses common Outlook Add-in sideloading issues.
# ────────────────────────────────────────────────────────
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
pass() { echo -e "  ${GREEN}✔ $1${NC}"; }
fail() { echo -e "  ${RED}✘ $1${NC}"; }
warn() { echo -e "  ${YELLOW}⚠ $1${NC}"; }

echo ""
echo "═══════════════════════════════════════"
echo "  MailPilot Deployment Diagnostics"
echo "═══════════════════════════════════════"
echo ""

ERRORS=0

# ── 1. Docker running? ──────────────────────────────────
echo "1. Docker services"
if docker compose ps --format '{{.Name}}' 2>/dev/null | grep -q backend; then
    pass "Backend container is running"
else
    fail "Backend container not found — run: bash deploy.sh"
    ERRORS=$((ERRORS + 1))
fi

if docker compose ps --format '{{.Name}}' 2>/dev/null | grep -q frontend; then
    pass "Frontend container is running"
else
    fail "Frontend container not found — run: bash deploy.sh"
    ERRORS=$((ERRORS + 1))
fi

# ── 2. HTTPS reachable? ─────────────────────────────────
echo ""
echo "2. HTTPS connectivity"
HEALTH=$(curl -sk https://localhost/api/health 2>/dev/null || echo "FAIL")
if echo "$HEALTH" | grep -q '"ok"'; then
    pass "API health check passed"
else
    fail "Cannot reach https://localhost/api/health"
    ERRORS=$((ERRORS + 1))
fi

INDEX=$(curl -sk -o /dev/null -w "%{http_code}" https://localhost/ 2>/dev/null || echo "000")
if [ "$INDEX" = "200" ]; then
    pass "Frontend index.html served (HTTP 200)"
else
    fail "Frontend not serving (HTTP $INDEX)"
    ERRORS=$((ERRORS + 1))
fi

ICON=$(curl -sk -o /dev/null -w "%{http_code}" https://localhost/assets/icon-32.png 2>/dev/null || echo "000")
if [ "$ICON" = "200" ]; then
    pass "Icon assets accessible (HTTP 200)"
else
    fail "Icon assets NOT accessible (HTTP $ICON) — Outlook won't show the button!"
    ERRORS=$((ERRORS + 1))
fi

CMD=$(curl -sk -o /dev/null -w "%{http_code}" https://localhost/commands.html 2>/dev/null || echo "000")
if [ "$CMD" = "200" ]; then
    pass "commands.html accessible (HTTP 200)"
else
    fail "commands.html NOT accessible (HTTP $CMD)"
    ERRORS=$((ERRORS + 1))
fi

# ── 3. Certificate trusted? ─────────────────────────────
echo ""
echo "3. SSL certificate trust"
# Try to connect without -k (no insecure flag)
CERT_OK=$(curl -s https://localhost/api/health 2>&1 || true)
if echo "$CERT_OK" | grep -q '"ok"'; then
    pass "Certificate is trusted by system"
else
    fail "Certificate NOT trusted — Outlook will silently fail!"
    echo ""
    echo "    Fix: run this command (one line, no line breaks):"
    echo ""
    if [ -f certs/cert.pem ]; then
        echo "    sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain certs/cert.pem"
    else
        echo "    (certs/cert.pem not found — run: bash docker/generate-certs.sh)"
    fi
    echo ""
    ERRORS=$((ERRORS + 1))
fi

# ── 4. Manifest in wef directory? ────────────────────────
echo ""
echo "4. Outlook sideload manifest"
WEF_DIR="$HOME/Library/Containers/com.microsoft.Outlook/Data/Documents/wef"
if [ -d "$WEF_DIR" ]; then
    pass "wef directory exists"
else
    fail "wef directory missing"
    echo "    Fix: mkdir -p \"$WEF_DIR\""
    ERRORS=$((ERRORS + 1))
fi

if [ -f "$WEF_DIR/manifest.xml" ]; then
    pass "manifest.xml found in wef/"
    # Check it points to correct URL
    if grep -q "https://localhost/" "$WEF_DIR/manifest.xml" && ! grep -q "localhost:3000" "$WEF_DIR/manifest.xml"; then
        pass "Manifest URLs point to https://localhost (Docker mode)"
    elif grep -q "localhost:3000" "$WEF_DIR/manifest.xml"; then
        warn "Manifest URLs point to localhost:3000 (dev mode, not Docker)"
    fi
else
    fail "manifest.xml NOT found in wef/"
    echo "    Fix: cp outlook-addin/manifest.docker.xml \"$WEF_DIR/manifest.xml\""
    ERRORS=$((ERRORS + 1))
fi

# ── 5. Outlook version check ────────────────────────────
echo ""
echo "5. Outlook version"
if [ -d "$HOME/Library/Containers/com.microsoft.Outlook" ]; then
    pass "Classic Outlook container found (sideloading supported)"
else
    fail "Classic Outlook container not found"
    warn "New Outlook for Mac does NOT support wef sideloading"
    warn "Use Outlook Web (outlook.office.com) instead"
    ERRORS=$((ERRORS + 1))
fi

# ── Summary ──────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════"
if [ $ERRORS -eq 0 ]; then
    echo -e "  ${GREEN}All checks passed!${NC}"
    echo ""
    echo "  If button still doesn't appear:"
    echo "    1. Clear Outlook cache:"
    echo "       rm -rf ~/Library/Caches/com.microsoft.Outlook"
    echo "       rm -rf ~/Library/Caches/Microsoft/Outlook"
    echo "    2. Fully quit Outlook (⌘Q)"
    echo "    3. Reopen Outlook"
    echo "    4. Open a mail in reading mode"
    echo "    5. Look for 'MailPilot' in the ribbon or ⋯ menu"
else
    echo -e "  ${RED}$ERRORS issue(s) found — fix them and re-run this script${NC}"
fi
echo "═══════════════════════════════════════"
echo ""
