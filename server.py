#!/usr/bin/env python3
"""
Werwolf Dashboard — VPS / multi-user web server
Кожен користувач входить своїм API ключем через браузер.

Запуск локально:    python server.py
Запуск продакшен:   gunicorn -w 4 -b 0.0.0.0:7433 server:app

Змінні середовища:
  PORT          — порт (default: 7433)
  SECRET_KEY    — секрет для сесій (ОБОВ'ЯЗКОВО змінити на VPS!)
  ALLOWED_HOSTS — через кому, наприклад: mysite.com,www.mysite.com
"""

import os
import re
import secrets
import requests as req_lib
from pathlib import Path
from flask import (
    Flask, request, jsonify, send_from_directory,
    session, redirect, url_for, make_response
)
from functools import wraps

# ── Config ─────────────────────────────────────────────────────────
WERWOLF    = "https://werwolf.pp.ua"
PORT       = int(os.environ.get("PORT", 7433))
SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(32))
STATIC     = Path(__file__).parent / "static"
SESSION_LIFETIME = 60 * 60 * 24 * 30   # 30 днів

if SECRET_KEY == secrets.token_hex(32):
    print("⚠  SECRET_KEY не задано — сесії скидатимуться при перезапуску.")
    print("   Встанови: export SECRET_KEY='your-random-secret'\n")

# ── App ─────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=str(STATIC), static_url_path="/static")
app.secret_key = SECRET_KEY
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("HTTPS", "0") == "1",
    PERMANENT_SESSION_LIFETIME=SESSION_LIFETIME,
)

# ── Key helpers ─────────────────────────────────────────────────────
def clean_key(k: str) -> str:
    return re.sub(r"[\x00-\x1f\x7f\s]", "", k or "")

def get_session_key() -> str:
    return clean_key(session.get("api_key", ""))

# ── Auth decorator ──────────────────────────────────────────────────
def require_key(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not get_session_key():
            return jsonify({"error": "Не авторизовано. Введіть API ключ."}), 401
        return f(*args, **kwargs)
    return wrapper

# ── Proxy ───────────────────────────────────────────────────────────
def proxy(method: str, path: str, key: str, body=None, params=None):
    url = f"{WERWOLF}/{path.lstrip('/')}"
    headers = {"Content-Type": "application/json"}
    k = clean_key(key)
    if k:
        headers["X-API-Key"] = k
    try:
        r = req_lib.request(
            method, url, headers=headers,
            json=body, params=params, timeout=20
        )
        try:    data = r.json()
        except: data = {"error": r.text[:300]}
        return data, r.status_code
    except req_lib.exceptions.ConnectionError:
        return {"error": "Немає з'єднання з Werwolf"}, 502
    except req_lib.exceptions.Timeout:
        return {"error": "Таймаут (20с)"}, 504
    except Exception as e:
        return {"error": str(e)}, 500

# ══════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════

# ── Головна сторінка ─────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(STATIC, "index.html")

# ── Сесія / авторизація ──────────────────────────────────────────
@app.route("/api/key", methods=["GET"])
def get_key():
    key = get_session_key()
    # Повертаємо маскований ключ для безпеки
    if key:
        masked = key[:6] + "•" * (len(key) - 10) + key[-4:] if len(key) > 10 else "•" * len(key)
    else:
        masked = ""
    return jsonify({"key": key, "masked": masked, "logged_in": bool(key)})

@app.route("/api/key", methods=["POST"])
def set_key():
    data = request.json or {}
    k = clean_key(data.get("key", ""))
    if not k:
        session.pop("api_key", None)
        return jsonify({"ok": True, "logged_in": False})

    # Перевіряємо ключ перед збереженням
    test_data, test_status = proxy("GET", "api/profile", k)
    if test_status == 401:
        return jsonify({"error": "Невірний API ключ"}), 401
    if test_status >= 500:
        return jsonify({"error": "Werwolf сервер недоступний"}), 502

    session.permanent = True
    session["api_key"] = k
    return jsonify({"ok": True, "logged_in": True})

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})

@app.route("/api/session", methods=["GET"])
def session_info():
    key = get_session_key()
    return jsonify({
        "logged_in": bool(key),
        "key_prefix": key[:6] + "..." if key else None,
    })

# ── Проксі до Werwolf ────────────────────────────────────────────
@app.route("/proxy/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
@require_key
def proxy_route(path):
    key    = get_session_key()
    body   = request.json if request.method in ("POST", "PUT") else None
    params = request.args.to_dict() if request.args else None
    data, status = proxy(request.method, path, key, body, params)
    return jsonify(data), status

# ── Health check ─────────────────────────────────────────────────
@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "werwolf-dashboard"})

# ══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import threading, webbrowser, time

    def _open():
        time.sleep(1)
        webbrowser.open(f"http://localhost:{PORT}")

    print(f"\n  🐺  Werwolf Dashboard (web mode)")
    print(f"  ──────────────────────────────────")
    print(f"  http://localhost:{PORT}")
    print(f"  Ctrl+C — зупинити\n")

    threading.Thread(target=_open, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT, debug=False)
