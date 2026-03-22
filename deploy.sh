#!/bin/bash
# deploy.sh — розгортання Werwolf Dashboard на VPS
# Використання: ./deploy.sh your-domain.com
set -e

DOMAIN="${1:-}"
if [ -z "$DOMAIN" ]; then
    echo "Використання: ./deploy.sh your-domain.com"
    exit 1
fi

echo ""
echo "🐺  Werwolf Dashboard — Deploy"
echo "    Домен: $DOMAIN"
echo ""

# ── 1. Встановити Docker ─────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    echo "▶  Встановлення Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
fi

if ! command -v docker-compose &>/dev/null && ! docker compose version &>/dev/null 2>&1; then
    echo "▶  Встановлення Docker Compose..."
    sudo apt-get install -y docker-compose-plugin
fi

# ── 2. Замінити домен у конфігах ─────────────────────────────────
echo "▶  Конфігурація домену: $DOMAIN"
sed -i "s/YOUR_DOMAIN/$DOMAIN/g" nginx.conf docker-compose.yml

# ── 3. Генерувати SECRET_KEY ─────────────────────────────────────
SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
sed -i "s/CHANGE_ME_TO_RANDOM_SECRET_KEY/$SECRET/" docker-compose.yml
echo "   SECRET_KEY згенеровано ✓"

# ── 4. SSL через Let's Encrypt ───────────────────────────────────
echo "▶  Отримання SSL сертифіката..."
sudo apt-get install -y certbot
sudo mkdir -p /var/www/certbot

# Тимчасово запустити Nginx без SSL для challenge
docker compose up -d nginx 2>/dev/null || true
sleep 3

sudo certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "admin@$DOMAIN" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN" \
    -d "www.$DOMAIN" || {
        echo "⚠  Certbot не вдалося. Запускаємо без SSL..."
        # Fallback: HTTP only config
        cat > nginx.conf << NGINX
server {
    listen 80;
    server_name $DOMAIN;
    location / {
        proxy_pass http://werwolf:7433;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
    location /static/ {
        proxy_pass http://werwolf:7433/static/;
        expires 7d;
    }
}
NGINX
    }

# ── 5. Запустити всі сервіси ─────────────────────────────────────
echo "▶  Запуск сервісів..."
docker compose up -d --build

# ── 6. Перевірка ─────────────────────────────────────────────────
sleep 5
if curl -sf "http://localhost:7433/health" > /dev/null; then
    echo ""
    echo "✅  Werwolf Dashboard запущено!"
    echo "    https://$DOMAIN"
    echo ""
    echo "   Перегляд логів: docker compose logs -f"
    echo "   Зупинка:        docker compose down"
    echo "   Оновлення:      git pull && docker compose up -d --build"
else
    echo "⚠  Сервіс не відповідає. Перевір логи:"
    echo "   docker compose logs"
fi
