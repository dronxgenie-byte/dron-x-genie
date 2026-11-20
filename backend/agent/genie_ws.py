"""Голосовой мост браузер ↔ GENIE (Yandex Realtime).

Браузер шлёт PCM16 моно 44 100 Гц кусками base64, получает обратно
текст, транскрипт пользователя и аудио-дельты. Ключ Yandex в браузер
не попадает: соединение с облаком держит сервер.

Протокол браузер → сервер:
    {"type": "audio", "pcm": "<base64 PCM16>"}   — кусок микрофона
    {"type": "text",  "text": "..."}             — текстовый ввод
    {"type": "stop"}                             — заглушить ответ
    {"type": "close"}                            — закрыть сессию

Сервер → браузер:
    {"type": "ready"}                            — сессия и промпт применены
    {"type": "user_text", "text": "..."}         — что услышал ASR
    {"type": "text", "text": "..."}              — дельта ответа
    {"type": "audio", "pcm": "<base64 PCM16>"}   — дельта голоса
    {"type": "interrupt"}                        — пользователь начал говорить
    {"type": "done", "usage": {...}}             — ход завершён
    {"type": "error", "message": "..."}          — ошибка
"""

from __future__ import annotations

import asyncio
import json

import aiohttp
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from . import genie
from .config import load_cloud

router = APIRouter()


async def _send(ws: WebSocket, payload: dict) -> None:
    try:
        await ws.send_json(payload)
    except (WebSocketDisconnect, RuntimeError):
        raise WebSocketDisconnect() from None


async def _browser_to_yandex(ws: WebSocket, yws: aiohttp.ClientWebSocketResponse) -> None:
    while True:
        raw = await ws.receive_text()
        try:
            data = json.loads(raw)
        except ValueError:
            continue

        kind = data.get("type")
        if kind == "audio":
            pcm = data.get("pcm")
            if pcm:
                await yws.send_json({"type": "input_audio_buffer.append", "audio": pcm})
        elif kind == "text":
            text = (data.get("text") or "").strip()
            if text:
                await yws.send_json(
                    {
                        "type": "conversation.item.create",
                        "item": {
                            "type": "message",
                            "role": "user",
                            "content": [{"type": "input_text", "text": text}],
                        },
                    }
                )
                await yws.send_json({"type": "response.create"})
        elif kind == "stop":
            await yws.send_json({"type": "response.cancel"})
        elif kind == "close":
            return


async def _yandex_to_browser(ws: WebSocket, yws: aiohttp.ClientWebSocketResponse) -> None:
    ready_sent = False

    async for msg in yws:
        if msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED):
            return
        if msg.type != aiohttp.WSMsgType.TEXT:
            continue

        event = json.loads(msg.data)
        kind = event.get("type")

        if kind == "session.updated":
            # Yandex присылает session.updated дважды на один session.update.
            if not ready_sent:
                ready_sent = True
                await _send(ws, {"type": "ready"})
        elif kind == "conversation.item.input_audio_transcription.completed":
            text = (event.get("transcript") or "").strip()
            if text:
                await _send(ws, {"type": "user_text", "text": text})
        elif kind == "response.output_text.delta":
            delta = event.get("delta") or ""
            if delta:
                await _send(ws, {"type": "text", "text": delta})
        elif kind == "response.output_audio.delta":
            delta = event.get("delta")
            if delta:
                await _send(ws, {"type": "audio", "pcm": delta})
        elif kind == "input_audio_buffer.speech_started":
            await _send(ws, {"type": "interrupt"})
        elif kind == "response.output_item.done":
            item = event.get("item") or {}
            if item.get("type") == "function_call":
                await yws.send_json(genie._function_output(item))
                await yws.send_json({"type": "response.create"})
        elif kind == "response.done":
            usage = (event.get("response") or {}).get("usage") or {}
            await _send(ws, {"type": "done", "usage": usage})
        elif kind == "error":
            detail = (event.get("error") or {}).get("message") or "ошибка облака"
            await _send(ws, {"type": "error", "message": detail})


@router.websocket("/ws/genie")
async def genie_voice(ws: WebSocket) -> None:
    await ws.accept()
    cloud = load_cloud()

    if not cloud.configured:
        await _send(ws, {"type": "error", "message": "Джинн не настроен: нет ключа Yandex."})
        await ws.close()
        return

    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                genie.wss_url(cloud), headers=genie.headers(cloud), heartbeat=20.0
            ) as yws:
                await yws.send_json(genie._session_payload(cloud, None))

                tasks = [
                    asyncio.create_task(_browser_to_yandex(ws, yws)),
                    asyncio.create_task(_yandex_to_browser(ws, yws)),
                ]
                done, pending = await asyncio.wait(
                    tasks, return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()
                await asyncio.gather(*pending, return_exceptions=True)
    except WebSocketDisconnect:
        pass
    except aiohttp.ClientError as exc:
        try:
            await _send(ws, {"type": "error", "message": f"Сеть недоступна: {exc}"})
        except Exception:
            pass
    except Exception as exc:  # noqa: BLE001
        try:
            await _send(ws, {"type": "error", "message": f"Сбой голосового канала: {exc}"})
        except Exception:
            pass
    finally:
        try:
            await ws.close()
        except Exception:
            pass
