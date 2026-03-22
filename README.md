# Werwolf Dashboard

Нативний desktop-додаток + PWA для Android.

---

## 🐧 Linux

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python werwolf.py
```

**Компіляція в бінарник:**
```bash
python build.py linux
./dist/werwolf
```

---

## 🪟 Windows

```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python werwolf.py
```

**Компіляція в .exe:**
```bat
python build.py windows
dist\werwolf.exe
```

> Потребує Visual C++ Redistributable

---

## 📱 Android (PWA)

1. Запусти сервер на ПК:
   ```bash
   python werwolf.py
   ```

2. Знайди IP свого ПК:
   ```bash
   ip addr | grep 192
   # або: hostname -I
   ```

3. Відкрий у Chrome на Android:
   ```
   http://192.168.x.x:7433
   ```

4. Chrome → **⋮ → Додати на головний екран**

Після цього Werwolf відкривається як окремий додаток (без адресного рядка, як нативний).

---

## Структура

```
werwolf/
├── werwolf.py          ← Qt вікно + Flask (Linux/Windows/Mac)
├── requirements.txt
├── build.py            ← python build.py [linux|windows|all]
├── run.sh              ← розумний запускач для Linux
└── static/
    ├── index.html      ← веб-інтерфейс
    ├── manifest.json   ← PWA маніфест (Android)
    ├── sw.js           ← Service Worker (офлайн кеш)
    └── icon-192.png    ← іконка додатку
```
