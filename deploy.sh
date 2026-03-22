#!/bin/bash
# deploy.sh — розгортання на VPS з існуючим Nginx + SSL
set -e

DOMAIN="${1:-dashboard.werwolf.pp.ua}"

echo ""
echo "🐺  Werwolf Dashboard — Deploy"
echo "    Домен: $DOMAIN"
echo ""

# ── 1. Docker ────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    echo "▶  Встановлення Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER"
    echo "   ⚠  Перезайди в сесію або виконай: newgrp docker"
fi

COMPOSE="docker compose"
if ! docker compose version &>/dev/null 2>&1; then
    COMPOSE="docker-compose"
fi

# ── 2. SECRET_KEY ────────────────────────────────────────────────
if grep -q "CHANGE_ME_TO_RANDOM_SECRET_KEY" docker-compose.yml; then
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i "s/CHANGE_ME_TO_RANDOM_SECRET_KEY/$SECRET/" docker-compose.yml
    echo "▶  SECRET_KEY згенеровано ✓"
fi

# ── 3. Запуск Flask контейнера ───────────────────────────────────
echo "▶  Збірка та запуск контейнера..."
$COMPOSE down 2>/dev/null || true
$COMPOSE up -d --build

# ── 4. Nginx конфіг ──────────────────────────────────────────────
echo ""
echo "▶  Налаштування Nginx..."
sed "s/dashboard.werwolf.pp.ua/$DOMAIN/g" nginx-vps.conf | sudo tee /etc/nginx/sites-available/werwolf > /dev/null
sudo ln -sf /etc/nginx/sites-available/werwolf /etc/nginx/sites-enabled/werwolf

if sudo nginx -t 2>/dev/null; then
    sudo systemctl reload nginx
    echo "   Nginx перезавантажено ✓"
else
    echo "   ⚠  Помилка в конфізі Nginx — перевір вручну:"
    echo "   sudo nginx -t"
fi

# ── 5. Перевірка ─────────────────────────────────────────────────
sleep 4
if curl -sf "http://127.0.0.1:7433/health" > /dev/null 2>&1; then
    echo ""
    echo "✅  Готово!"
    echo "    https://$DOMAIN"
    echo ""
    echo "   Логи:      $COMPOSE logs -f"
    echo "   Зупинка:   $COMPOSE down"
    echo "   Оновлення: git pull && $COMPOSE up -d --build"
else
    echo ""
    echo "⚠  Контейнер не відповідає:"
    $COMPOSE logs --tail=20
fi
