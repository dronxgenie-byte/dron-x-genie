"""Тест агента X — файловый мост NOD.

Отправляет запрос {"query": "Проверь сайт google.com", "agent": "x"} на /api/chat,
логирует ответ и время выполнения.

Перед запуском убедитесь, что сервер уже запущен:
    python -m uvicorn backend.agent.main:app --host 127.0.0.1 --port 8000
"""
from __future__ import annotations

import time

import requests

SERVER_URL = "http://127.0.0.1:8000"
CHAT_URL = f"{SERVER_URL}/api/chat"
TEST_PAYLOAD = {"query": "Проверь сайт google.com", "agent": "x"}


def main() -> None:
    # Проверяем, что сервер доступен
    try:
        r = requests.get(f"{SERVER_URL}/healthz", timeout=3)
        if r.status_code != 200:
            print("ОШИБКА: сервер не отвечает на /healthz")
            return
    except Exception as exc:
        print(f"ОШИБКА: сервер не доступен на {SERVER_URL}: {exc}")
        print("Запустите сервер: python -m uvicorn backend.agent.main:app --host 127.0.0.1 --port 8000")
        return

    print("Сервер доступен на http://127.0.0.1:8000")

    start = time.perf_counter()
    try:
        resp = requests.post(CHAT_URL, json=TEST_PAYLOAD, timeout=130)
        elapsed = round(time.perf_counter() - start, 3)
        body = resp.json()
    except requests.exceptions.Timeout:
        elapsed = round(time.perf_counter() - start, 3)
        print(f"ТАЙМАУТ: запрос занял {elapsed} сек (>120)")
        body = None
    except Exception as exc:
        elapsed = round(time.perf_counter() - start, 3)
        print(f"ОШИБКА запроса: {exc} (за {elapsed} сек)")
        body = None

    print("=" * 50)
    print(f"Время ответа: {elapsed} сек")
    print(f"HTTP статус: {resp.status_code if body is not None else 'N/A'}")
    print(f"Тело ответа: {body}")
    print("=" * 50)

    if body is not None:
        status = body.get("status")
        if status in ("ok", "error", "timeout"):
            print("Агент X интегрирован с NOD через файловый мост.")
        elif status == "skip":
            print("Статус skip — триггер не сработал (неожиданно для этого запроса).")
        else:
            print(f"Неизвестный статус: {status}")
    else:
        print("Тест не прошёл: нет корректного ответа от сервера.")


if __name__ == "__main__":
    main()
