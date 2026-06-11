#!/usr/bin/env bash
# ── Generate self-signed TLS certificates for local Docker deployment ──
#
# Outlook Add-ins require HTTPS. This script creates a self-signed cert
# for localhost, valid for 365 days.
#
# Usage:  bash docker/generate-certs.sh
# Output: certs/cert.pem, certs/key.pem
#
# After generating, trust the cert in your OS/browser:
#   macOS:  sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain certs/cert.pem
#   Linux:  sudo cp certs/cert.pem /usr/local/share/ca-certificates/mailpilot.crt && sudo update-ca-certificates
#   Windows: double-click cert.pem → Install → Trusted Root Certification Authorities
# ──────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERT_DIR="$SCRIPT_DIR/../certs"

mkdir -p "$CERT_DIR"

echo "Generating self-signed certificate for localhost..."

openssl req -x509 -nodes -days 365 \
    -newkey rsa:2048 \
    -keyout "$CERT_DIR/key.pem" \
    -out "$CERT_DIR/cert.pem" \
    -subj "/CN=localhost/O=MailPilot-Dev" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

echo ""
echo "Certificates generated:"
echo "  $CERT_DIR/cert.pem"
echo "  $CERT_DIR/key.pem"
echo ""
echo "To trust the certificate (optional, suppresses browser warnings):"
echo "  macOS:   sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain $CERT_DIR/cert.pem"
echo "  Linux:   sudo cp $CERT_DIR/cert.pem /usr/local/share/ca-certificates/mailpilot.crt && sudo update-ca-certificates"
echo "  Windows: double-click cert.pem → Install Certificate → Trusted Root Certification Authorities"
