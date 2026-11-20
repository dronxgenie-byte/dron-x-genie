agent_code = """import os
import requests
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
        
        # Правильный URL для вызова Runtime Agents (Responses API)
        self.api_url = f"https://{self.folder_id}.ai.api.cloud.yandex.net/ai-foundry/v1/agents/{self.agent_id}:run"
        
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
        
        # Формат запроса для Runtime Agent
        payload = {
            "messages": [
                {
                    "role": "user",
                    "text": user_message
                }
            ],
            "sessionVariables": {} 
        }
        
        try:
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Парсим ответ от Агента (структура может отличаться от простой модели)
            # Обычно ответ лежит в messages[0].text или result.alternatives[0].message.text
            # Для агентов AI Studio ответ часто приходит в поле 'messages'
            
            if "messages" in data and len(data["messages"]) > 0:
                ai_text = data["messages"][0].get("text", "Нет текста в ответе")
            elif "result" in data:
                 ai_text = data["result"].get("alternatives", [{}])[0].get("message", {}).get("text", "Неизвестный формат ответа")
            else:
                ai_text = str(data) # На всякий случай выводим всё, если формат неожиданный
            
            self.log_to_x_hub(user_message, ai_text)
            
            return {
                "response": ai_text,
                "source": "GENIE (Агент)",
                "model": "Alice AI LLM Flash"
            }
        except requests.exceptions.HTTPError as e:
            return {"response": f"Ошибка Агента: {e.response.text}", "source": "ERROR"}
        except Exception as e:
            return {"response": f"Ошибка подключения: {e}", "source": "ERROR"}
"""

with open("backend/genie.py", "w", encoding="utf-8") as f:
    f.write(agent_code)
    
print("✅ backend/genie.py создан (версия для Текстового Агента)")