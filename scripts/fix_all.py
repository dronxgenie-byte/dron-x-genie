genie_code = """import os
import json
import asyncio
import websockets
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class GenieAgent:
    def __init__(self):
        self.api_key = os.getenv("YANDEX_API_KEY")
        self.folder_id = os.getenv("YANDEX_FOLDER_ID")
        self.agent_id = os.getenv("YANDEX_AGENT_ID")
        
        if not all([self.api_key, self.folder_id, self.agent_id]):
            raise ValueError("Проверь YANDEX_API_KEY, FOLDER_ID и AGENT_ID в .env")
        
        self.ws_url = f"wss://ai.api.cloud.yandex.net/v1/realtime?model=gpt://{self.folder_id}/speech-realtime-max-tts-live/latest"
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.x_hub_path = os.path.join(base_dir, "vault", "06_X_HUB")
        os.makedirs(self.x_hub_path, exist_ok=True)

    def log_to_x_hub(self, user_msg: str, response: str):
        log_file = os.path.join(self.x_hub_path, f"genie_log_{datetime.now().strftime('%Y%m%d')}.md")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\\n## {timestamp}\\n")
            f.write(f"**Запрос:** {user_msg}\\n\\n")
            f.write(f"**Ответ:** {response}\\n\\n---\\n")

    async def process_async(self, user_message: str) -> dict:
        headers = {"Authorization": f"Api-Key {self.api_key}"}
        full_response = ""
        
        try:
            async with websockets.connect(self.ws_url, additional_headers=headers) as ws:
                await ws.send(json.dumps({
                    "type": "session.update",
                    "session": {
                        "prompt": {"id": self.agent_id}
                    }
                }))
                await asyncio.sleep(0.3)

                await ws.send(json.dumps({
                    "type": "conversation.item.create",
                    "item": {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": user_message}]
                    }
                }))

                await ws.send(json.dumps({"type": "response.create"}))

                async for raw in ws:
                    event = json.loads(raw)
                    msg_type = event.get("type")
                    
                    if msg_type == "response.output_text.delta":
                        full_response += event.get("delta", "")
                    elif msg_type in ["response.done", "response.output_item.done"]:
                        break
                    elif msg_type == "error":
                        return {"response": f"Ошибка Яндекса: {event}", "source": "ERROR"}
                        
                self.log_to_x_hub(user_message, full_response)
                
                return {
                    "response": full_response,
                    "source": "GENIE (Яндекс)",
                    "model": "speech-realtime-max"
                }
                
        except Exception as e:
            return {"response": f"Ошибка подключения: {e}", "source": "ERROR"}

    def process(self, user_message: str) -> dict:
        return asyncio.run(self.process_async(user_message))
"""

with open("backend/genie.py", "w", encoding="utf-8") as f:
    f.write(genie_code)
    
print("✅ backend/genie.py создан")