#!/usr/bin/env python3
"""
Werwolf Dashboard — білд система
Використання:
  python build.py linux    — бінарник для Linux
  python build.py windows  — .exe для Windows (потрібен Wine або запускати на Windows)
  python build.py all      — все одразу
"""
import subprocess, sys, shutil, os, platform
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"

def run(cmd, **kw):
    print(f"\n▶  {' '.join(str(x) for x in cmd)}")
    r = subprocess.run(cmd, **kw)
    if r.returncode != 0:
        print(f"✗ Помилка (код {r.returncode})")
        sys.exit(r.returncode)
    return r

def pip(*pkgs):
    run([sys.executable, "-m", "pip", "install", *pkgs, "--quiet"])

def pyinstaller_cmd(name, extra=None):
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--name", name,
        "--add-data", f"static{os.pathsep}static",
        "--hidden-import", "flask",
        "--hidden-import", "flask.json.provider",
        "--hidden-import", "requests",
        "--hidden-import", "PyQt6.QtWebEngineWidgets",
        "--hidden-import", "PyQt6.QtWebEngineCore",
        "--hidden-import", "PyQt6.QtNetwork",
        "--collect-all", "PyQt6",
        "--collect-submodules", "flask",
    ]
    if extra:
        cmd.extend(extra)
    cmd.append("werwolf.py")
    return cmd

# ─────────────────────────────────────────────────────────────────
def build_linux():
    print("\n══════════════════════════════")
    print("  🐧  BUILD: Linux")
    print("══════════════════════════════")
    pip("pyinstaller", "PyQt6", "PyQt6-WebEngine", "flask", "requests")

    run(pyinstaller_cmd("werwolf", ["--onefile"]))

    out = DIST / "werwolf"
    if out.exists():
        os.chmod(out, 0o755)
        size = out.stat().st_size / 1024 / 1024
        print(f"\n✅  dist/werwolf  ({size:.1f} MB)")
        print(f"   Запуск: ./dist/werwolf\n")
    else:
        print("\n✗  Файл не знайдено\n"); sys.exit(1)

# ─────────────────────────────────────────────────────────────────
def build_windows():
    print("\n══════════════════════════════")
    print("  🪟  BUILD: Windows (.exe)")
    print("══════════════════════════════")

    is_windows = platform.system() == "Windows"
    if not is_windows:
        print("⚠  Ця команда призначена для запуску на Windows.")
        print("   На Linux скопіюй папку на Windows і запусти там:\n")
        print("   pip install -r requirements.txt")
        print("   pip install pyinstaller")
        print("   python build.py windows\n")
        # Create a helper bat file anyway
        bat = ROOT / "build_windows.bat"
        bat.write_text(
            "@echo off\n"
            "echo Building Werwolf for Windows...\n"
            "pip install -r requirements.txt pyinstaller\n"
            "python build.py windows\n"
            "pause\n",
            encoding="utf-8"
        )
        print(f"   Створено: build_windows.bat  (запусти на Windows)\n")
        return

    pip("pyinstaller", "PyQt6", "PyQt6-WebEngine", "flask", "requests", "pywin32")

    # Windows-specific: add icon, windowed mode, version info
    extra = [
        "--onefile",
        "--windowed",           # No console window
        "--version-file", str(_make_version_file()),
    ]
    # Add icon if exists
    icon = ROOT / "static" / "icon.ico"
    if icon.exists():
        extra += ["--icon", str(icon)]

    run(pyinstaller_cmd("werwolf", extra))

    out = DIST / "werwolf.exe"
    if out.exists():
        size = out.stat().st_size / 1024 / 1024
        print(f"\n✅  dist/werwolf.exe  ({size:.1f} MB)\n")
    else:
        print("\n✗  werwolf.exe не знайдено\n"); sys.exit(1)

def _make_version_file():
    """Create PyInstaller version file for Windows."""
    path = ROOT / "version_info.txt"
    path.write_text("""\
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(2,0,0,0), prodvers=(2,0,0,0),
    mask=0x3f, flags=0x0, OS=0x40004,
    fileType=0x1, subtype=0x0,
    date=(0,0)
  ),
  kids=[
    StringFileInfo([StringTable(
      u'040904B0',
      [StringStruct(u'CompanyName', u'Werwolf'),
       StringStruct(u'FileDescription', u'Werwolf Dashboard'),
       StringStruct(u'FileVersion', u'2.0.0.0'),
       StringStruct(u'InternalName', u'werwolf'),
       StringStruct(u'OriginalFilename', u'werwolf.exe'),
       StringStruct(u'ProductName', u'Werwolf Dashboard'),
       StringStruct(u'ProductVersion', u'2.0.0.0')]
    )]),
    VarFileInfo([VarStruct(u'Translation', [0x409, 1200])])
  ]
)
""", encoding="utf-8")
    return path

# ─────────────────────────────────────────────────────────────────
def main():
    target = sys.argv[1].lower() if len(sys.argv) > 1 else "linux"

    os.chdir(ROOT)

    if (DIST).exists() and "--clean" in sys.argv:
        shutil.rmtree(DIST)
    if (ROOT / "build").exists():
        shutil.rmtree(ROOT / "build")

    if target in ("linux", "all"):
        build_linux()
    if target in ("windows", "win", "all"):
        build_windows()

    if target not in ("linux", "windows", "win", "all"):
        print(f"\nНевідома ціль: {target}")
        print("Використання: python build.py [linux|windows|all]\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
