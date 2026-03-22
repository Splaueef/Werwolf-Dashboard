# 🐺 Werwolf Dashboard

Кросплатформений desktop-додаток + PWA для Android
для роботи з Werwolf API.

---

## ⬇️ Завантаження

Можна одразу скачати готову збірку:

🔗 [https://github.com/Splaueef/Werwolf-Dashboard/releases/tag/v1.0.0](https://github.com/Splaueef/Werwolf-Dashboard/releases/tag/v1.0.0)

Або зібрати самостійно (див. нижче 👇)

---

## 🐧 Linux

### ▶️ Запуск з коду

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python werwolf.py
```

### ⚙️ Збірка в бінарник

```bash
python build.py linux
./dist/werwolf
```

---

## 🪟 Windows

### ▶️ Запуск з коду

```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python werwolf.py
```

### ⚙️ Збірка в `.exe`

```bat
python build.py windows
dist\werwolf.exe
```

> ⚠️ Потрібен встановлений Visual C++ Redistributable

---

## 📱 Android (PWA режим)

Можна використовувати як мобільний додаток через браузер.

### 🚀 Інструкція:

1. Запусти сервер на ПК:

   ```bash
   python werwolf.py
   ```

2. Дізнайся IP адрес ПК:

   ```bash
   hostname -I
   ```

3. Відкрий у Google Chrome на Android:

   ```
   http://192.168.x.x:7433
   ```

4. Натисни:

   ```
   ⋮ → Додати на головний екран
   ```

✅ Після цього додаток працює як нативний (без адресного рядка)

---

## 📂 Структура проєкту

```
werwolf/
├── werwolf.py          # Qt GUI + Flask сервер
├── requirements.txt
├── build.py            # python build.py [linux|windows|all]
├── run.sh              # запуск для Linux
└── static/
    ├── index.html      # веб-інтерфейс
    ├── manifest.json   # PWA маніфест
    ├── sw.js           # Service Worker (офлайн)
    └── icon-192.png    # іконка
```



