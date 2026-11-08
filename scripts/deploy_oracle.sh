#!/usr/bin/env bash
# ==============================================================================
# ATHINA ORACLE CLOUD ALWAYS FREE VM DEPLOYMENT SCRIPT
# One-command setup for Ubuntu 22.04 LTS (Ampere A1 / AMD VM)
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "======================================================"
echo "    ATHINA AI COMPANION - PRODUCTION DEPLOYMENT      "
echo "======================================================"

cd "$ROOT_DIR"

# 1. Check Docker & Docker Compose
if ! command -v docker &> /dev/null; then
    echo "[!] Docker not found. Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER" || true
fi

# 2. Check Environment File
if [ ! -f "backend/.env" ]; then
    echo "[*] Creating backend/.env from template..."
    cat << 'EOF' > backend/.env
# Athina Core Environment Variables
GEMINI_API_KEYS=your_gemini_key_1,your_gemini_key_2
GROQ_API_KEYS=your_groq_key_1
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_USER_ID=
TELEGRAM_BACKUP_CHANNEL_ID=
ADMIN_SECRET=athina_secret_key_change_me
POSTGRES_USER=athina
POSTGRES_PASSWORD=athina_secure_password
POSTGRES_DB=athina
ATHINA_DOMAIN=localhost
EOF
    echo "[!] Please edit backend/.env with your actual API keys before continuing."
fi

# 3. Build & Launch Containers
echo "[*] Building and starting Athina containers..."
docker compose pull db caddy || true
docker compose up -d --build

# 4. Wait for database and verify health
echo "[*] Waiting for services to become healthy..."
sleep 5

# Check health endpoint
if curl -s http://127.0.0.1:8000/api/health | grep -q "healthy"; then
    echo "[✓] Athina Backend is Healthy and Operational!"
else
    echo "[!] Warning: Backend healthcheck did not respond immediately. Check 'docker compose logs backend'."
fi

echo "======================================================"
echo "  Athina Engine is deployed successfully!             "
echo "  API Docs: http://localhost:8000/docs                "
echo "  Health  : http://localhost:8000/api/health          "
echo "======================================================"
