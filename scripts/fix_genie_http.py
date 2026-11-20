genie_code = """import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class GenieAgent:
    def __init__(self):
        self.api_key = os.getenv("YANDEX_API_KEY")
        self.folder_id = os.getenv("YANDEX_FOLDER_ID")
        
        if not self.api_key or not self.folder_id:
            raise ValueError("Проверь YANDEX_API_KEY и FOLDER_ID в .env")
        
        # HTTP API YandexGPT - работает стабильно
        self.api_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/chat/completion"
        
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

    def process(self, user_message: str) -> dict:
        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "modelUri": f"gpt://{self.folder_id}/yandexgpt/latest",
            "completionOptions": {
                "stream": False,
                "temperature": 0.7,
                "maxTokens": "1000"
            },
            "messages": [
                {
                    "role": "system",
                    "text": "Ты — GENIE, нейроДжинн. Отвечай на русском языке, с лёгким магическим пафосом, но чётко и по делу. Обращайся 'повелитель' или 'хозяин'."
                },
                {
                    "role": "user",
                    "text": user_message
                }
            ]
        }
        
        try:
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            ai_text = data["result"]["alternatives"][0]["message"]["text"]
            self.log_to_x_hub(user_message, ai_text)
            
            return {
                "response": ai_text,
                "source": "GENIE (Яндекс HTTP)",
                "model": "YandexGPT"
            }
        except requests.exceptions.HTTPError as e:
            return {"response": f"Ошибка Яндекса: {e.response.text}", "source": "ERROR"}
        except Exception as e:
            return {"response": f"Ошибка подключения: {e}", "source": "ERROR"}
"""

with open("backend/genie.py", "w", encoding="utf-8") as f:
    f.write(genie_code)
    
print("✅ backend/genie.py создан (HTTP версия)")