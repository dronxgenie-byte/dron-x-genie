"""
NOD Discovery — ночной поиск бесплатных LLM-провайдеров.

Модуль ищет в интернете información о новых бесплатных API для LLM,
записывает находки в базу данных (дисквери-лог) и предлагает их для
добавления в систему. Работает по расписанию (ночью) через cron/wakeup.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from .nod_providers import add_discovery, add_provider, add_model, list_providers

LOG_FILE = Path(__file__).resolve().parent / "data" / "discovery_queue.json"

# ---------------------------------------------------------------
# Источники поиска (статические списки bekannten бесплатных провайдеров)
# В будущем можно добавить реальный веб-скрейпинг через SearchTool NOD
# ---------------------------------------------------------------

KNOWN_FREE_PROVIDERS: list[dict[str, Any]] = [
    {
        "name": "amd",
        "display_name": "AMD AI Developer Program",
        "provider_type": "amd",
        "base_url": "https://api.amd.com/v1",
        "auth_type": "api_key",
        "auth_header_name": "Authorization",
        "auth_header_prefix": "Bearer",
        "docs_url": "https://developer.amd.com/ai",
        "free_tier_url": "https://developer.amd.com/ai",
        "notes": "AMD AI Developer Program — бесплатные баллы AMD для обхода блокировок нейросетей в РФ.",
        "models": [
            {"model_id": "deepseek-v4.1-flash-1017", "display_name": "DeepSeek V4.1 Flash 1017", "is_free": True, "cost_priority": 1, "context_window": 131072},
            {"model_id": "gemma-4-31b-it", "display_name": "Gemma 4 31B IT", "is_free": True, "cost_priority": 1, "context_window": 131072},
        ],
    },
    {
        "name": "coarena",
        "display_name": "Coarena",
        "provider_type": "aggregator",
        "base_url": "https://coarena.ai/api/v1",
        "auth_type": "api_key",
        "auth_header_name": "Authorization",
        "auth_header_prefix": "Bearer",
        "docs_url": "https://coarena.ai",
        "free_tier_url": "https://coarena.ai",
        "notes": "Бесплатный Level 0 API для обхода блокировок нейросетей в РФ.",
        "models": [
            {"model_id": "gpt-3.5-turbo", "display_name": "GPT-3.5 Turbo", "is_free": True, "context_window": 16384},
            {"model_id": "gpt-4", "display_name": "GPT-4", "is_free": True, "context_window": 8192},
            {"model_id": "claude-3-haiku", "display_name": "Claude 3 Haiku", "is_free": True, "context_window": 200000},
            {"model_id": "claude-3-sonnet", "display_name": "Claude 3 Sonnet", "is_free": True, "context_window": 200000},
            {"model_id": "llama-3.1-8b", "display_name": "Llama 3.1 8B", "is_free": True, "context_window": 131072},
            {"model_id": "llama-3.1-70b", "display_name": "Llama 3.1 70B", "is_free": True, "context_window": 131072},
            {"model_id": "nemotron-mini", "display_name": "Nemotron Mini", "is_free": True, "context_window": 4096},
        ],
    },
    {
        "name": "openrouter",
        "display_name": "OpenRouter",
        "provider_type": "aggregator",
        "base_url": "https://openrouter.ai/api/v1",
        "auth_type": "api_key",
        "auth_header_name": "Authorization",
        "auth_header_prefix": "Bearer",
        "docs_url": "https://openrouter.ai/docs",
        "free_tier_url": "https://openrouter.ai/keys",
        "notes": "Агрегатор моделей с бесплатными tier для многих моделей.",
        "models": [
            {"model_id": "meta-llama/llama-3.1-8b-instruct:free", "display_name": "Llama 3.1 8B (free)", "is_free": True, "context_window": 131072},
            {"model_id": "google/gemma-2-9b-it:free", "display_name": "Gemma 2 9B (free)", "is_free": True, "context_window": 8192},
            {"model_id": "microsoft/phi-3-mini-128k-instruct:free", "display_name": "Phi-3 Mini (free)", "is_free": True, "context_window": 131072},
        ],
    },
    {
        "name": "groq",
        "display_name": "Groq",
        "provider_type": "cloud",
        "base_url": "https://api.groq.com/openai/v1",
        "auth_type": "api_key",
        "auth_header_name": "Authorization",
        "auth_header_prefix": "Bearer",
        "docs_url": "https://console.groq.com/docs",
        "free_tier_url": "https://console.groq.com/keys",
        "notes": "Быстрый бесплатный tier с лимитами RPM.",
        "models": [
            {"model_id": "llama-3.1-8b-instant", "display_name": "Llama 3.1 8B Instant", "is_free": True, "context_window": 131072, "rate_limit_rpm": 30},
            {"model_id": "llama-3.3-70b-versatile", "display_name": "Llama 3.3 70B Versatile", "is_free": True, "context_window": 131072, "rate_limit_rpm": 30},
            {"model_id": "mixtral-8x7b-32768", "display_name": "Mixtral 8x7B", "is_free": True, "context_window": 32768, "rate_limit_rpm": 30},
        ],
    },
    {
        "name": "together",
        "display_name": "Together AI",
        "provider_type": "cloud",
        "base_url": "https://api.together.xyz/v1",
        "auth_type": "api_key",
        "auth_header_name": "Authorization",
        "auth_header_prefix": "Bearer",
        "docs_url": "https://docs.together.ai",
        "free_tier_url": "https://api.together.ai/signin",
        "notes": "Бесплатные кредиты при регистрации.",
        "models": [
            {"model_id": "meta-llama/Llama-3.1-8B-Instruct-Turbo", "display_name": "Llama 3.1 8B Turbo", "is_free": True, "context_window": 131072},
            {"model_id": "meta-llama/Llama-3.3-70B-Instruct-Turbo", "display_name": "Llama 3.3 70B Turbo", "is_free": True, "context_window": 131072},
        ],
    },
]


# ---------------------------------------------------------------
# Поиск и запись находок
# ---------------------------------------------------------------

def run_discovery() -> dict[str, Any]:
    """Выполнить ночной поиск бесплатных провайдеров и моделей.

    Возвращает отчёт о найденных провайдерах и новых записях.
    """
    existing = {p["name"] for p in list_providers()}
    added_providers: list[str] = []
    added_models: list[str] = []
    skipped: list[str] = []

    for prov in KNOWN_FREE_PROVIDERS:
        prov_name = prov["name"]
        if prov_name in existing:
            skipped.append(prov_name)
            continue

        # Добавляем провайдера
        prov_id = add_provider(
            name=prov["name"],
            provider_type=prov["provider_type"],
            base_url=prov["base_url"],
            display_name=prov.get("display_name"),
            auth_type=prov.get("auth_type", "api_key"),
            auth_header_name=prov.get("auth_header_name", "Authorization"),
            auth_header_prefix=prov.get("auth_header_prefix", "Bearer"),
            docs_url=prov.get("docs_url"),
            free_tier_url=prov.get("free_tier_url"),
            notes=prov.get("notes"),
        )
        add_discovery(
            prov["name"],
            source_url=prov.get("free_tier_url") or prov.get("docs_url"),
            notes=prov.get("notes"),
            added_to_db=True,
        )
        added_providers.append(prov["name"])

        # Добавляем модели
        for m in prov.get("models", []):
            try:
                add_model(
                    provider_name=prov["name"],
                    model_id=m["model_id"],
                    display_name=m.get("display_name"),
                    context_window=m.get("context_window"),
                    max_output_tokens=None,
                    price_per_1k_input=0.0,
                    price_per_1k_output=0.0,
                    is_free=m.get("is_free", False),
                    cost_priority=m.get("cost_priority", 2),
                    rate_limit_rpm=m.get("rate_limit_rpm", 0),
                    rate_limit_tpm=0,
                    notes=m.get("notes"),
                )
                added_models.append(f"{prov['name']}:{m['model_id']}")
            except Exception as exc:  # noqa: BLE001
                add_discovery(
                    prov["name"],
                    model_id=m.get("model_id"),
                    source_url=prov.get("free_tier_url"),
                    notes=f"Ошибка добавления модели: {exc}",
                    added_to_db=False,
                )

    report = {
        "status": "ok",
        "added_providers": added_providers,
        "added_models": added_models,
        "skipped_existing": skipped,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Сохраняем отчёт в очередь на утренний просмотр
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOG_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return report


def get_discovery_report() -> dict[str, Any] | None:
    """Получить последний отчёт ночного поиска (если есть)."""
    if not LOG_FILE.exists():
        return None
    try:
        return json.loads(LOG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def clear_discovery_report() -> None:
    """Удалить отчёт после просмотра."""
    if LOG_FILE.exists():
        LOG_FILE.unlink()
