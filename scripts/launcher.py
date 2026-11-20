#!/usr/bin/env python3
"""DRON X GENIE — лаунчер проекта."""
import os
import sys
import subprocess
import webbrowser
from pathlib import Path

# ============ НАСТРОЙКИ ============
PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = PROJECT_ROOT / ".venv"
VENV_PYTHON = VENV_DIR / "Scripts" / "python.exe"
ACTIVATE_BAT = VENV_DIR / "Scripts" / "activate.bat"
SETUP_ENV_PS1 = PROJECT_ROOT / "scripts" / "setup_env.ps1"
BACKEND_PORT = 8000
FRONTEND_PORT = 3000

# Точное имя модели из LM Studio (проверь через 'lms ls' в терминале)
MODEL_KEY = "gemma-4-e4b-agentic-sol-fable-reasoning-geminicli"
LMSTUDIO_WAIT = 10
# ===================================


def log(msg):
    print(f"[DRON] {msg}", flush=True)


def ensure_venv():
    """Проверяет и при необходимости создаёт .venv через setup_env.ps1."""
    if not VENV_PYTHON.exists():
        log(".venv не найден. Запускаю настройку окружения...")
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(SETUP_ENV_PS1)],
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode != 0:
            log("ОШИБКА: не удалось создать .venv")
            sys.exit(1)
        log(".venv создан.")
    else:
        log(".venv найден.")


def find_lms():
    import shutil
    p = shutil.which("lms")
    if p:
        return p
    fallback = Path(os.environ["USERPROFILE"]) / ".lmstudio" / "bin" / "lms.exe"
    if fallback.exists():
        return str(fallback)
    return None


def start_lmstudio():
    lms = find_lms()
    if not lms:
        log("LM Studio CLI не найден. Запускаю GUI...")
        app = Path(os.environ["LOCALAPPDATA"]) / "Programs" / "lm-studio" / "LM Studio.exe"
        if app.exists():
            subprocess.Popen([str(app)])
        else:
            log("LM Studio не найден. Запустите вручную.")
        return

    log(f"LM Studio CLI найден: {lms}")
    log(f"Загружаю модель: {MODEL_KEY}")

    r = subprocess.run(
        [lms, "load", MODEL_KEY, "--gpu=max", "--context-length=8192"],
        capture_output=True, text=True, timeout=120
    )
    if r.returncode != 0:
        log(f"Не удалось загрузить модель: {r.stderr.strip()}")
        log("Запускаю GUI LM Studio (загрузите модель вручную)")
        app = Path(os.environ["LOCALAPPDATA"]) / "Programs" / "lm-studio" / "LM Studio.exe"
        if app.exists():
            subprocess.Popen([str(app)])
        return

    log(f"Стартую API-сервер LM Studio на порту 1234")
    subprocess.run(
        [lms, "server", "start", "--port", "1234"],
        capture_output=True, text=True, timeout=30
    )
    log(f"Жду {LMSTUDIO_WAIT} сек прогрева модели...")
    import time
    time.sleep(LMSTUDIO_WAIT)


def start_backend():
    # Запускаем uvicorn через activate.bat (как setup_env.ps1)
    cmd = f"""\"{ACTIVATE_BAT}\" && cd \"{PROJECT_ROOT / 'backend'}\" && uvicorn agent.main:app --host 127.0.0.1 --port {BACKEND_PORT}"""
    log(f"Backend: {cmd}")
    return subprocess.Popen(cmd, shell=True, cwd=str(PROJECT_ROOT))


def start_frontend():
    py = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable
    cmd = [py, "-m", "http.server", str(FRONTEND_PORT)]
    log(f"Frontend: {' '.join(cmd)}")
    return subprocess.Popen(cmd, cwd=str(PROJECT_ROOT))


def main():
    log("=" * 50)
    log("DRON X GENIE - запуск системы")
    log("=" * 50)

    ensure_venv()
    start_lmstudio()
    backend = start_backend()
    frontend = start_frontend()

    import time
    time.sleep(3)
    url = f"http://localhost:{FRONTEND_PORT}/vault/frontend/dron_ui/tv_main.html"
    log(f"Открываю интерфейс: {url}")
    webbrowser.open(url)

    log("Готово. Окно можно свернуть. Ctrl+C - остановить всё.")
    try:
        backend.wait()
    except KeyboardInterrupt:
        log("Остановка...")
        backend.terminate()
        frontend.terminate()


if __name__ == "__main__":
    main()
