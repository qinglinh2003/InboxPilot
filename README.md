# MailPilot

Outlook add-in that summarizes emails, detects priority/deadlines, and recommends categories — powered by OpenAI.

```
Outlook  →  click "Summarize"  →  Task Pane opens
         →  reads email body   →  sends to backend
         →  OpenAI analysis    →  summary + priority + categories
         →  user confirms      →  categories applied to email
```

## Architecture

```
Outlook Web / Desktop
    │
    │  iframe loads Task Pane from your server
    ▼
nginx (TLS)
    ├── /mailpilot/          →  static React files (pre-built)
    └── /mailpilot/api/*     →  reverse proxy → uvicorn (:8082)
                                    ├── FastAPI (3 endpoints)
                                    ├── OpenAI API (gpt-4o-mini / gpt-4o)
                                    └── SQLite (cache + usage logs)
```

## Project Structure

```
code/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app (3 endpoints)
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── schemas.py           # Request/response models
│   │   ├── auth.py              # API key auth + rate limiting
│   │   ├── email/               # Cleaner, hashing, taxonomy
│   │   ├── db/                  # Async SQLAlchemy + models
│   │   └── llm/                 # OpenAI client, prompts, schemas
│   ├── tests/                   # 32 unit/integration tests
│   └── pyproject.toml
├── outlook-addin/
│   ├── src/taskpane/            # React + TypeScript + Fluent UI
│   ├── manifest.xml             # Dev manifest (localhost:3000)
│   ├── manifest.docker.xml      # Docker manifest (localhost:443)
│   ├── manifest.server.xml      # Production manifest (your domain)
│   ├── package.json
│   └── vite.config.ts
├── deploy/
│   └── nginx.mailpilot.conf     # nginx snippet (reference)
├── docker/                      # Docker deployment files
├── env.sh.example               # Environment variable template
├── configure.sh                 # Interactive env.sh generator
├── deploy-server.sh             # One-click server deployment
├── deploy.sh                    # Docker Compose deployment
├── setup.sh                     # Local dev setup
└── start.sh                     # Local dev servers
```

---

## Server Deployment

Deploy MailPilot to any Linux server with nginx and TLS already configured.

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- nginx (running, with TLS/SSL configured for your domain)
- systemd

### Step 1 — Clone and deploy

```bash
git clone git@github.com:qinglinh2003/InboxPilot.git
cd InboxPilot/code
bash deploy-server.sh
```

The script will interactively:

1. **Check prerequisites** — Python, Node, npm, nginx, systemd
2. **Configure environment** — prompts for your OpenAI API key, auto-generates an API token
3. **Ask deployment settings** — domain name, URL path (e.g. `/mailpilot/`), backend port
4. **Install backend** — creates Python venv, installs dependencies
5. **Build frontend** — compiles React app with your domain baked in
6. **Generate manifest** — creates an Outlook manifest with your domain's URLs
7. **Deploy to nginx** — copies static files, generates nginx config snippet
8. **Start service** — creates and enables a systemd service

### Step 2 — Include the nginx snippet

The script generates a config snippet at the path it tells you (e.g. `/etc/nginx/snippets/mailpilot.conf`). Add it to your existing server block:

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    # ... your existing TLS config ...

    include /etc/nginx/snippets/mailpilot.conf;

    # ... your other location blocks ...
}
```

Then reload nginx:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

### Step 3 — Verify

```bash
# Check service status
bash deploy-server.sh --status

# Or manually
curl https://your-domain.com/mailpilot/api/health
# → {"status":"ok","version":"0.1.0"}
```

### Management commands

```bash
# Re-deploy after code changes
bash deploy-server.sh --update

# Check status
bash deploy-server.sh --status

# Uninstall (stops service, removes nginx config and web root)
bash deploy-server.sh --uninstall

# View backend logs
sudo journalctl -u mailpilot -f

# Restart backend
sudo systemctl restart mailpilot
```

---

## Upload the Add-in to Outlook

Once the server is running, you need to load the manifest into Outlook so the "Summarize" button appears.

### Option A — Outlook Web (recommended)

Works with any Outlook account (personal or work/school).

1. Open [Outlook Web](https://outlook.office365.com/mail/)
2. Open any email (reading mode)
3. Find **"Apps"** (puzzle icon) or **"..."** (more actions) in the toolbar above the email
4. Click **"Get Add-ins"**
   - If you can't find it, go directly to: `https://aka.ms/olksideload`
5. In the sidebar, select **"My add-ins"**
6. Scroll to the bottom → **"Custom Add-ins"** section
7. Click **"Add a custom add-in"** → **"Add from file..."**
8. Upload the manifest file:
   - **Server deployment:** `outlook-addin/manifest.server.xml` (or download from `https://your-domain.com/mailpilot/manifest.xml`)
   - **Docker deployment:** `outlook-addin/manifest.docker.xml`
   - **Local dev:** `outlook-addin/manifest.xml`
9. Click **"Install"** when prompted

After installation, open any email. The **"Summarize"** button will appear in:
- The email toolbar (ribbon)
- Or inside the **"..."** (more actions) menu

### Option B — macOS Classic Outlook (sideload via filesystem)

> Only works with Classic Outlook (not "New Outlook for Mac").

```bash
# Create the sideload directory
mkdir -p ~/Library/Containers/com.microsoft.Outlook/Data/Documents/wef

# Copy the manifest (use the one matching your deployment)
cp outlook-addin/manifest.server.xml \
   ~/Library/Containers/com.microsoft.Outlook/Data/Documents/wef/manifest.xml

# Restart Outlook
osascript -e 'quit app "Microsoft Outlook"'
sleep 3
open -a "Microsoft Outlook"
```

### Option C — Windows Outlook (sideload)

```bash
# Use the Office dev CLI
cd outlook-addin
npx office-addin-debugging start manifest.xml desktop
```

Or manually: **File → Manage Add-ins** → follow the web interface steps from Option A.

### Troubleshooting the add-in

| Symptom | Cause & Fix |
|---|---|
| Button doesn't appear | Manifest not loaded. Re-upload via Option A. For work/school accounts, the admin may have disabled custom add-ins. |
| Task Pane is blank (white) | TLS certificate not trusted. Open `https://your-domain.com/mailpilot/` in the browser and verify no certificate warnings. |
| "Network Error" in Task Pane | Backend not running. Check: `curl https://your-domain.com/mailpilot/api/health` |
| "Unauthorized" error | API token mismatch. The token baked into the frontend JS must match `MAILPILOT_API_TOKEN` in `env.sh`. Re-run `bash deploy-server.sh --update` to rebuild. |
| API 502 error | OpenAI API issue. Check: `sudo journalctl -u mailpilot -f` for details. Verify your `OPENAI_API_KEY` is valid. |
| Work/school account: no "Custom Add-ins" option | IT admin has disabled sideloading. Ask them to enable it in Microsoft 365 Admin Center → Settings → Integrated apps → User uploaded apps. Or use a personal Outlook account. |

---

## Alternative: Docker Deployment

For local use or servers where you prefer containers over systemd.

### Prerequisites

- Docker and Docker Compose

### Deploy

```bash
# 1. Configure environment
bash configure.sh        # choose "Docker" mode when prompted

# 2. Generate self-signed TLS certs (Outlook requires HTTPS)
bash docker/generate-certs.sh

# 3. Trust the cert (macOS only, one-time)
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain certs/cert.pem

# 4. Launch
bash deploy.sh
# or: bash deploy.sh --detach  (background)
```

Services:
- **Frontend:** `https://localhost` (nginx serving static files + reverse proxy)
- **Backend:** uvicorn inside container, proxied via nginx

```bash
bash deploy.sh logs       # tail logs
bash deploy.sh down       # stop
```

Upload `manifest.docker.xml` to Outlook (see "Upload the Add-in" above).

---

## Local Development

For developing and debugging with hot-reload.

```bash
# 1. Configure
bash configure.sh         # choose "Local dev" mode

# 2. Install dependencies
bash setup.sh

# 3. Start dev servers
bash start.sh
# Backend:  http://localhost:8000
# Frontend: https://localhost:3000 (Vite + HMR)
```

Upload `manifest.xml` to Outlook for testing.

### Run tests

```bash
cd backend
source ../.venv-mailpilot/bin/activate   # or your venv
pytest
```

---

## Environment Variables

All configuration lives in `env.sh` (generated by `configure.sh` or `deploy-server.sh`). See `env.sh.example` for the full template.

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes | OpenAI API key (`sk-...`) |
| `MAILPILOT_API_TOKEN` | Yes | Shared secret for frontend↔backend auth (64-char hex) |
| `DEFAULT_MODEL` | No | Model for normal emails (default: `gpt-4o-mini`) |
| `ESCALATION_MODEL` | No | Model for sensitive emails (default: `gpt-4o`) |
| `DATABASE_URL` | No | SQLite connection string (default: `sqlite+aiosqlite:///./mailpilot.db`) |
| `MAILPILOT_ALLOWED_ORIGIN` | No | CORS origin (auto-set by deployment scripts) |

---

## API Endpoints

All endpoints are under `/api/` and require an `X-API-Key` header.

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Health check (no auth required) |
| `GET` | `/api/categories` | List available email categories |
| `POST` | `/api/analyze` | Analyze an email: returns summary, priority, deadline, and suggested categories |

### Example: analyze an email

```bash
curl -X POST https://your-domain.com/mailpilot/api/analyze \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-token" \
  -d '{
    "message_id": "AAMkAGI2...",
    "subject": "Q3 Budget Review — Action Required by Friday",
    "sender": "cfo@company.com",
    "body_text": "Hi team, please review the attached Q3 budget..."
  }'
```

Response:

```json
{
  "summary": "CFO requests the team to review the Q3 budget spreadsheet and submit comments by Friday.",
  "priority": "high",
  "deadline": "2026-06-13",
  "categories": [
    {"name": "Action Required", "confidence": 0.95},
    {"name": "Finance", "confidence": 0.82}
  ],
  "model_used": "gpt-4o-mini",
  "cached": false
}
```
