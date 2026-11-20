"""Агент X — лёгкий роутер через файловый мост NOD.

Никаких харнессов, никаких tool-calls, никаких циклов планирования.
Только файловый IPC: задача в nod_bridge/task.json, результат из nod_bridge/result.json.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger("agent_x")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
NOD_BRIDGE_DIR = PROJECT_ROOT / "nod_bridge"
TASK_FILE = NOD_BRIDGE_DIR / "task.json"
RESULT_FILE = NOD_BRIDGE_DIR / "result.json"
LOCK_FILE = NOD_BRIDGE_DIR / ".lock"
WAIT_TIMEOUT = 30  # секунд (было 120)

# Триггеры веб-задач: сайт, браузер, проверь, найди, остатки, api
WEB_TRIGGERS = [
    r"\bсайт\b", r"\bбраузер\b", r"\bпроверь\b", r"\bнайди\b",
    r"\bостатки\b", r"\bapi\b",
    r"\bсайте\b", r"\bбраузере\b", r"\bпроверить\b", r"\bнайти\b",
]


class AgentX:
    """Лёгкий роутер агента X через файловый мост NOD.

    Единственный метод: handle_request(query).
    """

    def __init__(self) -> None:
        self._trigger_re = re.compile("|".join(WEB_TRIGGERS), re.IGNORECASE)
        NOD_BRIDGE_DIR.mkdir(parents=True, exist_ok=True)

    def _has_web_trigger(self, query: str) -> bool:
        return bool(query and self._trigger_re.search(query))

    @staticmethod
    def _atomic_write(path: Path, payload: dict) -> None:
        """Атомарная запись JSON: пишем во временный файл, затем переименовываем."""
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)

    @staticmethod
    def _acquire_lock(timeout: float = 5.0) -> bool:
        """Попытаться захватить .lock файл. Возвращает True если удалось."""
        start = time.perf_counter()
        while time.perf_counter() - start < timeout:
            try:
                # Эксклюзивное создание — если файл уже existe, другой процесс держит лок
                fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                return True
            except FileExistsError:
                time.sleep(0.1)
        return False

    @staticmethod
    def _release_lock() -> None:
        try:
            if LOCK_FILE.exists():
                LOCK_FILE.unlink()
        except OSError:
            pass

    @staticmethod
    def _safe_unlink(path: Path) -> None:
        try:
            if path.exists():
                path.unlink()
        except OSError:  # noqa: BLE001 — не критично, если файл не удалился
            pass

    def send_to_nod_via_file(self, query: str) -> dict[str, Any]:
        """Отправить задачу в NOD через файловый мост.

        Пишет task.json атомарно, ждёт result.json (до 30 сек),
        валидирует UUID совпадение, удаляет файлы только при status: ok.
        """
        task_id = str(uuid.uuid4())
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        task_payload = {"id": task_id, "task": query, "timestamp": timestamp}

        # Ждём освобождения лока (другой процесс может писать task.json)
        if not self._acquire_lock(timeout=5.0):
            logger.error("[AGENT X] Не удалось захватить .lock за 5 сек")
            return {"status": "error", "message": "Файловый мост занят. Повторите попытку."}

        try:
            # Атомарная запись task.json
            self._atomic_write(TASK_FILE, task_payload)
            logger.info("[AGENT X] Задача записана в %s (id=%s)", TASK_FILE, task_id)
        finally:
            self._release_lock()

        start = time.perf_counter()
        while time.perf_counter() - start < WAIT_TIMEOUT:
            if RESULT_FILE.exists():
                break
            time.sleep(0.5)

        if not RESULT_FILE.exists():
            elapsed = round(time.perf_counter() - start, 1)
            logger.error("[AGENT X] NOD не ответил за %s сек", elapsed)
            # НЕ удаляем task.json — пусть монитор попробует снова при следующем цикле
            return {
                "status": "timeout",
                "message": "NOD думает... Попробуйте позже.",
            }

        # Читаем result.json
        try:
            result = json.loads(RESULT_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("[AGENT X] Некорректный result.json: %s", exc)
            self._safe_unlink(TASK_FILE)
            self._safe_unlink(RESULT_FILE)
            return {"status": "error", "message": f"Некорректный ответ от NOD: {exc}"}

        # Валидация UUID — результат должен соответствовать нашей задаче
        result_task_id = result.get("task_id") or result.get("id")
        if result_task_id != task_id:
            logger.warning(
                "[AGENT X] Ignoring stale result: expected id=%s, got id=%s",
                task_id,
                result_task_id,
            )
            # Не удаляем task.json — это может быть результат от старой задачи,
            # а наша всё ещё ждёт ответа. Удаляем только result.json.
            self._safe_unlink(RESULT_FILE)
            return {
                "status": "error",
                "message": "Результат не соответствует текущей задаче. Повторите попытку.",
            }

        # Удаляем файлы только при успешном ответе
        if isinstance(result, dict) and result.get("status") == "ok":
            self._safe_unlink(TASK_FILE)
            self._safe_unlink(RESULT_FILE)
            return result

        # При ошибке от NOD — не удаляем task.json, пусть попробуют снова
        return result

    def handle_request(self, query: str) -> dict[str, Any]:
        """Обработать запрос.

        Если в запросе есть триггер веб-задачи — проксирует в NOD через файловый мост.
        Иначе возвращает {"status": "skip"}.
        """
        if not query or not self._has_web_trigger(query):
            return {"status": "skip"}

        return self.send_to_nod_via_file(query)
