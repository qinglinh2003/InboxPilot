# ── MailPilot Frontend (multi-stage) ──────────────────
# Stage 1: Build React app with Vite
# Stage 2: Serve static files via nginx (+ reverse proxy for /api)
#
# Build context: code/ (project root)
# Usage:  docker build -f docker/frontend.Dockerfile .
# ──────────────────────────────────────────────────────

# ── Stage 1: Build ───────────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies (cached layer)
COPY outlook-addin/package.json outlook-addin/package-lock.json* ./
RUN npm install

# Copy source
COPY outlook-addin/ .

# Build-time env vars baked into the JS bundle.
# VITE_BACKEND_URL="" means relative URLs — nginx proxies /api to backend.
ARG VITE_BACKEND_URL=""
ARG VITE_API_TOKEN=""
ENV VITE_BACKEND_URL=$VITE_BACKEND_URL \
    VITE_API_TOKEN=$VITE_API_TOKEN

RUN npm run build

# ── Stage 2: Serve ───────────────────────────────────
FROM nginx:1.27-alpine

# Remove default nginx site
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx config
COPY docker/nginx.conf /etc/nginx/conf.d/mailpilot.conf

# Copy built static files from stage 1
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 443

CMD ["nginx", "-g", "daemon off;"]
