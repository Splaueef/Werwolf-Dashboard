#!/bin/bash
# deploy.sh — розгортання Werwolf Dashboard на VPS
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

# ── 1. Docker ────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    echo "▶  Встановлення Docker..."
    sudo apt-get update -qq
    sudo apt-get install -y ca-certificates curl gnupg lsb-release
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
        | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update -qq
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
        docker-buildx-plugin docker-compose-plugin
    sudo usermod -aG docker "$USER"
    echo "   Docker встановлено ✓"
else
    echo "   Docker вже встановлено ✓"
fi

# Перевірити docker compose (plugin або standalone)
if docker compose version &>/dev/null 2>&1; then
    COMPOSE="docker compose"
elif command -v docker-compose &>/dev/null; then
    COMPOSE="docker-compose"
else
    echo "▶  Встановлення docker-compose (standalone)..."
    sudo curl -fsSL \
        "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    COMPOSE="docker-compose"
fi
echo "   Compose: $COMPOSE ✓"

# ── 2. Домен у конфігах ──────────────────────────────────────────
echo "▶  Конфігурація домену: $DOMAIN"
sed -i "s/YOUR_DOMAIN/$DOMAIN/g" nginx.conf docker-compose.yml 2>/dev/null || true

# ── 3. SECRET_KEY ────────────────────────────────────────────────
if grep -q "CHANGE_ME_TO_RANDOM_SECRET_KEY" docker-compose.yml 2>/dev/null; then
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i "s/CHANGE_ME_TO_RANDOM_SECRET_KEY/$SECRET/" docker-compose.yml
    echo "   SECRET_KEY згенеровано ✓"
fi

# ── 4. SSL ───────────────────────────────────────────────────────
echo "▶  SSL сертифікат (Let's Encrypt)..."
sudo apt-get install -y certbot -qq 2>/dev/null || true
sudo mkdir -p /var/www/certbot

# Спочатку запустити тільки app без nginx щоб отримати сертифікат
$COMPOSE up -d werwolf 2>/dev/null || sudo docker run -d \
    -e SECRET_KEY="$SECRET" \
    -p 7433:7433 \
    --name werwolf_tmp \
    $(sudo docker build -q .) 2>/dev/null || true

# Тимчасовий nginx для challenge
sudo apt-get install -y nginx -qq 2>/dev/null || true
sudo mkdir -p /var/www/certbot
sudo nginx -t 2>/dev/null && sudo systemctl start nginx 2>/dev/null || true

sudo certbot certonly \
    --webroot --webroot-path=/var/www/certbot \
    --email "admin@$DOMAIN" \
    --agree-tos --no-eff-email \
    -d "$DOMAIN" 2>/dev/null \
|| sudo certbot certonly \
    --standalone \
    --email "admin@$DOMAIN" \
    --agree-tos --no-eff-email \
    -d "$DOMAIN" 2>/dev/null \
|| {
    echo "   ⚠  SSL не вдалося — запускаємо без HTTPS"
    cat > nginx.conf << NGINX
server {
    listen 80;
    server_name $DOMAIN;
    client_max_body_size 1m;

    location / {
        proxy_pass http://werwolf:7433;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_read_timeout 30s;
    }
    location /static/ {
        proxy_pass http://werwolf:7433/static/;
        expires 7d;
    }
}
NGINX
        # Прибрати nginx сервіс з compose якщо немає SSL
        sed -i '/ssl_certificate/d' nginx.conf 2>/dev/null || true
}

sudo systemctl stop nginx 2>/dev/null || true
sudo docker rm -f werwolf_tmp 2>/dev/null || true

# ── 5. Запуск ────────────────────────────────────────────────────
echo "▶  Запуск сервісів..."
$COMPOSE down 2>/dev/null || true
$COMPOSE up -d --build

# ── 6. Перевірка ─────────────────────────────────────────────────
echo "▶  Перевірка..."
sleep 6
if curl -sf "http://localhost:7433/health" > /dev/null 2>&1; then
    echo ""
    echo "✅  Werwolf Dashboard запущено!"
    if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
        echo "    https://$DOMAIN"
    else
        echo "    http://$DOMAIN"
    fi
    echo ""
    echo "   Логи:      $COMPOSE logs -f"
    echo "   Зупинка:   $COMPOSE down"
    echo "   Оновлення: git pull && $COMPOSE up -d --build"
else
    echo ""
    echo "⚠  Сервіс не відповідає. Перевір логи:"
    $COMPOSE logs --tail=30
fi
