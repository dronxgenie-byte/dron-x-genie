import requests
import os
import json
from datetime import datetime
from pathlib import Path
from phrases import get_phrase
from genie import GenieAgent

class DronAgent:
    def __init__(self):
        self.api_url = "http://127.0.0.1:1234/v1/chat/completions"
        self.fast_model = "gemma-4-e4b"
        self.main_model = "gemma-4-e4b"
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.vault_path = os.path.join(base_dir, "vault")
        self.logs_path = os.path.join(self.vault_path, "05_SYSTEM", "logs")
        os.makedirs(self.logs_path, exist_ok=True)
        
        # Загружаем конфигурацию из configs/dron.json
        self.config = self._load_config()
        self.system_prompt = "\n".join(self.config.get("system_prompt", []))
        self.model_config = self.config.get("model", {})
        self.base_url = self.model_config.get("base_url", "http://127.0.0.1:1234/v1")
        self.temperature = self.model_config.get("temperature", 0.2)
        self.model_name = self.model_config.get("name", "gemma-4-e4b")
        
        # Инициализируем Джинна
        self.genie = GenieAgent()
    
    def _load_config(self) -> dict:
        """Загружает конфигурацию из configs/dron.json"""
        config_path = Path(__file__).resolve().parent.parent / "configs" / "dron.json"
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Не удалось загрузить dron.json: {e}")
            return {
                "system_prompt": ["Ты — DRON. Отвечай кратко, по делу, на русском языке."],
                "model": {"name": "gemma-4-e4b", "temperature": 0.2, "base_url": "http://127.0.0.1:1234/v1"}
            }
        
    def update_status(self, action: str):
        status_file = os.path.join(self.logs_path, "dron_heartbeat.md")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(status_file, "w", encoding="utf-8") as f:
            f.write(f"# Статус Дрона\n\n- **Время:** {timestamp}\n- **Действие:** {action}\n- **Статус:** Активен\n")

    def save_to_inbox(self, content: str) -> str:
        self.update_status("Сохранение заметки в INBOX")
        inbox_path = os.path.join(self.vault_path, "01_INBOX")
        os.makedirs(inbox_path, exist_ok=True)
        filepath = os.path.join(inbox_path, f"note_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# Запись от {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n{content}\n")
        self.update_status("Ожидание команд")
        return get_phrase("saving", mode="x")

    def summarize_chat(self, chat_history: list, model_to_use: str) -> str:
        self.update_status("Сжатие контекста чата...")
        history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
        
        prompt = f"Сделай краткую выжимку диалога. Только факты, код и следующие шаги. Игнорируй воду.\nДИАЛОГ:\n{history_text}"
        
        payload = {
            "model": model_to_use,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "stream": False
        }
        
        try:
            response = requests.post(self.api_url, json=payload, timeout=180)
            response.raise_for_status()
            summary_text = response.json()["choices"][0]["message"]["content"]
            
            summary_path = os.path.join(self.vault_path, "04_RESOURCES", "chat_summaries")
            os.makedirs(summary_path, exist_ok=True)
            filename = f"summary_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
            
            with open(os.path.join(summary_path, filename), "w", encoding="utf-8") as f:
                f.write(f"# Выжимка чата\n\n{summary_text}\n")
            
            self.update_status("Контекст сжат и сохранен")
            return f"✅ Чат сжат и сохранен в `04_RESOURCES/chat_summaries/{filename}`."
        except Exception as e:
            self.update_status("Ошибка при сжатии")
            return f"❌ Ошибка сжатия: {e}"

    def summon_genie(self, user_message: str) -> dict:
        self.update_status(f"Призываю Джинна: {user_message[:30]}...")
        result = self.genie.process(user_message)
        self.update_status("Джинн ответил, ожидаю команд")
        return result

    def process(self, user_message: str, mode: str = "x", chat_history: list = None) -> dict:
        self.update_status(f"Обработка: {user_message[:30]}...")
        msg_lower = user_message.lower()
        
        if msg_lower.startswith("/сохрани") or msg_lower.startswith("/save"):
            content = user_message.split(maxsplit=1)[1] if len(user_message.split(maxsplit=1)) > 1 else user_message
            return {"response": self.save_to_inbox(content), "source": "DRON"}
            
        if msg_lower.startswith("/сжать") or msg_lower.startswith("/summarize"):
            if chat_history and len(chat_history) > 2:
                return {"response": self.summarize_chat(chat_history, self.main_model), "source": "DRON", "action": "clear_chat"}
            else:
                return {"response": "В чате слишком мало сообщений для сжатия.", "source": "DRON"}

        if "что делает дрон" in msg_lower or "статус дрона" in msg_lower:
            status_file = os.path.join(self.logs_path, "dron_heartbeat.md")
            if os.path.exists(status_file):
                with open(status_file, "r", encoding="utf-8") as f:
                    return {"response": f"🧞 Джинн докладывает: {f.read()}", "source": "GENIE"}
            else:
                return {"response": "Файл статуса не найден. Дрон молчит.", "source": "GENIE"}

        model_to_use = self.fast_model if len(user_message) < 50 else self.main_model
        system_prompt = "Ты — DRON. Отвечай кратко, по делу, на русском языке."
        
        payload = {
            "model": model_to_use,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.3,
            "stream": False
        }
        
        try:
            timeout = 120 if model_to_use == self.main_model else 30
            response = requests.post(self.api_url, json=payload, timeout=timeout)
            response.raise_for_status()
            ai_text = response.json()["choices"][0]["message"]["content"]
            
            self.update_status("Ожидание команд")
            return {
                "thinking": get_phrase("thinking", mode=mode),
                "response": ai_text,
                "source": f"DRON ({'12B' if model_to_use == self.main_model else '4B'})"
            }
        except Exception as e:
            self.update_status("Ошибка связи с моделью")
            return {"response": get_phrase("error", mode=mode), "source": "ERROR"}