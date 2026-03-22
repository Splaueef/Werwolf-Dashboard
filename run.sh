#!/bin/bash
# Werwolf Dashboard launcher
# Handles GLX / OpenGL issues on Linux

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── GPU / GLX fix ─────────────────────────────────────────────────
export QT_XCB_GL_INTEGRATION=none
export QT_QUICK_BACKEND=software
export QTWEBENGINE_DISABLE_SANDBOX=1
export QTWEBENGINE_CHROMIUM_FLAGS="\
--disable-gpu \
--disable-gpu-sandbox \
--no-sandbox \
--disable-software-rasterizer \
--ignore-gpu-blacklist \
--disable-gpu-compositing \
--in-process-gpu"

# ── Platform ───────────────────────────────────────────────────────
# Prefer XCB over Wayland (WebEngine compat)
if [ -n "$WAYLAND_DISPLAY" ] && [ -z "$QT_QPA_PLATFORM" ]; then
    export QT_QPA_PLATFORM=xcb
fi
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"

# ── Find binary or Python ─────────────────────────────────────────
BINARY="$SCRIPT_DIR/dist/werwolf"
if [ -f "$BINARY" ]; then
    exec "$BINARY" "$@"
fi

BINARY="$SCRIPT_DIR/werwolf-linux"
if [ -f "$BINARY" ]; then
    exec "$BINARY" "$@"
fi

# Fallback: find Python with PyQt6
PYTHON=""
for VENV in "$SCRIPT_DIR/venv" "$SCRIPT_DIR/.venv"; do
    if [ -f "$VENV/bin/python" ]; then
        if "$VENV/bin/python" -c "import PyQt6.QtWebEngineWidgets" 2>/dev/null; then
            PYTHON="$VENV/bin/python"
            break
        fi
    fi
done

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
    echo "    pip install -r requirements.txt"
    echo ""
    exit 1
fi

cd "$SCRIPT_DIR"
exec "$PYTHON" werwolf.py "$@"
