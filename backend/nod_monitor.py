"""
NOD Key Health Monitor — мониторинг работоспособности API ключей.

Периодически проверяет каждый сохранённый ключ, отправляя тестовый запрос
к соответствующему провайдеру. Записывает результат в БД и обновляет
статус ключа (работает / не работает / ошибка).

Также отслеживает использование бесплатных баллов AMD AI Developer Program:
- Запись состояния в amd_billing после каждого запроса
- Предупреждение в логах при rps_used > 15 (80% от лимита 20 RPS)

Используется роутером nod_router.py для автоматического переключения
на живые ключи.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from .nod_providers import (
    get_provider,
    list_keys,
    record_amd_billing,
    record_key_health,
)
from .nod_vault import get_key

# ---------------------------------------------------------------
# Константы AMD
# ---------------------------------------------------------------

AMD_RPS_LIMIT = 20
AMD_RPS_WARNING_THRESHOLD = 15  # 80% от лимита

# Внутреннее состояние AMD счётчика (в памяти, дублируется в БД)
_amd_state: dict[str, Any] = {
    "remaining_tokens": None,
    "rps_used": 0,
    "rps_limit": AMD_RPS_LIMIT,
    "daily_limit": None,
    "daily_used": 0,
    "last_updated": None,
}

logger = logging.getLogger("nod.monitor")

# ---------------------------------------------------------------
# Тестовый запрос
# ---------------------------------------------------------------

TEST_PROMPT = "Привет"


def _build_test_headers(
    provider: dict[str, Any],
    decrypted_key: str,
) -> dict[str, str]:
    """Построить заголовки для тестового запроса."""
    header_name = provider.get("auth_header_name", "Authorization")
    header_prefix = provider.get("auth_header_prefix", "Bearer")
    return {
        "Content-Type": "application/json",
        header_name: f"{header_prefix} {decrypted_key}",
    }


def _build_test_body(model_id: str | None) -> dict[str, Any]:
    return {
        "model": model_id or "default",
        "messages": [{"role": "user", "content": TEST_PROMPT}],
        "max_tokens": 5,
        "temperature": 0,
    }


async def check_provider_key(
    provider_name: str,
    *,
    model_id: str | None = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Проверить первый активный ключ провайдера. Вернуть результат с is_working."""
    provider = get_provider(provider_name)
    if not provider:
        return {
            "provider": provider_name,
            "is_working": False,
            "error": "Провайдер не найден в БД",
        }

    from .nod_providers import list_keys as _list_keys

    keys = _list_keys(provider_name)
    if not keys:
        return {
            "provider": provider_name,
            "is_working": False,
            "error": "Нет ключей в базе",
        }

    key_row = keys[0]
    decrypted_key = get_key(f"{provider_name}:{key_row['key_name']}")
    if not decrypted_key:
        return {
            "provider": provider_name,
            "key_id": key_row["id"],
            "is_working": False,
            "error": "Ключ не найден в vault",
        }

    base_url = provider["base_url"].rstrip("/")
    url = f"{base_url}/chat/completions"
    headers = _build_test_headers(provider, decrypted_key)
    body = _build_test_body(model_id)

    try:
        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, headers=headers, json=body)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        is_working = response.status_code == 200

        record_key_health(key_row["id"], is_working=is_working, response_time_ms=elapsed_ms)

        return {
            "provider": provider_name,
            "key_id": key_row["id"],
            "is_working": is_working,
            "response_time_ms": elapsed_ms,
            "status_code": response.status_code,
            "error": None if is_working else f"HTTP {response.status_code}",
        }

    except httpx.TimeoutException:
        record_key_health(key_row["id"], is_working=False, error_message="Timeout")
        return {
            "provider": provider_name,
            "key_id": key_row["id"],
            "is_working": False,
            "error": "Таймаут запроса",
        }
    except Exception as exc:  # noqa: BLE001
        record_key_health(key_row["id"], is_working=False, error_message=str(exc))
        return {
            "provider": provider_name,
            "key_id": key_row["id"],
            "is_working": False,
            "error": str(exc),
        }


# ---------------------------------------------------------------
# AMD мониторинг — отслеживание бесплатных баллов
# ---------------------------------------------------------------

def record_amd_usage(
    *,
    remaining_tokens: int | None = None,
    rps_used: int | None = None,
    daily_used: int | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Обновить состояние AMD использования в памяти и БД.

    Вызывается после каждого успешного запроса к AMD провайдеру.
    """
    global _amd_state

    # Обновляем внутреннее состояние
    if remaining_tokens is not None:
        _amd_state["remaining_tokens"] = remaining_tokens
    if rps_used is not None:
        _amd_state["rps_used"] = rps_used
    else:
        _amd_state["rps_used"] = _amd_state.get("rps_used", 0) + 1
    if daily_used is not None:
        _amd_state["daily_used"] = daily_used
    else:
        _amd_state["daily_used"] = _amd_state.get("daily_used", 0) + 1
    _amd_state["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")

    # Записываем в БД
    record_amd_billing(
        remaining_tokens=_amd_state["remaining_tokens"],
        rps_used=_amd_state["rps_used"],
        rps_limit=_amd_state["rps_limit"],
        daily_limit=_amd_state["daily_limit"],
        daily_used=_amd_state["daily_used"],
        notes=notes,
    )

    # Предупреждение приapproaching лимита
    rps_used_val = _amd_state["rps_used"]
    if rps_used_val > AMD_RPS_WARNING_THRESHOLD:
        logger.warning(
            f"AMD RPS достиг {rps_used_val}/{AMD_RPS_LIMIT} "
            f"(порог предупреждения {AMD_RPS_WARNING_THRESHOLD})"
        )

    return get_amd_usage_snapshot()


def get_amd_usage_snapshot() -> dict[str, Any]:
    """Получить текущий снимок состояния AMD использования."""
    return dict(_amd_state)


def get_amd_status() -> dict[str, Any]:
    """Получить полный статус AMD с последней записью из БД."""
    from .nod_providers import get_latest_amd_billing

    snapshot = get_amd_usage_snapshot()
    latest_db = get_latest_amd_billing()

    return {
        "current": snapshot,
        "last_db_record": latest_db,
        "rps_limit": AMD_RPS_LIMIT,
        "warning_threshold": AMD_RPS_WARNING_THRESHOLD,
        "is_near_limit": snapshot.get("rps_used", 0) > AMD_RPS_WARNING_THRESHOLD,
        "is_limit_reached": snapshot.get("rps_used", 0) >= AMD_RPS_LIMIT,
    }


# ---------------------------------------------------------------
# Все ключи
# ---------------------------------------------------------------

async def check_all_keys() -> dict[str, Any]:
    """Проверить все ключи всех провайдеров. Вернуть сводный отчёт."""
    results: list[dict[str, Any]] = []
    working_count = 0
    total_count = 0

    keys = list_keys()
    for key_row in keys:
        provider_name = key_row["provider_name"]
        result = await check_provider_key(provider_name)
        results.append(result)
        total_count += 1
        if result.get("is_working"):
            working_count += 1

    return {
        "status": "ok",
        "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_keys": total_count,
        "working_keys": working_count,
        "failed_keys": total_count - working_count,
        "results": results,
    }


def get_health_summary() -> dict[str, Any]:
    """Быстрая сводка без сетевых запросов (из последних записей в БД)."""
    keys = list_keys()
    total = len(keys)
    working = 0
    failed = 0
    unknown = 0

    for k in keys:
        sc = k.get("success_count", 0)
        fc = k.get("fail_count", 0)
        if sc > 0 and fc == 0:
            working += 1
        elif fc > 0 and sc == 0:
            failed += 1
        else:
            unknown += 1

    return {
        "total_keys": total,
        "working": working,
        "failed": failed,
        "unknown": unknown,
    }
