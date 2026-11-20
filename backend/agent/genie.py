"""GENIE — голосовой семейный агент на Yandex AI Studio Realtime.

Отличия от Дрона:
- Дрон думает локально (LM Studio), GENIE живёт в облаке Yandex.
- GENIE — мультимодальный: слушает (ASR), говорит (TTS) и отвечает текстом
  в рамках одной WebSocket-сессии.
- Личность GENIE задана промптом в AI Studio (YANDEX_PROMPT_ID), поэтому
  здесь нет второго системного промпта: дублировать характер вредно.

Протокол проверен на живой сессии 2026-10-31:
- wss://ai.api.cloud.yandex.net/v1/realtime?model=gpt://{folder}/{model}
- session.update с prompt.id применяется (session.updated содержит instructions)
- conversation.item.create с input_text работает (текстовый чат без микрофона)
- ответ приходит дельтами response.output_text.delta и response.output_audio.delta
- audio/pcm, 44100 Гц, 16 бит, моно — и на вход, и на выход
- у промпта есть tool web_search: на function_call обязательно отвечать,
  иначе ход навсегда остаётся в статусе in_progress.
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import wave
from dataclasses import dataclass, field

import aiohttp

from .config import Cloud

DEFAULT_WSS = "wss://ai.api.cloud.yandex.net/v1/realtime"
DEFAULT_MODEL = "speech-realtime-max-tts-live/latest"
DEFAULT_SERVICE = "ANANISIM OS"

AUDIO_RATE = 44100
AUDIO_CHANNELS = 1
AUDIO_WIDTH = 2  # 16 бит

MAX_HISTORY = 8
MAX_MESSAGE = 4000

READY = "ready"
UNAVAILABLE = "unavailable"
UNCONFIGURED = "unconfigured"


class GenieError(RuntimeError):
    """Ошибка облачного агента."""


@dataclass
class GenieReply:
    reply: str
    agent: str = "genie"
    model: str = ""
    session_id: str | None = None
    audio_wav: bytes | None = None
    usage: dict = field(default_factory=dict)


def status(cloud: Cloud) -> str:
    """Дешёвый статус без сети: настроен ли агент."""
    if not cloud.configured:
        return UNCONFIGURED
    if not (cloud.prompt_id or cloud.text_model):
        return UNCONFIGURED
    return READY


def wss_url(cloud: Cloud) -> str:
    base = (cloud.realtime_wss or DEFAULT_WSS).strip()
    model = (cloud.realtime_model or DEFAULT_MODEL).strip()
    return f"{base}?model=gpt://{cloud.folder_id}/{model}"


def headers(cloud: Cloud) -> dict:
    return {"Authorization": f"Api-Key {cloud.api_key}"}


def _session_payload(cloud: Cloud, instructions: str | None) -> dict:
    session: dict = {}
    if cloud.prompt_id:
        session["prompt"] = {
            "id": cloud.prompt_id,
            "variables": {"service_name": cloud.service_name or DEFAULT_SERVICE},
        }
    if instructions:
        session["instructions"] = instructions
    return {"type": "session.update", "session": session}


def pcm_to_wav(pcm: bytes) -> bytes:
    """Собрать WAV из сырого PCM16 моно 44.1 кГц."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as out:
        out.setnchannels(AUDIO_CHANNELS)
        out.setsampwidth(AUDIO_WIDTH)
        out.setframerate(AUDIO_RATE)
        out.writeframes(pcm)
    return buffer.getvalue()


def _function_output(item: dict, answer: str | None = None) -> dict:
    """Ответ на вызов инструмента.

    Если обработчик дал ответ (например, Дрон подсказал факт) — возвращаем его.
    Иначе честно сообщаем, что инструмент выключен.
    """
    name = item.get("name") or "tool"

    if answer:
        payload = {"ok": True, "agent": "dron", "answer": answer[:2000]}
    else:
        payload = {
            "ok": False,
            "error": "tool_unavailable",
            "message": (
                f"Инструмент {name} недоступен в этой сборке. "
                "Скажи пользователю честно, что поиск сейчас выключен."
            ),
        }

    return {
        "type": "conversation.item.create",
        "item": {
            "type": "function_call_output",
            "call_id": item.get("call_id"),
            "output": json.dumps(payload, ensure_ascii=False),
        },
    }


def _message_item(role: str, text: str) -> dict:
    """Элемент сообщения в формате Realtime API.

    ВАЖНО: у message-элемента поле называется `content` (массив частей).
    Поле `text` Яндекс не читает — content остаётся null и сессия отвечает
    ошибкой «Invalid client event: null».
    """
    part_type = "input_text" if role == "user" else "text"
    return {
        "type": "conversation.item.create",
        "item": {
            "type": "message",
            "role": role,
            "content": [{"type": part_type, "text": text[:MAX_MESSAGE]}],
        },
    }


def _history_items(history: list[dict] | None) -> list[dict]:
    """История как элементы разговора Realtime API."""
    items: list[dict] = []
    for turn in (history or [])[-MAX_HISTORY:]:
        if not isinstance(turn, dict):
            continue
        role = turn.get("role")
        content = (turn.get("content") or "").strip()
        if not content or role not in {"user", "assistant"}:
            continue
        items.append(_message_item(role, content))
    return items


async def chat(
    cloud: Cloud,
    message: str,
    history: list[dict] | None = None,
    *,
    instructions: str | None = None,
    with_audio: bool = False,
    timeout: float = 60.0,
    memory: str | None = None,
    tool_handler=None,
) -> GenieReply:
    """Один ход разговора с GENIE по тексту."""
    text = (message or "").strip()
    if not text:
        raise ValueError("Пустое сообщение.")
    if len(text) > MAX_MESSAGE:
        raise ValueError("Сообщение слишком длинное.")
    if not cloud.configured:
        raise GenieError("Облачный Джинн не настроен: нет ключа или folder_id.")

    parts: list[str] = []
    audio = bytearray()
    session_id: str | None = None
    usage: dict = {}
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout

    async with aiohttp.ClientSession() as session:
        try:
            async with session.ws_connect(
                wss_url(cloud), headers=headers(cloud), heartbeat=20.0, timeout=timeout
            ) as ws:
                # Отправляем сессию
                await ws.send_json(_session_payload(cloud, instructions))
                
                # Собираем все сообщения в один batch
                messages: list[dict] = []

                # Память семьи — служебный контекст, не вопрос.
                if memory:
                    messages.append(
                        _message_item(
                            "user",
                            "[КОНТЕКСТ ПАМЯТИ, не вопрос и не требует ответа]\n" + memory[:6000],
                        )
                    )

                # История
                messages.extend(_history_items(history))

                # Текущее сообщение
                messages.append(_message_item("user", text))

                # Отправляем все сообщения сразу
                for msg in messages:
                    await ws.send_json(msg)

                # Запрашиваем ответ
                await ws.send_json({"type": "response.create"})

                while True:
                    remaining = deadline - loop.time()
                    if remaining <= 0:
                        raise GenieError("Джинн не ответил вовремя.")
                    try:
                        msg = await ws.receive(timeout=remaining)
                    except asyncio.TimeoutError:
                        raise GenieError("Джинн не ответил вовремя.") from None

                    if msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED):
                        raise GenieError("Соединение с Джинном закрыто.")
                    if msg.type == aiohttp.WSMsgType.ERROR:
                        raise GenieError(f"Сбой соединения: {ws.exception()}")
                    if msg.type != aiohttp.WSMsgType.TEXT:
                        continue

                    event = json.loads(msg.data)
                    kind = event.get("type")

                    if kind == "session.created":
                        session_id = (event.get("session") or {}).get("id")
                    elif kind == "response.output_text.delta":
                        parts.append(event.get("delta") or "")
                    elif kind == "response.output_audio.delta":
                        delta = event.get("delta")
                        if delta:
                            audio.extend(base64.b64decode(delta))
                    elif kind == "response.output_item.done":
                        item = event.get("item") or {}
                        if item.get("type") == "function_call":
                            answer = None
                            if tool_handler is not None:
                                try:
                                    answer = await tool_handler(item)
                                except Exception:
                                    answer = None
                            await ws.send_json(_function_output(item, answer))
                            await ws.send_json({"type": "response.create"})
                    elif kind == "response.done":
                        usage = (event.get("response") or {}).get("usage") or {}
                        break
                    elif kind == "error":
                        detail = (event.get("error") or {}).get("message") or json.dumps(
                            event.get("error"), ensure_ascii=False
                        )
                        raise GenieError(f"Yandex вернула ошибку: {detail}")
        except aiohttp.ClientError as exc:
            raise GenieError(f"Сеть недоступна: {exc}") from exc

    reply = "".join(parts).strip()
    if not reply:
        raise GenieError("Джинн вернул пустой ответ.")

    return GenieReply(
        reply=reply,
        model=cloud.realtime_model or DEFAULT_MODEL,
        session_id=session_id,
        audio_wav=pcm_to_wav(bytes(audio)) if (with_audio and audio) else None,
        usage=usage,
    )


async def probe(cloud: Cloud, *, timeout: float = 8.0) -> str:
    """Живая проверка: поднимаем сессию, ждём применения промпта, закрываем."""
    if not cloud.configured:
        return UNCONFIGURED
    loop = asyncio.get_event_loop()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                wss_url(cloud), headers=headers(cloud), heartbeat=20.0, timeout=timeout
            ) as ws:
                await ws.send_json(_session_payload(cloud, None))
                deadline = loop.time() + timeout
                while loop.time() < deadline:
                    try:
                        msg = await ws.receive(timeout=max(0.1, deadline - loop.time()))
                    except asyncio.TimeoutError:
                        break
                    if msg.type != aiohttp.WSMsgType.TEXT:
                        continue
                    event = json.loads(msg.data)
                    kind = event.get("type")
                    if kind == "session.updated":
                        return READY
                    if kind == "error":
                        return UNAVAILABLE
    except Exception:
        return UNAVAILABLE
    return UNAVAILABLE
