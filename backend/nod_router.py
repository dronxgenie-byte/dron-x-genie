"""
NOD Router — авто-переключение между провайдерами и ключами с умным роутингом.

При получении задачи от Агента X роутер:
1. Фильтрует провайдеров по приоритету стоимости (1=AMD, 2=free-tier, 3=paid)
2. Проверяет здоровье ключа (success_count > fail_count или нет проверок)
3. Проверяет лимиты AMD (rps_used < rps_limit и remaining_tokens > 0)
4. Если AMD исчерпан — переходит к приоритету 2, затем к 3
5. Если ни один провайдер не доступен — возвращает понятную ошибку

Интегрируется с файловым мостом NOD (nod_bridge/task.json / result.json).
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx

from .nod_monitor import check_provider_key, record_amd_usage
from .nod_providers import (
    get_latest_amd_billing,
    get_provider,
    get_models_by_priority,
    list_keys,
    list_models,
    list_providers,
    record_amd_billing,
)
from .nod_vault import get_key

logger = logging.getLogger("nod.router")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
NOD_BRIDGE_DIR = PROJECT_ROOT / "nod_bridge"
TASK_FILE = NOD_BRIDGE_DIR / "task.json"
RESULT_FILE = NOD_BRIDGE_DIR / "result.json"

AMD_RPS_LIMIT = 20
AMD_RPS_WARNING_THRESHOLD = 15  # 80% от лимита

# Приоритеты стоимости
PRIORITY_AMD_FREE = 1      # Бесплатные баллы AMD
PRIORITY_FREE_TIER = 2     # Бесплатные tier провайдеры
PRIORITY_PAID = 3          # Платные API

PRIORITY_LABELS = {
    PRIORITY_AMD_FREE: "AMD бесплатные баллы",
    PRIORITY_FREE_TIER: "Бесплатный tier",
    PRIORITY_PAID: "Платные API",
}


class NODRouter:
    """Роутер запросов к провайдерам с умным роутингом по стоимости."""

    def __init__(self) -> None:
        NOD_BRIDGE_DIR.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------
    # Выбор провайдера с учётом приоритетов и лимитов
    # ---------------------------------------------------------------

    def select_best_provider(
        self,
        *,
        model_preference: str | None = None,
        require_free: bool = False,
        require_priority: int | None = None,
    ) -> dict[str, Any] | None:
        """Выбрать провайдера с рабочим ключом, учитывая cost_priority.

        Логика выбора:
        1. Определяем целевой приоритет (по умолчанию 1 — AMD).
        2. Ищем модели с этим приоритетом.
        3. Проверяем здоровье ключей провайдеров.
        4. Для AMD (приоритет 1) проверяем лимиты RPS и остаток токенов.
        5. Если лимиты AMD исчерпаны — переходим к приоритету 2, затем 3.
        6. Возвращаем лучшего провайдера с наибольшим success_count.
        """
        # Определяем целевой приоритет
        if require_priority is not None:
            target_priority = require_priority
        elif require_free:
            target_priority = PRIORITY_AMD_FREE
        else:
            target_priority = PRIORITY_AMD_FREE

        # Пробуем приоритеты по порядку: целевой → 2 → 3
        for priority in (target_priority, PRIORITY_FREE_TIER, PRIORITY_PAID):
            if priority < target_priority:
                continue  # Не опускаемся ниже целевого, если он явно задан

            result = self._try_select_at_priority(priority, model_preference)
            if result is not None:
                return result

        return None

    def _try_select_at_priority(
        self,
        priority: int,
        model_preference: str | None = None,
    ) -> dict[str, Any] | None:
        """Попробовать выбрать провайдера с заданным приоритетом."""
        # Получаем модели с этим приоритетом
        priority_models = get_models_by_priority(priority)
        if not priority_models:
            return None

        # Если AMD (приоритет 1) — проверяем лимиты перед выбором
        if priority == PRIORITY_AMD_FREE:
            billing = get_latest_amd_billing()
            if billing:
                rps_used = billing.get("rps_used") or 0
                rps_limit = billing.get("rps_limit") or AMD_RPS_LIMIT
                remaining_tokens = billing.get("remaining_tokens")

                if rps_used >= rps_limit:
                    logger.warning(
                        f"AMD RPS лимит исчерпан: {rps_used}/{rps_limit}, "
                        f"переходим к приоритету 2"
                    )
                    return None
                if remaining_tokens is not None and remaining_tokens <= 0:
                    logger.warning(
                        f"AMD токены исчерпаны: {remaining_tokens}, "
                        f"переходим к приоритету 2"
                    )
                    return None

        # Собираем уникальные провайдеры с этими моделями
        candidate_providers = {}
        for m in priority_models:
            pname = m["provider_name"]
            if pname not in candidate_providers:
                candidate_providers[pname] = m

        # Проверяем ключи для каждого кандидата
        all_keys = list_keys()
        best_provider = None
        best_key = None
        best_score = -1

        for pname, model in candidate_providers.items():
            keys = [k for k in all_keys if k["provider_name"] == pname]
            if not keys:
                continue

            # Берем лучший ключ для этого провайдера
            best_k = max(keys, key=lambda k: (k.get("success_count", 0), -k.get("fail_count", 0)))

            # Проверяем здоровье ключа (должен быть success_count > fail_count или нет проверок)
            sc = best_k.get("success_count", 0)
            fc = best_k.get("fail_count", 0)
            cc = best_k.get("check_count", 0)
            if cc > 0 and sc <= fc:
                continue  # Ключ не健康

            score = sc
            if score > best_score:
                best_score = score
                best_provider = model
                best_key = best_k

        if best_provider is None:
            return None

        return {
            "provider_name": best_provider["provider_name"],
            "model_id": best_provider["model_id"],
            "cost_priority": best_provider.get("cost_priority", 2),
            "key_id": best_key["id"],
            "key_name": best_key["key_name"],
        }

    # ---------------------------------------------------------------
    # Выполнение запроса с полной логикой роутинга
    # ---------------------------------------------------------------

    async def route_request(
        self,
        query: str,
        *,
        model_preference: str | None = None,
        require_free: bool = False,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Маршрутизировать запрос к самому подходящему живому провайдеру.

        Логика:
        1. Выбираем провайдера через select_best_provider()
        2. Если AMD — проверяем лимиты ещё раз перед отправкой
        3. Отправляем запрос
        4. Записываем AMD биллинг после успешного запроса
        5. При ошибке — пробуем следующий провайдера с более низким приоритетом
        """
        # Пробуем приоритеты по порядку
        for priority in (PRIORITY_AMD_FREE, PRIORITY_FREE_TIER, PRIORITY_PAID):
            selected = self.select_best_provider(
                model_preference=model_preference,
                require_free=require_free,
                require_priority=priority,
            )

            if not selected:
                continue

            provider_name = selected["provider_name"]
            provider = get_provider(provider_name)
            if not provider:
                logger.warning(f"Провайдер '{provider_name}' не найден в БД")
                continue

            # Получаем ключ из vault
            decrypted_key = get_key(f"{provider_name}:{selected['key_id']}")
            if not decrypted_key:
                logger.warning(f"Ключ '{selected['key_name']}' не найден в vault")
                continue

            # Формируем запрос к провайдеру
            base_url = provider["base_url"].rstrip("/")
            url = f"{base_url}/chat/completions"
            header_name = provider.get("auth_header_name", "Authorization")
            header_prefix = provider.get("auth_header_prefix", "Bearer")
            headers = {
                "Content-Type": "application/json",
                header_name: f"{header_prefix} {decrypted_key}",
            }
            body = {
                "model": model_preference or selected["model_id"] or "default",
                "messages": [{"role": "user", "content": query}],
                "max_tokens": 1024,
                "temperature": 0.7,
            }

            try:
                start = time.perf_counter()
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(url, headers=headers, json=body)
                elapsed_ms = int((time.perf_counter() - start) * 1000)

                if response.status_code == 200:
                    data = response.json()
                    content = ""
                    choices = data.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "")

                    # Записываем AMD биллинг после успешного запроса
                    if priority == PRIORITY_AMD_FREE:
                        self._record_amd_request(elapsed_ms)

                    return {
                        "status": "ok",
                        "provider": provider_name,
                        "provider_type": provider.get("provider_type"),
                        "model": model_preference or selected["model_id"],
                        "cost_priority": priority,
                        "response": content,
                        "response_time_ms": elapsed_ms,
                        "raw": data,
                    }
                else:
                    logger.warning(
                        f"Провайдер '{provider_name}' вернул HTTP {response.status_code}, "
                        f"пробуем следующий приоритет"
                    )
                    continue

            except httpx.TimeoutException:
                logger.warning(
                    f"Таймаут запроса к '{provider_name}', пробуем следующий приоритет"
                )
                continue
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    f"Ошибка запроса к '{provider_name}': {exc}, пробуем следующий"
                )
                continue

        # Все приоритеты исчерпаны
        return {
            "status": "error",
            "message": (
                "Нет доступных провайдеров. "
                "AMD лимиты исчерпаны, бесплатные tier недоступны, "
                "платные API не настроены."
            ),
            "suggestion": (
                "Добавьте провайдера и ключ через NOD-консоль, "
                "или пополните баллы AMD AI Developer Program."
            ),
        }

    # ---------------------------------------------------------------
    # AMD биллинг — запись после успешного запроса
    # ---------------------------------------------------------------

    def _record_amd_request(self, response_time_ms: int) -> None:
        """Записать состояние AMD биллинга после успешного запроса."""
        from .nod_monitor import get_amd_usage_snapshot

        snapshot = get_amd_usage_snapshot()
        record_amd_billing(
            remaining_tokens=snapshot.get("remaining_tokens"),
            rps_used=snapshot.get("rps_used"),
            rps_limit=snapshot.get("rps_limit", AMD_RPS_LIMIT),
            daily_limit=snapshot.get("daily_limit"),
            daily_used=snapshot.get("daily_used"),
            notes=f"Запрос через AMD, время ответа {response_time_ms} мс",
        )

        # Предупреждение приapproaching лимита
        rps_used = snapshot.get("rps_used", 0)
        if rps_used > AMD_RPS_WARNING_THRESHOLD:
            logger.warning(
                f"AMD RPS достиг {rps_used}/{AMD_RPS_LIMIT} "
                f"(порог предупреждения {AMD_RPS_WARNING_THRESHOLD})"
            )

    # ---------------------------------------------------------------
    # Файловый мост NOD
    # ---------------------------------------------------------------

    def handle_file_bridge(self) -> dict[str, Any]:
        """Обработать задачу из nod_bridge/task.json через файловый мост."""
        if not TASK_FILE.exists():
            return {"status": "skip"}

        try:
            task_data = json.loads(TASK_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            return {"status": "error", "message": f"Некорректный task.json: {exc}"}

        query = task_data.get("task", "")
        if not query:
            self._safe_unlink(TASK_FILE)
            return {"status": "error", "message": "Пустая задача"}

        # Запускаем асинхронную маршрутизацию
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.route_request(query))
        finally:
            loop.close()

        # Пишем результат
        RESULT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

        # Удаляем задачу
        self._safe_unlink(TASK_FILE)

        return result

    @staticmethod
    def _safe_unlink(path: Path) -> None:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass

    # ---------------------------------------------------------------
    # Информация о состоянии
    # ---------------------------------------------------------------

    def get_status(self) -> dict[str, Any]:
        """Статус системы провайдеров и ключей с приоритетами."""
        providers = list_providers()
        keys = list_keys()
        working = [k for k in keys if k.get("success_count", 0) > k.get("fail_count", 0)]
        models = list_models()

        # AMD статус
        billing = get_latest_amd_billing()
        amd_status = None
        if billing:
            amd_status = {
                "remaining_tokens": billing.get("remaining_tokens"),
                "rps_used": billing.get("rps_used"),
                "rps_limit": billing.get("rps_limit", AMD_RPS_LIMIT),
                "daily_limit": billing.get("daily_limit"),
                "daily_used": billing.get("daily_used"),
                "checked_at": billing.get("checked_at"),
            }

        # Модели по приоритетам
        models_by_priority = {}
        for p in (1, 2, 3):
            models_by_priority[p] = len(get_models_by_priority(p))

        return {
            "providers_count": len(providers),
            "providers": [
                {"name": p["name"], "type": p.get("provider_type"), "base_url": p.get("base_url")}
                for p in providers
            ],
            "keys_count": len(keys),
            "working_keys_count": len(working),
            "models_count": len(models),
            "models_by_priority": models_by_priority,
            "free_models_count": sum(1 for m in models if m.get("is_free")),
            "providers_list": [p["name"] for p in providers],
            "amd_billing": amd_status,
        }
