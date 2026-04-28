#!/usr/bin/env bash
# Zap Bot — one-command server setup
# Run this on a fresh Ubuntu 22.04 DigitalOcean droplet:
#   bash <(curl -sL https://raw.githubusercontent.com/zapitpest/zap-it-ai-bot/main/deploy.sh)
# Or after git clone: bash deploy.sh

set -e

REPO="https://github.com/zapitpest/zap-it-ai-bot.git"
APP_DIR="/opt/zapbot"
SERVICE="zapbot"

echo ""
echo "======================================"
echo "  Zap Bot — Deployment Script"
echo "======================================"
echo ""

# 1. System packages
echo "[1/6] Installing system packages..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv git

# 2. Clone or update repo
echo "[2/6] Downloading Zap Bot..."
if [ -d "$APP_DIR/.git" ]; then
    cd "$APP_DIR" && git pull origin main
else
    git clone "$REPO" "$APP_DIR"
    cd "$APP_DIR"
fi

# 3. Python virtualenv + dependencies
echo "[3/6] Installing Python dependencies..."
python3 -m venv venv
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

# 4. Create .env if missing
if [ ! -f "$APP_DIR/.env" ]; then
    echo "[4/6] Creating .env from template..."
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    echo ""
    echo "  *** ACTION REQUIRED ***"
    echo "  Edit /opt/zapbot/.env and fill in your API keys:"
    echo "    nano /opt/zapbot/.env"
    echo ""
    echo "  Required keys:"
    echo "    Sm8=             (ServiceM8)"
    echo "    ANTHROPIC_API_KEY="
    echo "    OPENAI_API_KEY="
    echo "    Gohighlevel="
    echo "    MANUS_API_KEY="
    echo "    META_ADS_TOKEN="
    echo "    META_AD_ACCOUNT_ID=act_61588715705652"
    echo "    GMAIL_APP_PASSWORD=roml wyrp sxxa tuvd"
    echo "    COMMERCIAL_SHEET_ID=1dDZdZ01d5MjdwYkfwxHgNvFisa1wQL_ReWZYR6RJZ7o"
    echo ""
    echo "  After editing, run: bash /opt/zapbot/deploy.sh"
    exit 0
else
    echo "[4/6] .env found — skipping"
fi

# 5. Systemd service (auto-start on reboot)
echo "[5/6] Installing systemd service..."
cat > /etc/systemd/system/${SERVICE}.service << EOF
[Unit]
Description=Zap Bot AI Automation
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=${APP_DIR}
ExecStart=${APP_DIR}/venv/bin/python scheduler.py
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ${SERVICE}
systemctl restart ${SERVICE}

# 6. Done
echo "[6/6] Done!"
echo ""
echo "======================================"
echo "  Zap Bot is running!"
echo "======================================"
echo ""
echo "  Check status:   systemctl status zapbot"
echo "  View live logs: journalctl -u zapbot -f"
echo "  Stop bot:       systemctl stop zapbot"
echo "  Restart bot:    systemctl restart zapbot"
echo ""
echo "  Run health check: cd /opt/zapbot && venv/bin/python health_check.py"
echo ""
