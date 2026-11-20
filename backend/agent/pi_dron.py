"""PI Дрон — координатор синхронизации и управления системой ANANISIM OS.

PI = Programming Intelligence / Project Intelligence
Дрон в скафандре программирования управляет:
- Синхронизацией между DRON_X_GENIE (память) и dron-x-genie (код)
- Подключением n8n через MCP
- Координацией всех агентов системы
- Мониторингом целостности данных
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

import requests

# Пути: PROJECT — код, VAULT — память (Obsidian). Граница жёсткая.
from .config import PROJECT_ROOT, VAULT_ROOT

PROJECT_PATH = PROJECT_ROOT
VAULT_PATH = VAULT_ROOT
N8N_PATH = PROJECT_PATH / "n8n"  # Автоматизации
ROOT = PROJECT_PATH  # совместимость

# Куда PI Дрон кладёт снимок кода внутри волта (не мусорит в корень).
SNAPSHOT_DIR = VAULT_PATH / "85_AGENTS" / "CODE_SNAPSHOT"

READY = "ready"
UNAVAILABLE = "unavailable"
SYNCING = "syncing"
ERROR = "error"

# ===== Адаптивный режим исполнения Дрона (Cloud Live / Local Offline) =====

CLOUD_LIVE = "CLOUD_LIVE"
LOCAL_OFFLINE = "LOCAL_OFFLINE"

_CLOUD_ENDPOINTS = [
    "https://api.groq.com/openai/v1/models",
    "https://api.sambanova.ai/v1/models",
]

_MODE_CACHE: str | None = None
_MODE_CACHE_TIME: float = 0.0
_MODE_CACHE_TTL = 60.0  # segundos — перепроверяем не чаще раза в минуту

logger = logging.getLogger("dron.execution_mode")


def get_execution_mode(timeout: int = 2) -> str:
    """Определить режим исполнения Дрона: CLOUD_LIVE или LOCAL_OFFLINE.

    Проверяет доступность облачных эндпоинтов с жёстким таймаутом.
    Результат кэшируется на MODE_CACHE_TTL секунд, чтобы не пинговать
    облако при каждом сообщении и не получать баны от провайдеров.
    При любой ошибке или таймауте — graceful degradation в LOCAL_OFFLINE.
    """
    global _MODE_CACHE, _MODE_CACHE_TIME

    now = time.monotonic()
    if _MODE_CACHE is not None and (now - _MODE_CACHE_TIME) < _MODE_CACHE_TTL:
        return _MODE_CACHE

    mode = LOCAL_OFFLINE
    for url in _CLOUD_ENDPOINTS:
        try:
            if requests.get(url, timeout=timeout).status_code == 200:
                mode = CLOUD_LIVE
                break
        except Exception:  # сетевой сбой, таймаут, refused — продолжаем перебор
            continue

    if mode != _MODE_CACHE:
        _MODE_CACHE = mode
        _MODE_CACHE_TIME = now
        logger.debug("[DRON] Mode switched to %s", mode)

    return mode


PROJECT_ROOT_FOR_PROMPTS = Path(__file__).resolve().parents[2]
PROMPTS_DIR = PROJECT_ROOT_FOR_PROMPTS / "prompts"


def load_prompt(name: str) -> str:
    """Прочитать файл системного промпта из prompts/."""
    path = PROMPTS_DIR / name
    if not path.exists():
        logger.warning("[DRON] Prompt file not found: %s, fallback to default", path)
        return DRON_SYSTEM_PROMPT if "DRON_SYSTEM_PROMPT" in globals() else ""
    return path.read_text(encoding="utf-8")


class PIDronError(Exception):
    """Ошибка PI Дрона."""
    pass


class PIDron:
    """Координатор синхронизации ANANISIM OS."""
    
    def __init__(self):
        self.vault_path = VAULT_PATH
        self.project_path = PROJECT_PATH
        self.n8n_path = N8N_PATH
        self.sync_log: list[dict] = []
        self._callbacks: list[Callable] = []
        
    async def status(self) -> dict:
        """Проверить статус системы."""
        return {
            "status": READY if self.vault_path.exists() and self.project_path.exists() else UNAVAILABLE,
            "vault": str(self.vault_path),
            "project": str(self.project_path),
            "n8n": str(self.n8n_path) if self.n8n_path.exists() else None,
            "last_sync": self._get_last_sync_time(),
            "components": await self._check_components(),
        }
    
    async def _check_components(self) -> dict:
        """Проверить компоненты системы."""
        return {
            "vault_exists": self.vault_path.exists(),
            "project_exists": self.project_path.exists(),
            "n8n_exists": self.n8n_path.exists(),
            "backend_exists": (self.project_path / "backend").exists() if self.project_path.exists() else False,
            "frontend_exists": (self.project_path / "frontend").exists() if self.project_path.exists() else False,
        }
    
    def _get_last_sync_time(self) -> str | None:
        """Получить время последней синхронизации."""
        log_file = self.project_path / "data" / "sync_log.json"
        if log_file.exists():
            try:
                data = json.loads(log_file.read_text(encoding="utf-8"))
                return data.get("last_sync", "never")
            except Exception:
                return None
        return None
    
    async def sync_vault_to_project(self, files: list[str] | None = None) -> dict:
        """Собрать индекс памяти (Vault) для агентов проекта.

        Заметки НЕ копируются в проект — только индекс (путь, размер, mtime).
        Результат: PROJECT/data/vault_index.json
        """
        if not self.vault_path.exists():
            raise PIDronError(f"Vault не найден: {self.vault_path}")

        skip_dirs = {".obsidian", ".smart-env", ".git", "90_ARCHIVE", "dron-x-genie"}
        indexed: list[dict] = []
        errors: list[str] = []

        for path in self.vault_path.rglob("*.md"):
            try:
                rel = path.relative_to(self.vault_path)
                if any(part in skip_dirs for part in rel.parts[:-1]):
                    continue
                stat = path.stat()
                indexed.append(
                    {
                        "path": rel.as_posix(),
                        "size": stat.st_size,
                        "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                    }
                )
            except OSError as exc:
                errors.append(f"{path}: {exc}")

        target = self.project_path / "data" / "vault_index.json"
        payload = {
            "generated": datetime.now().isoformat(timespec="seconds"),
            "vault": str(self.vault_path),
            "count": len(indexed),
            "notes": sorted(indexed, key=lambda item: item["path"]),
        }
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            self._log_sync("vault→index", "data/vault_index.json", "ok")
        except OSError as exc:
            errors.append(f"data/vault_index.json: {exc}")
            self._log_sync("vault→index", "data/vault_index.json", "error", str(exc))

        return {
            "success": not errors,
            "synced": ["data/vault_index.json"] if not errors else [],
            "indexed": len(indexed),
            "errors": errors,
            "count": 1 if not errors else 0,
        }
    
    async def sync_project_to_vault(self, files: list[str] | None = None) -> dict:
        """Положить снимок кода проекта внутрь волта: 85_AGENTS/CODE_SNAPSHOT.

        Копируется только код и документация проекта — без data/, логов и кэшей,
        чтобы корень волта и заметки Obsidian оставались чистыми.
        """
        if not self.project_path.exists():
            raise PIDronError(f"Проект не найден: {self.project_path}")
        if not self.vault_path.exists():
            raise PIDronError(f"Vault не найден: {self.vault_path}")

        skip_dirs = {"data", "logs", "__pycache__", ".git", "node_modules", ".venv", "n8n"}
        patterns = ("backend/**/*.py", "frontend/**/*.html", "frontend/**/*.css", "frontend/**/*.js", "prompts/**/*.json")

        synced: list[str] = []
        errors: list[str] = []

        for pattern in patterns:
            for src in self.project_path.glob(pattern):
                if not src.is_file():
                    continue
                rel = src.relative_to(self.project_path)
                if any(part in skip_dirs or part.endswith(".pyc") for part in rel.parts):
                    continue
                dst = SNAPSHOT_DIR / rel
                try:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    synced.append(rel.as_posix())
                    self._log_sync("project→snapshot", rel.as_posix(), "ok")
                except OSError as exc:
                    errors.append(f"{rel.as_posix()}: {exc}")
                    self._log_sync("project→snapshot", rel.as_posix(), "error", str(exc))

        # Манифест снимка — чтобы в Obsidian было видно, что это и когда снято.
        manifest = SNAPSHOT_DIR / "MANIFEST.md"
        try:
            lines = [
                "# Снимок кода ANANISIM OS",
                "",
                f"- Проект: `{self.project_path}`",
                f"- Снято: {datetime.now().isoformat(timespec='seconds')}",
                f"- Файлов: {len(synced)}",
                "",
                "## Файлы",
                "",
            ]
            lines += [f"- `{name}`" for name in sorted(synced)]
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except OSError as exc:
            errors.append(f"MANIFEST.md: {exc}")

        return {
            "success": not errors,
            "synced": synced,
            "errors": errors,
            "count": len(synced),
        }
    
    async def sync_all(self, direction: str = "bidirectional") -> dict:
        """Полная синхронизация всех компонентов."""
        result = {
            "vault_to_project": None,
            "project_to_vault": None,
            "n8n_sync": None,
            "total": 0,
            "errors": [],
        }
        
        try:
            if direction in ["vault_to_project", "bidirectional"]:
                result["vault_to_project"] = await self.sync_vault_to_project()
                result["total"] += result["vault_to_project"]["count"]
                result["errors"].extend(result["vault_to_project"]["errors"])
            
            if direction in ["project_to_vault", "bidirectional"]:
                result["project_to_vault"] = await self.sync_project_to_vault()
                result["total"] += result["project_to_vault"]["count"]
                result["errors"].extend(result["project_to_vault"]["errors"])
            
            if direction in ["n8n", "bidirectional"]:
                result["n8n_sync"] = await self._sync_n8n()
                if result["n8n_sync"]:
                    result["total"] += result["n8n_sync"].get("count", 0)
                    result["errors"].extend(result["n8n_sync"].get("errors", []))
            
            # Сохраняем лог
            self._save_sync_log(result)
            
            return result
            
        except Exception as e:
            result["errors"].append(str(e))
            return result
    
    async def _sync_n8n(self) -> dict | None:
        """Синхронизация с n8n (если установлен)."""
        if not self.n8n_path.exists():
            return None
        
        # TODO: Реализовать синхронизацию workflows n8n
        # Пока просто возвращаем статус
        return {
            "status": "not_implemented",
            "message": "n8n интеграция будет добавлена позже",
            "count": 0,
        }
    
    def _log_sync(self, direction: str, file: str, status: str, error: str | None = None):
        """Логирование синхронизации."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "direction": direction,
            "file": file,
            "status": status,
            "error": error,
        }
        self.sync_log.append(entry)
    
    def _save_sync_log(self, result: dict):
        """Сохранить лог синхронизации (в проект, не в волт)."""
        log_file = self.project_path / "data" / "sync_log.json"
        log_data = {
            "last_sync": datetime.now().isoformat(),
            "result": result,
            "log": self.sync_log[-100:],  # Последние 100 записей
        }
        
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            log_file.write_text(json.dumps(log_data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"Ошибка сохранения лога: {e}")
    
    def add_callback(self, callback: Callable):
        """Добавить обработчик событий синхронизации."""
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        """Удалить обработчик событий."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)


# Глобальный экземпляр PI Дрона
_pi_dron_instance: PIDron | None = None


def get_pidron() -> PIDron:
    """Получить или создать глобальный экземпляр PI Дрона."""
    global _pi_dron_instance
    if _pi_dron_instance is None:
        _pi_dron_instance = PIDron()
    return _pi_dron_instance


async def main():
    """Тестовая функция для проверки работы PI Дрона."""
    pidron = get_pidron()
    
    print("=" * 60)
    print("PI ДРОН - СИСТЕМА СИНХРОНИЗАЦИИ ANANISIM OS")
    print("=" * 60)
    
    # Проверка статуса
    status = await pidron.status()
    print(f"\nСтатус системы:")
    print(f"  Status: {status['status']}")
    print(f"  Vault: {status['vault']}")
    print(f"  Project: {status['project']}")
    print(f"  N8N: {status['n8n']}")
    
    # Проверка компонентов
    print(f"\nКомпоненты:")
    for name, value in status['components'].items():
        print(f"  {name}: {'✅' if value else '❌'}")
    
    # Запуск синхронизации
    print("\nЗапуск синхронизации...")
    result = await pidron.sync_all(direction="bidirectional")
    
    print(f"\nРезультаты:")
    print(f"  Всего файлов синхронизировано: {result['total']}")
    print(f"  Ошибок: {len(result['errors'])}")
    
    if result['vault_to_project']:
        print(f"\nVault → Project:")
        print(f"  Успешно: {result['vault_to_project']['count']}")
        if result['vault_to_project']['errors']:
            print(f"  Ошибки: {result['vault_to_project']['errors'][:3]}")
    
    if result['project_to_vault']:
        print(f"\nProject → Vault:")
        print(f"  Успешно: {result['project_to_vault']['count']}")
        if result['project_to_vault']['errors']:
            print(f"  Ошибки: {result['project_to_vault']['errors'][:3]}")
    
    print("\n" + "=" * 60)
    print("PI Дрон готов к работе!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
