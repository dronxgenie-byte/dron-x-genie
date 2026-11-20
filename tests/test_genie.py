import os
import json
import asyncio
import websockets
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("YANDEX_API_KEY")
agent_id = os.getenv("YANDEX_AGENT_ID")

print(f"API Key: {api_key[:10]}...")
print(f"Agent ID: {agent_id}")

# Правильный URL для Yandex AI Studio Realtime API
ws_url = f"wss://llm.mcp.cloud.yandex.net/ai-foundry/foundry/realtime/v1/converse?agent_id={agent_id}"

print(f"URL: {ws_url}")

if not api_key or not agent_id:
    print("❌ Ключи не настроены в .env")
    exit()

async def test():
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        print("Подключаюсь к Яндексу...")
        async with websockets.connect(ws_url, additional_headers=headers) as ws:
            print("✅ Подключено!")
            
            # Отправляем приветствие
            message_event = {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "Привет, Джинн! Как дела?"}]
                }
            }
            await ws.send(json.dumps(message_event))
            print("Сообщение отправлено")
            
            # Запрашиваем ответ
            response_event = {
                "type": "response.create",
                "response": {
                    "modalities": ["text"],
                    "instructions": ""
                }
            }
            await ws.send(json.dumps(response_event))
            print("Запрос ответа отправлен")
            
            full_response = ""
            async for raw in ws:
                event = json.loads(raw)
                event_type = event.get("type", "")
                print(f"📨 Получено событие: {event_type}")
                
                if event_type == "response.text.delta":
                    delta = event.get("delta", "")
                    full_response += delta
                    print(f"💬 Часть ответа: {delta}")
                elif event_type == "response.text.done":
                    print(f"\n✅ Полный ответ Джинна: {full_response}")
                    break
                elif event_type == "error":
                    print(f" Ошибка: {event}")
                    break
                    
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Ошибка подключения (HTTP {e.status_code}):")
        print(f"Возможно, агент не настроен или ключ недействителен")
    except Exception as e:
        print(f"❌ Ошибка: {type(e).__name__}: {e}")

asyncio.run(test())