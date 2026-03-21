#!/bin/bash
# Запускач Werwolf Dashboard
# Автоматично знаходить Python з PyQt6

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Якщо є venv поряд — використати його
for VENV in "$SCRIPT_DIR/venv" "$SCRIPT_DIR/.venv" "$HOME/venv" "$HOME/.venv"; do
    if [ -f "$VENV/bin/python" ]; then
        PYTHON="$VENV/bin/python"
        break
    fi
done

# Якщо venv не знайдено — шукаємо python з PyQt6
if [ -z "$PYTHON" ]; then
    for PY in python3 python python3.12 python3.11 python3.10; do
        if command -v "$PY" &>/dev/null; then
            if "$PY" -c "import PyQt6.QtWebEngineWidgets" 2>/dev/null; then
                PYTHON="$PY"
                break
            fi
        fi
    done
fi

if [ -z "$PYTHON" ]; then
    echo ""
    echo "❌  Не знайдено Python з PyQt6."
    echo ""
    echo "   Активуйте venv та встановіть:"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    echo ""
    exit 1
fi

echo "▶  Python: $PYTHON"

# Wayland fix
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
export QTWEBENGINE_CHROMIUM_FLAGS="--disable-gpu-sandbox --no-sandbox"

cd "$SCRIPT_DIR"
exec "$PYTHON" werwolf.py "$@"
