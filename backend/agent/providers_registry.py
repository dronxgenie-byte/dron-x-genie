"""Реестр провайдеров и моделей для ANANISIM OS.

Задачи модуля:
1. Хранить таблицу: провайдер / модели / подписка и лимиты / доступность в РФ / ключ.
2. Проверять живость провайдера (probe) — реальным запросом, а не на слово.
3. Обновлять каталог из сети (публичные JSON-каталоги моделей) и показывать,
   что появилось нового. Без LLM: только HTTP + JSON, поэтому бесплатно.

Данные-семена собраны по состоянию на 2026-11 и помечены `verify: true`,
пока провайдер ни разу не проверен реальным запросом. После probe флаг снимается.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path

import httpx

REGISTRY_VERSION = 1
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
REGISTRY_FILE = DATA_DIR / "providers_registry.json"

READY = "ready"
UNCONFIGURED = "unconfigured"
UNREACHABLE = "unreachable"

# Публичные каталоги моделей (JSON, без ключа). Используются для «парсинга сети».
PUBLIC_CATALOGS = {
    "openrouter": "https://openrouter.ai/api/v1/models",
    "huggingface": "https://huggingface.co/api/models?pipeline_tag=text-generation&sort=trendingScore&limit=20",
}

SEED: dict = {
    "version": REGISTRY_VERSION,
    "updated_at": None,
    "note": "Подписки и лимиты меняются. Столбец verify=true — данные не проверены реальным запросом.",
    "providers": [
        {
            "id": "lm-studio",
            "name": "LM Studio (локально)",
            "kind": "local",
            "base_url": "http://127.0.0.1:1234/v1",
            "key_env": None,
            "models": ["google/gemma-4-e4b", "qwen3.5:4b"],
            "plan": "бесплатно, без лимитов",
            "price": "0 ₽",
            "tokens": "ограничено только железом",
            "ru_access": "работает всегда",
            "free_tier": True,
            "connected": True,
            "priority": 1,
            "verify": False,
            "note": "Спит, когда ноутбук выключен. Основа для Дрона.",
        },
        {
            "id": "timeweb-genie",
            "name": "Timeweb → DeepSeek",
            "kind": "gateway",
            "base_url": "https://agent.timeweb.cloud/api/v1/cloud-ai/agents/07d69a8c-53e9-458a-a61e-2563b99394ee/v1",
            "key_env": "TIMEWEB_GENIE_API_KEY",
            "models": ["DeepSeek V4 Flash"],
            "plan": "оплата по факту (рубли, карта РФ)",
            "price": "≈ копейки за запрос",
            "tokens": "оплата за токены, лимитов подписки нет",
            "ru_access": "работает, оплата картой РФ",
            "free_tier": False,
            "connected": True,
            "priority": 2,
            "verify": True,
            "note": "То, на чём сейчас работает X через harness. Дешевле официального DeepSeek.",
        },
        {
            "id": "groq",
            "name": "Groq",
            "kind": "remote",
            "base_url": "https://api.groq.com/openai/v1",
            "key_env": "GROQ_API_KEY",
            "models": [
                "llama-3.3-70b-versatile",
                "llama-3.1-8b-instant",
                "qwen/qwen3-32b",
                "moonshotai/kimi-k2-instruct",
            ],
            "plan": "бесплатный tier с лимитами запросов",
            "price": "0 ₽ в рамках лимита",
            "tokens": "ограничение по RPM/TPM и суткам, а не по кошельку",
            "ru_access": "нужен аккаунт; доступность из РФ проверить",
            "free_tier": True,
            "connected": False,
            "priority": 3,
            "verify": True,
            "note": "Самый быстрый бесплатный вариант. DeepSeek у Groq нет — Llama/Qwen/Kimi.",
        },
        {
            "id": "github-models",
            "name": "GitHub Models",
            "kind": "remote",
            "base_url": "https://models.github.ai/inference",
            "key_env": "GITHUB_MODELS_TOKEN",
            "models": ["deepseek/DeepSeek-R1", "deepseek/DeepSeek-V3-0324", "openai/gpt-4o-mini"],
            "plan": "бесплатная квота на день",
            "price": "0 ₽ в рамках квоты",
            "tokens": "лимит запросов/токенов в сутки, зависит от аккаунта",
            "ru_access": "нужен GitHub-аккаунт и PAT",
            "free_tier": True,
            "connected": False,
            "priority": 4,
            "verify": True,
            "note": "Единственный бесплатный путь именно к DeepSeek. Ключ — personal access token.",
        },
        {
            "id": "openrouter",
            "name": "OpenRouter",
            "kind": "remote",
            "base_url": "https://openrouter.ai/api/v1",
            "key_env": "OPENROUTER_API_KEY",
            "models": ["deepseek/deepseek-chat-v3.1:free", "qwen/qwen3-235b-a22b:free"],
            "plan": "есть модели :free с лимитами",
            "price": "0 ₽ для :free",
            "tokens": "жёсткие лимиты бесплатных моделей",
            "ru_access": "сайт блокирован в РФ, нужен VPN/прокси",
            "free_tier": True,
            "connected": False,
            "priority": 6,
            "verify": True,
            "note": "Бесплатные модели есть, но из РФ — только через прокси.",
        },
        {
            "id": "vsegpt",
            "name": "VseGPT",
            "kind": "remote",
            "base_url": "https://api.vsegpt.ru/v1",
            "key_env": "VSEGPT_API_KEY",
            "models": ["deepseek/deepseek-chat", "openai/gpt-4o-mini"],
            "plan": "оплата по факту, рублями",
            "price": "от копеек за запрос",
            "tokens": "оплата за токены",
            "ru_access": "работает, карта РФ, без VPN",
            "free_tier": False,
            "connected": False,
            "priority": 5,
            "verify": True,
            "note": "Российский агрегатор: DeepSeek и другие через один ключ.",
        },
        {
            "id": "proxyapi",
            "name": "ProxyAPI",
            "kind": "remote",
            "base_url": "https://api.proxyapi.ru/openai/v1",
            "key_env": "PROXYAPI_API_KEY",
            "models": ["gpt-4o-mini", "deepseek-chat"],
            "plan": "оплата по факту, рублями",
            "price": "от копеек за запрос",
            "tokens": "оплата за токены",
            "ru_access": "работает, карта РФ, без VPN",
            "free_tier": False,
            "connected": False,
            "priority": 6,
            "verify": True,
            "note": "Резерв к VseGPT, если у одного кончился баланс.",
        },
    ],
}


def _env(name: str | None) -> str:
    return (os.getenv(name) or "").strip() if name else ""


def load_registry() -> dict:
    """Прочитать реестр с диска, при отсутствии — создать из семян."""
    if REGISTRY_FILE.is_file():
        try:
            data = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("providers"):
                return data
        except (OSError, json.JSONDecodeError):
            pass
    data = json.loads(json.dumps(SEED))
    save_registry(data)
    return data


def save_registry(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data["version"] = REGISTRY_VERSION
    REGISTRY_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _provider(data: dict, provider_id: str) -> dict | None:
    for item in data.get("providers", []):
        if item.get("id") == provider_id:
            return item
    return None


async def probe(provider: dict, client: httpx.AsyncClient) -> dict:
    """Проверить провайдера реальным запросом к /models или корню."""
    base = (provider.get("base_url") or "").rstrip("/")
    key = _env(provider.get("key_env"))
    started = time.perf_counter()
    result = {"id": provider.get("id"), "status": UNCONFIGURED, "latency_ms": None, "models_seen": []}

    if not base:
        result["status"] = UNREACHABLE
        return result
    if provider.get("kind") != "local" and not key:
        result["status"] = UNCONFIGURED
        return result

    headers = {"Authorization": f"Bearer {key}"} if key else {}
    try:
        response = await client.get(f"{base}/models", headers=headers, timeout=12.0)
    except Exception as exc:  # noqa: BLE001
        result["status"] = UNREACHABLE
        result["error"] = str(exc)[:180]
        return result

    result["latency_ms"] = int((time.perf_counter() - started) * 1000)
    if response.status_code == 200:
        result["status"] = READY
        try:
            payload = response.json()
            seen = [item.get("id") for item in payload.get("data", []) if item.get("id")]
            result["models_seen"] = seen[:40]
        except ValueError:
            pass
    elif response.status_code in (401, 403):
        result["status"] = UNCONFIGURED
        result["error"] = "ключ не принят"
    else:
        result["status"] = UNREACHABLE
        result["error"] = f"HTTP {response.status_code}"
    return result


async def _fetch_public_catalogs(client: httpx.AsyncClient) -> dict:
    """Спарсить публичные каталоги моделей: что нового в мире."""
    found: dict[str, list[str]] = {}
    for name, url in PUBLIC_CATALOGS.items():
        try:
            response = await client.get(url, timeout=15.0)
            if response.status_code != 200:
                continue
            payload = response.json()
            if name == "openrouter":
                items = payload.get("data", [])
                free = [
                    item.get("id")
                    for item in items
                    if isinstance(item, dict) and item.get("id") and _is_free(item)
                ]
                found[name] = free[:30]
            elif name == "huggingface":
                items = payload if isinstance(payload, list) else payload.get("data", [])
                found[name] = [
                    item.get("modelId") or item.get("id")
                    for item in items
                    if isinstance(item, dict) and (item.get("modelId") or item.get("id"))
                ][:20]
        except Exception:  # noqa: BLE001 — сеть может быть закрыта, это не ошибка борта
            continue
    return found


def _is_free(item: dict) -> bool:
    pricing = item.get("pricing") or {}
    try:
        return float(pricing.get("prompt", "1")) == 0.0 and float(pricing.get("completion", "1")) == 0.0
    except (TypeError, ValueError):
        return False


async def refresh() -> dict:
    """Полный цикл: проверить всех + спарсить публичные каталоги + сохранить diff."""
    data = load_registry()
    changes: list[str] = []

    async with httpx.AsyncClient(follow_redirects=True) as client:
        probes = await asyncio.gather(
            *(probe(provider, client) for provider in data.get("providers", []))
        )
        catalogs = await _fetch_public_catalogs(client)

    for result in probes:
        provider = _provider(data, result["id"])
        if not provider:
            continue
        provider["status"] = result["status"]
        provider["latency_ms"] = result["latency_ms"]
        provider["checked_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        if result["status"] == READY:
            provider["verify"] = False
            provider["connected"] = True
            known = set(provider.get("models") or [])
            new_models = [m for m in result.get("models_seen", []) if m not in known]
            if new_models:
                provider["models"] = (provider.get("models") or []) + new_models[:10]
                changes.append(f"{provider['name']}: +{len(new_models[:10])} моделей")
        elif result.get("error"):
            provider["last_error"] = result["error"]

    # Публичные каталоги не привязаны к нашему ключу: складываем как «слухи рынка».
    data["market"] = {
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "free_models": catalogs.get("openrouter", []),
        "trending_models": catalogs.get("huggingface", []),
    }
    if catalogs.get("openrouter"):
        changes.append(f"OpenRouter: {len(catalogs['openrouter'])} бесплатных моделей")
    if catalogs.get("huggingface"):
        changes.append(f"HuggingFace: {len(catalogs['huggingface'])} трендовых моделей")

    data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save_registry(data)

    ready = [p["id"] for p in data["providers"] if p.get("status") == READY]
    return {
        "ok": True,
        "ready": ready,
        "changes": changes,
        "providers": _public_view(data),
        "market": data.get("market"),
    }


def _public_view(data: dict) -> list[dict]:
    """Только безопасные поля — без имён переменных с ключами."""
    fields = (
        "id", "name", "kind", "models", "plan", "price", "tokens", "ru_access",
        "free_tier", "connected", "priority", "verify", "status", "latency_ms",
        "checked_at", "last_error", "note",
    )
    view = []
    for provider in data.get("providers", []):
        item = {field: provider.get(field) for field in fields}
        item["key_configured"] = bool(_env(provider.get("key_env"))) if provider.get("key_env") else True
        view.append(item)
    view.sort(key=lambda item: (item.get("priority") or 99, item.get("name") or ""))
    return view


def registry_view() -> dict:
    data = load_registry()
    return {
        "updated_at": data.get("updated_at"),
        "note": data.get("note"),
        "providers": _public_view(data),
        "market": data.get("market"),
    }


def set_active(provider_id: str) -> dict:
    """Отметить выбранного провайдера активным для X."""
    data = load_registry()
    provider = _provider(data, provider_id)
    if not provider:
        return {"ok": False, "error": f"нет провайдера {provider_id}"}
    data["active"] = provider_id
    save_registry(data)
    return {"ok": True, "active": provider_id}
