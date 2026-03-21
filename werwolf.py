#!/usr/bin/env python3
"""
Werwolf Dashboard — нативний desktop додаток
Встановлення: pip install PyQt6 PyQt6-WebEngine flask requests
Запуск:       python werwolf.py
Компіляція:   python build.py
"""

import sys
import os
import platform
import re
import json
import threading
import time
from pathlib import Path

# ── Перевірка залежностей ──────────────────────────────────────────
def check_deps():
    missing = []
    checks = {
        "PyQt6":              "PyQt6.QtWidgets",
        "PyQt6-WebEngine":    "PyQt6.QtWebEngineWidgets",
        "flask":              "flask",
        "requests":           "requests",
    }
    for pkg, mod in checks.items():
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"\n❌  Встановіть залежності:")
        print(f"    pip install {' '.join(missing)}\n")
        print("    Якщо використовуєте venv:")
        print("    source venv/bin/activate && pip install -r requirements.txt\n")
        sys.exit(1)

check_deps()

import requests as req_lib
from flask import Flask, request, jsonify, send_from_directory

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QSizeGrip, QFrame
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtCore import (
    Qt, QUrl, QSize, QPoint, QTimer, pyqtSignal, QObject
)
from PyQt6.QtGui import QIcon, QColor, QPainter, QFont, QPixmap

# ══════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════
WERWOLF  = "https://werwolf.pp.ua"
PORT     = 7433
KEY_FILE = Path.home() / ".werwolf_key"
STATIC   = Path(__file__).parent / "static"

APP_NAME    = "Werwolf Dashboard"
APP_VERSION = "2.0"
WIN_W, WIN_H = 1200, 760
WIN_MIN_W, WIN_MIN_H = 900, 580

# Colors (match CSS variables)
C_BG      = "#0c0c0f"
C_TITLE   = "#111115"
C_ACCENT  = "#e8593c"
C_TEXT    = "#edeae4"
C_MUT     = "#72706a"
C_LINE    = "#2a2a36"

# ══════════════════════════════════════════════════════════════════════
# KEY MANAGEMENT
# ══════════════════════════════════════════════════════════════════════
def clean_key(k: str) -> str:
    return re.sub(r"[\x00-\x1f\x7f\s]", "", k or "")

def load_key() -> str:
    try:
        return clean_key(KEY_FILE.read_text()) if KEY_FILE.exists() else ""
    except Exception:
        return ""

def save_key(k: str):
    try:
        KEY_FILE.write_text(clean_key(k))
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════
# FLASK PROXY SERVER
# ══════════════════════════════════════════════════════════════════════
flask_app = Flask(__name__, static_folder=str(STATIC), static_url_path="/static")
flask_app.logger.disabled = True

import logging
log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

def proxy(method: str, path: str, key: str, body=None, params=None):
    url = f"{WERWOLF}/{path.lstrip('/')}"
    headers = {"Content-Type": "application/json"}
    k = clean_key(key)
    if k:
        headers["X-API-Key"] = k
    try:
        r = req_lib.request(method, url, headers=headers, json=body,
                            params=params, timeout=20)
        try:
            data = r.json()
        except Exception:
            data = {"error": r.text[:300]}
        return data, r.status_code
    except req_lib.exceptions.ConnectionError:
        return {"error": "Немає підключення до мережі"}, 502
    except req_lib.exceptions.Timeout:
        return {"error": "Таймаут (20с)"}, 504
    except Exception as e:
        return {"error": str(e)}, 500

@flask_app.route("/")
def index():
    return send_from_directory(STATIC, "index.html")

@flask_app.route("/api/key", methods=["GET"])
def get_key():
    return jsonify({"key": load_key()})

@flask_app.route("/api/key", methods=["POST"])
def set_key():
    k = clean_key(request.json.get("key", ""))
    save_key(k)
    return jsonify({"ok": True, "key": k})

@flask_app.route("/proxy/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def proxy_route(path):
    key    = clean_key(request.headers.get("X-API-Key", "") or load_key())
    body   = request.json if request.method in ("POST", "PUT") else None
    params = request.args.to_dict() if request.args else None
    data, status = proxy(request.method, path, key, body, params)
    return jsonify(data), status

def run_flask():
    flask_app.run(host="localhost", port=PORT, debug=False, use_reloader=False)

# ══════════════════════════════════════════════════════════════════════
# CUSTOM TITLE BAR
# ══════════════════════════════════════════════════════════════════════
class TitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_win = parent
        self._drag_pos  = None
        self.setFixedHeight(42)
        self.setStyleSheet(f"background:{C_TITLE};border-bottom:1px solid {C_LINE};")
        self._build()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 8, 0)
        layout.setSpacing(0)

        # Icon
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(24, 24)
        icon_lbl.setStyleSheet("background:transparent;")
        pix = self._wolf_icon()
        icon_lbl.setPixmap(pix)
        layout.addWidget(icon_lbl)

        layout.addSpacing(10)

        # Title
        title = QLabel(APP_NAME)
        title.setStyleSheet(f"""
            color:{C_TEXT};
            font-family:'Inter','Helvetica',sans-serif;
            font-size:13px;
            font-weight:500;
            background:transparent;
        """)
        layout.addWidget(title)

        layout.addStretch()

        # Version badge
        ver = QLabel(f"v{APP_VERSION}")
        ver.setStyleSheet(f"""
            color:{C_MUT};
            font-size:10px;
            background:transparent;
            padding-right:12px;
        """)
        layout.addWidget(ver)

        # Window buttons
        for label, tip, slot, color in [
            ("–", "Згорнути", self._minimize, "#555"),
            ("⤢", "Розгорнути", self._maximize, "#555"),
            ("✕", "Закрити",   self._close,    C_ACCENT),
        ]:
            btn = QPushButton(label)
            btn.setToolTip(tip)
            btn.setFixedSize(34, 28)
            btn.clicked.connect(slot)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background:transparent;
                    color:{color};
                    border:none;
                    font-size:14px;
                    border-radius:6px;
                }}
                QPushButton:hover {{
                    background:rgba(255,255,255,0.07);
                }}
                QPushButton:pressed {{
                    background:rgba(255,255,255,0.12);
                }}
            """)
            layout.addWidget(btn)

    def _wolf_icon(self) -> QPixmap:
        pix = QPixmap(24, 24)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(C_ACCENT))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(2, 2, 20, 20)
        p.setPen(QColor("#fff"))
        font = QFont("Arial", 11, QFont.Weight.Bold)
        p.setFont(font)
        p.drawText(0, 0, 24, 24, Qt.AlignmentFlag.AlignCenter, "W")
        p.end()
        return pix

    def _minimize(self):  self.parent_win.showMinimized()
    def _close(self):     self.parent_win.close()
    def _maximize(self):
        if self.parent_win.isMaximized():
            self.parent_win.showNormal()
        else:
            self.parent_win.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.parent_win.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            if self.parent_win.isMaximized():
                self.parent_win.showNormal()
                self._drag_pos = QPoint(self.parent_win.width() // 2, self.height() // 2)
            self.parent_win.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event):
        self._maximize()

# ══════════════════════════════════════════════════════════════════════
# STATUS BAR
# ══════════════════════════════════════════════════════════════════════
class StatusBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedHeight(26)
        self.setStyleSheet(f"""
            background:{C_TITLE};
            border-top:1px solid {C_LINE};
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(0)

        self._status = QLabel("Очікування...")
        self._status.setStyleSheet(f"color:{C_MUT};font-size:10px;background:transparent;")
        layout.addWidget(self._status)

        layout.addStretch()

        url_lbl = QLabel(f"localhost:{PORT}")
        url_lbl.setStyleSheet(f"color:{C_LINE};font-size:10px;font-family:monospace;background:transparent;")
        layout.addWidget(url_lbl)

        # Resize grip
        grip = QSizeGrip(parent)
        grip.setFixedSize(16, 16)
        grip.setStyleSheet("background:transparent;")
        layout.addWidget(grip)

    def set_text(self, text: str, color: str = C_MUT):
        self._status.setText(text)
        self._status.setStyleSheet(f"color:{color};font-size:10px;background:transparent;")

# ══════════════════════════════════════════════════════════════════════
# LOADING SCREEN
# ══════════════════════════════════════════════════════════════════════
class LoadingScreen(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setStyleSheet(f"background:{C_BG};")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Wolf logo
        logo = QLabel("🐺")
        logo.setStyleSheet(f"""
            font-size:48px;
            color:{C_ACCENT};
            background:transparent;
        """)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)

        title = QLabel(APP_NAME)
        title.setStyleSheet(f"""
            font-size:20px;
            font-weight:600;
            color:{C_TEXT};
            background:transparent;
            margin-top:8px;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self._msg = QLabel("Запуск сервера...")
        self._msg.setStyleSheet(f"""
            font-size:12px;
            color:{C_MUT};
            background:transparent;
            margin-top:4px;
        """)
        self._msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._msg)

        # Animated dots
        self._dots = QLabel("●  ○  ○")
        self._dots.setStyleSheet(f"color:{C_ACCENT};font-size:14px;background:transparent;margin-top:16px;")
        self._dots.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._dots)

        self._dot_state = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(400)

    def _animate(self):
        states = ["●  ○  ○", "○  ●  ○", "○  ○  ●"]
        self._dot_state = (self._dot_state + 1) % 3
        self._dots.setText(states[self._dot_state])

    def set_message(self, msg: str):
        self._msg.setText(msg)

    def stop(self):
        self._timer.stop()

# ══════════════════════════════════════════════════════════════════════
# MAIN WINDOW
# ══════════════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    _ready_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.resize(WIN_W, WIN_H)
        self.setMinimumSize(WIN_MIN_W, WIN_MIN_H)
        self._center()

        # Root widget
        root = QWidget()
        root.setStyleSheet(f"""
            QWidget {{
                background:{C_BG};
                font-family:'Inter','Helvetica',sans-serif;
            }}
        """)
        self.setCentralWidget(root)

        self._layout = QVBoxLayout(root)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        # Title bar
        self._titlebar = TitleBar(self)
        self._layout.addWidget(self._titlebar)

        # Stacked area (loading / web)
        self._stack = QWidget()
        self._stack_layout = QVBoxLayout(self._stack)
        self._stack_layout.setContentsMargins(0, 0, 0, 0)
        self._stack_layout.setSpacing(0)
        self._layout.addWidget(self._stack, stretch=1)

        # Loading screen
        self._loading = LoadingScreen(self)
        self._stack_layout.addWidget(self._loading)

        # Web view (hidden initially)
        self._web = QWebEngineView()
        self._web.hide()
        self._web.setStyleSheet(f"background:{C_BG};border:none;")

        # Disable right-click context menu
        self._web.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

        # Custom page to handle new window requests
        page = self._web.page()
        page.setBackgroundColor(QColor(C_BG))

        self._stack_layout.addWidget(self._web)

        # Status bar
        self._statusbar = StatusBar(self)
        self._layout.addWidget(self._statusbar)

        # Border
        root.setStyleSheet(f"""
            QWidget#root {{
                border:1px solid {C_LINE};
                border-radius:0px;
            }}
        """)

        # Connect signal
        self._ready_signal.connect(self._on_server_ready)

        # Start Flask in background thread
        self._flask_thread = threading.Thread(target=run_flask, daemon=True)
        self._flask_thread.start()

        # Poll until Flask is ready
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._check_server)
        self._poll_timer.start(200)

        self._statusbar.set_text("Запуск Flask сервера...")

    def _center(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width()  - WIN_W) // 2
        y = (screen.height() - WIN_H) // 2
        self.move(x, y)

    def _check_server(self):
        try:
            import urllib.request
            urllib.request.urlopen(f"http://localhost:{PORT}/", timeout=1)
            self._poll_timer.stop()
            self._ready_signal.emit()
        except Exception:
            pass

    def _on_server_ready(self):
        self._loading.set_message("Завантаження інтерфейсу...")
        self._statusbar.set_text("Завантаження...", C_MUT)
        self._web.loadFinished.connect(self._on_load_finished)
        self._web.load(QUrl(f"http://localhost:{PORT}/"))

    def _on_load_finished(self, ok: bool):
        if ok:
            self._loading.stop()
            self._loading.hide()
            self._web.show()
            self._statusbar.set_text("Готово", "#5dcaa5")
        else:
            self._loading.set_message("Помилка завантаження — перевірте з'єднання")
            self._statusbar.set_text("Помилка завантаження", C_ACCENT)

    # ── Drag to resize from edges ──────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._resize_edge = self._get_edge(event.position().toPoint())

    def _get_edge(self, pos):
        m = 6
        x, y, w, h = pos.x(), pos.y(), self.width(), self.height()
        edges = []
        if x < m:     edges.append("left")
        if x > w - m: edges.append("right")
        if y < m:     edges.append("top")
        if y > h - m: edges.append("bottom")
        return edges


# ══════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════
def main():
    # Platform-specific setup
    _platform = platform.system()

    if _platform == "Windows":
        # Windows: hide console window
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(APP_NAME)
        except Exception:
            pass
        os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS",
            "--disable-gpu-sandbox --no-sandbox")
    elif _platform == "Linux":
        # Linux: prefer xcb over wayland for WebEngine compat
        if "WAYLAND_DISPLAY" in os.environ and "QT_QPA_PLATFORM" not in os.environ:
            os.environ["QT_QPA_PLATFORM"] = "xcb"
        os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS",
            "--disable-gpu-sandbox --no-sandbox --disable-software-rasterizer")
    elif _platform == "Darwin":
        # macOS
        os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    # App-wide stylesheet
    app.setStyleSheet(f"""
        QToolTip {{
            background:{C_TITLE};
            color:{C_TEXT};
            border:1px solid {C_LINE};
            font-size:11px;
            padding:4px 8px;
        }}
        QScrollBar:vertical {{
            background:{C_BG};
            width:6px;
            margin:0;
        }}
        QScrollBar::handle:vertical {{
            background:{C_LINE};
            border-radius:3px;
            min-height:20px;
        }}
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height:0;
        }}
    """)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
