#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import base64
import json
import logging
import sys

import aiohttp
from yandex_ai_studio_sdk._experimental.audio.microphone import AsyncMicrophone
from yandex_ai_studio_sdk._experimental.audio.out import AsyncAudioOut

assert sys.version_info >= (3, 10), "Python 3.10+ is required"

import os

# ТВОИ ДАННЫЕ (берутся из переменных окружения)
YANDEX_CLOUD_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
YANDEX_CLOUD_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_REALTIME_MODEL = "speech-realtime-max-tts-live/latest"
PROMPT_ID = "aip1i1ag428a8ki54kai"  # ID твоего агента GENIE

assert YANDEX_CLOUD_FOLDER_ID and YANDEX_CLOUD_API_KEY, (
	"YANDEX_CLOUD_FOLDER_ID и YANDEX_CLOUD_API_KEY обязательны"
)

WSS_URL = (
	"wss://ai.api.cloud.yandex.net/v1/realtime"
	f"?model=gpt://{YANDEX_CLOUD_FOLDER_ID}/{YANDEX_REALTIME_MODEL}"
)

HEADERS = {"Authorization": f"Api-Key {YANDEX_CLOUD_API_KEY}"}

def b64_decode(s: str) -> bytes:
	return base64.b64decode(s)

def b64_encode(b: bytes) -> str:
	return base64.b64encode(b).decode("ascii")

logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s - %(levelname)s - %(message)s",
	datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

def process_function_call(item: dict) -> dict:
	call_id = item.get("call_id")
	return {
		"type": "conversation.item.create",
		"item": {
			"type": "function_call_output",
			"call_id": call_id,
			"output": json.dumps({"ok": True}, ensure_ascii=False),
		},
	}

async def setup_session(ws: aiohttp.ClientWebSocketResponse) -> None:
	prompt_obj: dict[str, object] = {
		"id": PROMPT_ID,
		"variables": {
			"service_name": "DRON_X_GENIE"
		}
	}
	await ws.send_json(
		{
			"type": "session.update",
			"session": {
				"prompt": prompt_obj,
			},
		}
	)
	logger.info("Отправлен session.update с prompt.id=%r", PROMPT_ID)

async def downlink(ws: aiohttp.ClientWebSocketResponse, audio_out: AsyncAudioOut) -> None:
	play_epoch = 0
	current_response_epoch = None

	async for msg in ws:
		if msg.type != aiohttp.WSMsgType.TEXT:
			continue

		message = json.loads(msg.data)
		msg_type = message.get("type")

		match msg_type:
			case "session.created":
				logger.info("Сессия создана.")
			case "conversation.item.input_audio_transcription.completed":
				transcript = message.get("transcript", "")
				if transcript:
					logger.info(f"🎤 Ты сказал: {transcript}")
			case "response.output_text.delta":
				delta = message.get("delta", "")
				if delta:
					print(delta, end="", flush=True)
			case "input_audio_buffer.speech_started":
				play_epoch += 1
				current_response_epoch = None
				await audio_out.clear()
			case "response.created":
				current_response_epoch = play_epoch
				print("\n🗣️ Джинн отвечает: ", end="", flush=True)
			case "response.output_audio.delta":
				if current_response_epoch == play_epoch:
					delta = message.get("delta")
					if delta:
						decoded = b64_decode(delta)
						await audio_out.write(decoded)
			case "response.output_item.done":
				print() # Перенос строки после ответа
				item = message.get("item") or {}
				if item.get("type") == "function_call":
					payload_item = process_function_call(item)
					await ws.send_json(payload_item)
					await ws.send_json({"type": "response.create"})
			case "error":
				logger.error(f"ОШИБКА СЕРВЕРА: {json.dumps(message, ensure_ascii=False)}")

async def uplink(ws: aiohttp.ClientWebSocketResponse) -> None:
	mic = AsyncMicrophone(samplerate=44100)
	async for pcm in mic:
		try:
			await ws.send_json(
				{
					"type": "input_audio_buffer.append",
					"audio": b64_encode(pcm),
				}
			)
		except aiohttp.ClientConnectionResetError:
			return

async def main() -> None:
	print("="*50)
	print("🪔 ДЖИНН ГОТОВ К ОБЩЕНИЮ")
	print("Говори в микрофон. Для выхода нажми Ctrl+C.")
	print("="*50)

	try:
		async with aiohttp.ClientSession() as session:
			async with session.ws_connect(WSS_URL, headers=HEADERS, heartbeat=20.0) as ws:
				logger.info("Подключено к Realtime API.")
				await setup_session(ws)

				async with AsyncAudioOut(samplerate=44100) as audio_out:
					await asyncio.gather(
						uplink(ws),
						downlink(ws, audio_out),
					)
	except (KeyboardInterrupt, asyncio.CancelledError):
		print("\nВыход.")
	finally:
		logger.info("Соединение закрыто.")

if __name__ == "__main__":
	asyncio.run(main())