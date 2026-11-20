"""X-Agent — агент ANANISIM OS, работающий через внешние провайдеры и харнесс.

Роли на борту:
- Дрон  — локальная модель (LM Studio), память и присмотр за системой;
- Джин  — лицо и голос (Yandex Realtime);
- X     — рабочий агент под разными провайдерами, в том числе DeepSeek Harness.

Провайдеры:
1. `harness` — запускает `dsh --profile headless "<задача>"` и забирает финальный
   ответ. Так X получает полноценный кодинг-агент (файлы, инструменты) с тем
   провайдером, который настроен в профиле харнесса.
2. `local` — LM Studio (бесплатно, без сети).
3. `openai` — любой OpenAI-совместимый эндпоинт (VseGPT, ProxyAPI, GitHub Models,
   Groq, OpenRouter через прокси): задаётся X_OPENAI_BASE_URL / X_OPENAI_API_KEY.
4. `openrouter`, `groq` — предустановленные адреса.

Секреты живут только в .env и никогда не уходят в браузер.
"""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import time
from dataclasses import dataclass, field

import httpx

READY = "ready"
UNAVAILABLE = "unavailable"
UNCONFIGURED = "unconfigured"

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
HARNESS_TASK_LIMIT = 6000

# Символы, которые ломают командную строку Windows.
_UNSAFE = str.maketrans({'"': " ", "&": " ", "|": " ", "<": " ", ">": " ", "^": " ", "%": " "})


@dataclass
class XConfig:
    """Конфигурация X-агента."""

    provider: str = "harness"
    model: str = "default"
    api_key: str = ""
    base_url: str = ""
    profile: str = "headless"
    temperature: float = 0.7
    max_tokens: int = 1200
    timeout: float = 300.0
    extra_params: dict = field(default_factory=dict)


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def default_config() -> XConfig:
    """Конфигурация по умолчанию из .env."""
    provider = _env("X_PROVIDER", "harness").lower()
    base = _env("X_OPENAI_BASE_URL")
    key = _env("X_OPENAI_API_KEY")
    model = _env("X_OPENAI_MODEL", "default")

    if provider == "local":
        base = base or _env("LM_STUDIO_URL", "http://127.0.0.1:1234/v1")
        model = _env("X_OPENAI_MODEL", _env("LM_STUDIO_MODEL", "google/gemma-4-e4b"))
        key = ""
    elif provider == "openrouter":
        base = base or "https://openrouter.ai/api/v1"
        key = key or _env("OPENROUTER_API_KEY")
        model = _env("X_OPENAI_MODEL", "deepseek/deepseek-chat-v3.1:free")
    elif provider == "groq":
        base = base or "https://api.groq.com/openai/v1"
        key = key or _env("GROQ_API_KEY")
        model = _env("X_OPENAI_MODEL", "llama-3.3-70b-versatile")

    return XConfig(
        provider=provider,
        model=model,
        api_key=key,
        base_url=base,
        profile=_env("X_HARNESS_PROFILE", "headless"),
        temperature=float(_env("X_TEMPERATURE", "0.7") or 0.7),
        max_tokens=int(_env("X_MAX_TOKENS", "1200") or 1200),
        timeout=float(_env("X_TIMEOUT", "300") or 300),
    )


def harness_binary() -> str | None:
    """Где лежит CLI харнесса (npm-шим `dsh`)."""
    explicit = _env("DSH_BIN")
    if explicit and os.path.isfile(explicit):
        return explicit
    found = shutil.which("dsh")
    if found:
        return found
    fallback = os.path.join(os.environ.get("APPDATA", ""), "npm", "dsh.cmd")
    return fallback if os.path.isfile(fallback) else None


def clean_output(text: str) -> str:
    """Убрать ANSI-последовательности и служебный мусор."""
    stripped = ANSI_RE.sub("", text or "").replace("\r\n", "\n").strip()
    return stripped


def _sanitize_task(text: str) -> str:
    return (text or "").translate(_UNSAFE).strip()[:HARNESS_TASK_LIMIT]


class XAgent:
    """X: внешние провайдеры и харнесс."""

    def __init__(self, config: XConfig | None = None):
        self.config = config or default_config()

    # ---------- статус ----------

    async def status(self) -> str:
        provider = (self.config.provider or "").lower()
        if provider == "harness":
            return READY if harness_binary() else UNCONFIGURED
        if provider == "local":
            try:
                async with httpx.AsyncClient(timeout=4.0) as client:
                    response = await client.get(f"{self.config.base_url}/models")
                return READY if response.status_code == 200 else UNAVAILABLE
            except Exception:
                return UNAVAILABLE
        if not self.config.base_url:
            return UNCONFIGURED
        return READY if self.config.api_key or provider in {"local"} else UNCONFIGURED

    def providers(self) -> list[dict]:
        """Список провайдеров без секретов."""
        dsh = harness_binary()
        local_url = _env("LM_STUDIO_URL", "http://127.0.0.1:1234/v1")
        openai_base = _env("X_OPENAI_BASE_URL")
        openai_key = bool(_env("X_OPENAI_API_KEY"))

        items = [
            {
                "id": "harness",
                "name": "DeepSeek Harness",
                "kind": "coding-agent",
                "detail": f"dsh --profile {self.config.profile}" if dsh else "dsh не найден в PATH",
                "ready": bool(dsh),
                "model": self.config.profile,
            },
            {
                "id": "local",
                "name": "Локальная модель",
                "kind": "local",
                "detail": local_url,
                "ready": True,
                "model": _env("LM_STUDIO_MODEL", "google/gemma-4-e4b"),
            },
            {
                "id": "openai",
                "name": "OpenAI-совместимый",
                "kind": "remote",
                "detail": openai_base or "задайте X_OPENAI_BASE_URL в .env",
                "ready": bool(openai_base and openai_key),
                "model": _env("X_OPENAI_MODEL", "default"),
            },
            {
                "id": "groq",
                "name": "Groq",
                "kind": "remote",
                "detail": "https://api.groq.com/openai/v1",
                "ready": bool(_env("GROQ_API_KEY")),
                "model": _env("X_OPENAI_MODEL", "llama-3.3-70b-versatile"),
            },
            {
                "id": "openrouter",
                "name": "OpenRouter (нужен VPN/прокси из РФ)",
                "kind": "remote",
                "detail": "https://openrouter.ai/api/v1",
                "ready": bool(_env("OPENROUTER_API_KEY")),
                "model": _env("X_OPENAI_MODEL", "deepseek/deepseek-chat-v3.1:free"),
            },
        ]
        return items

    # ---------- чат ----------

    async def chat(
        self,
        message: str,
        history: list[dict] | None = None,
        *,
        provider: str | None = None,
        model: str | None = None,
        context: str | None = None,
        timeout: float | None = None,
    ) -> dict:
        provider = (provider or self.config.provider or "harness").lower()
        model = model or self.config.model
        timeout = float(timeout or self.config.timeout)

        if provider == "harness":
            try:
                return await self._chat_harness(message, context, timeout)
            except RuntimeError as exc:
                fallback = _env("X_FALLBACK", "local").lower()
                if fallback in {"", "none", "off", "0"}:
                    raise
                return await self._chat_fallback(message, history, context, timeout, str(exc))
        if provider == "local":
            return await self._chat_openai_compatible(
                message, history, context,
                base_url=self.config.base_url or _env("LM_STUDIO_URL", "http://127.0.0.1:1234/v1"),
                api_key="",
                model=_env("LM_STUDIO_MODEL", "google/gemma-4-e4b"),
                timeout=timeout,
            )
        if provider == "openrouter":
            return await self._chat_openai_compatible(
                message, history, context,
                base_url=self.config.base_url or "https://openrouter.ai/api/v1",
                api_key=self.config.api_key or _env("OPENROUTER_API_KEY"),
                model=model,
                timeout=timeout,
            )
        if provider == "groq":
            return await self._chat_openai_compatible(
                message, history, context,
                base_url=self.config.base_url or "https://api.groq.com/openai/v1",
                api_key=self.config.api_key or _env("GROQ_API_KEY"),
                model=model,
                timeout=timeout,
            )
        if provider in {"openai", "vsegpt", "proxyapi", "github"}:
            return await self._chat_openai_compatible(
                message, history, context,
                base_url=self.config.base_url or _env("X_OPENAI_BASE_URL"),
                api_key=self.config.api_key or _env("X_OPENAI_API_KEY"),
                model=model,
                timeout=timeout,
            )
        raise ValueError(f"Неизвестный провайдер: {provider}")

    async def _chat_fallback(
        self,
        message: str,
        history: list[dict] | None,
        context: str | None,
        timeout: float,
        reason: str,
    ) -> dict:
        """Харнесс не смог (нет ключа/провайдер недоступен) — работаем локально.

        Сначала пробуем харнесс с локальным профилем (инструменты сохраняются),
        затем прямую локальную модель. Причина честно попадает в ответ.
        """
        local_profile = _env("X_FALLBACK_PROFILE", "headless-local")
        note = f"[откат: {reason.splitlines()[0][:160]}]"

        try:
            result = await self._chat_harness(
                message, context, timeout, profile=local_profile
            )
            result["reply"] = f"{result['reply']}\n\n{note}"
            result["fallback"] = True
            return result
        except RuntimeError:
            pass

        result = await self._chat_openai_compatible(
            message,
            history,
            context,
            base_url=_env("LM_STUDIO_URL", "http://127.0.0.1:1234/v1"),
            api_key="",
            model=_env("LM_STUDIO_MODEL", "google/gemma-4-e4b"),
            timeout=timeout,
        )
        result["reply"] = f"{result['reply']}\n\n{note}"
        result["fallback"] = True
        return result

    def _child_env(self) -> dict[str, str]:
        """Окружение для дочернего dsh: провайдерские ключи из .env ANANISIM."""
        env = dict(os.environ)
        env.setdefault("DRON_LOCAL_API_KEY", "lm-studio")
        key_env = _env("X_HARNESS_KEY_ENV", "TIMEWEB_GENIE_API_KEY")
        key_value = _env(key_env)
        if key_value:
            env[key_env] = key_value
        return env

    async def _chat_harness(
        self,
        message: str,
        context: str | None,
        timeout: float,
        profile: str | None = None,
    ) -> dict:
        """Запустить харнесс в headless-режиме и забрать финальный ответ."""
        binary = harness_binary()
        if not binary:
            raise RuntimeError(
                "CLI харнесса не найден. Установите DeepSeek Harness "
                "или задайте DSH_BIN в .env."
            )

        profile = profile or self.config.profile
        task = message if not context else f"Контекст от Дрона:\n{context}\n\nЗадача:\n{message}"
        task = _sanitize_task(task)
        if not task:
            raise ValueError("Пустая задача для харнесса.")

        started = time.perf_counter()
        process = await asyncio.create_subprocess_exec(
            "cmd.exe", "/c", binary, "--profile", profile, task,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self._child_env(),
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise RuntimeError(f"Харнесс не ответил за {int(timeout)} c.") from None

        out = clean_output(stdout.decode("utf-8", "replace"))
        err = clean_output(stderr.decode("utf-8", "replace"))
        elapsed = round(time.perf_counter() - started, 1)

        if process.returncode != 0 and not out:
            raise RuntimeError(f"Харнесс завершился с кодом {process.returncode}: {err[-500:]}")

        if not out:
            raise RuntimeError(f"Харнесс вернул пустой ответ. {err[-300:]}")

        return {
            "reply": out,
            "agent": "x",
            "provider": "harness",
            "model": f"dsh:{profile}",
            "duration_s": elapsed,
            "truncated": len(out) > 8000,
        }

    async def _chat_openai_compatible(
        self,
        message: str,
        history: list[dict] | None,
        context: str | None,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float,
    ) -> dict:
        if not base_url:
            raise RuntimeError("Не задан base_url провайдера (X_OPENAI_BASE_URL).")

        messages: list[dict] = []
        if context:
            messages.append({"role": "system", "content": f"Контекст от Дрона:\n{context}"})
        for item in (history or [])[-10:]:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = item.get("content") or ""
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": str(content)[:4000]})
        messages.append({"role": "user", "content": message})

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        body = {
            "model": model,
            "messages": messages,
            "stream": False,
            "max_tokens": max(64, int(self.config.max_tokens)),
            "temperature": float(self.config.temperature),
        }

        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/chat/completions", json=body, headers=headers
            )
        elapsed = round(time.perf_counter() - started, 1)

        if response.status_code != 200:
            raise RuntimeError(f"HTTP {response.status_code}: {response.text[:300]}")

        payload = response.json()
        choices = payload.get("choices") or []
        if not choices:
            raise RuntimeError("Провайдер вернул пустой ответ.")

        content = ((choices[0].get("message") or {}).get("content") or "").strip()
        if not content:
            raise RuntimeError("Провайдер вернул пустой текст.")

        usage = payload.get("usage") or {}
        return {
            "reply": content,
            "agent": "x",
            "provider": model and base_url,
            "model": payload.get("model") or model,
            "duration_s": elapsed,
            "usage": {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
            },
        }


_x_agent_instance: XAgent | None = None


def get_x_agent(config: XConfig | None = None) -> XAgent:
    """Получить (или пересоздать) X-агента."""
    global _x_agent_instance
    if _x_agent_instance is None:
        _x_agent_instance = XAgent(config or default_config())
    elif config is not None:
        _x_agent_instance.config = config
    return _x_agent_instance
