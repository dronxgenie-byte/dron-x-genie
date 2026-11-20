import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class GenieAgent:
    def __init__(self):
        self.api_key = os.getenv("YANDEX_API_KEY").strip()
        self.folder_id = os.getenv("YANDEX_FOLDER_ID").strip()

        if not self.api_key or not self.folder_id:
            raise ValueError("Проверь ключи в .env")

        # Эндпоинты YandexGPT: пробуем chat/completion, затем completion (фолбэк)
        self.api_urls = [
            "https://llm.api.cloud.yandex.net/foundationModels/v1/chat/completion",
            "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
        ]

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.x_hub_path = os.path.join(base_dir, "vault", "06_X_HUB")
        os.makedirs(self.x_hub_path, exist_ok=True)

    def log_to_x_hub(self, user_msg: str, response: str):
        log_file = os.path.join(self.x_hub_path, f"genie_log_{datetime.now().strftime('%Y%m%d')}.md")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Запрос:** {user_msg}\n\n")
            f.write(f"**Ответ:** {response}\n\n---\n")

    def _build_payload(self, user_message: str, url: str) -> dict:
        """Собирает payload под конкретный эндпоинт Yandex API."""
        model_uri = f"gpt://{self.folder_id}/yandexgpt/latest"
        base_payload = {
            "modelUri": model_uri,
            "completionOptions": {
                "stream": False,
                "temperature": 0.7,
                "maxTokens": 2000,
            },
        }
        # chat/completion ожидает массив messages, completion — строку text
        if "/chat/completion" in url:
            base_payload["messages"] = [
                {"role": "system", "text": "Ты — GENIE, остроумный помощник. Отвечай на русском с лёгким пафосом."},
                {"role": "user", "text": user_message},
            ]
        else:
            base_payload["text"] = f"Ты — GENIE, остроумный помощник. Отвечай на русском с лёгким пафосом.\n\nПользователь: {user_message}"
        return base_payload

    def _extract_text(self, data: dict, url: str) -> str:
        """Извлекает текст ответа из разных форматов Yandex API."""
        if "/chat/completion" in url:
            return data["result"]["alternatives"][0]["message"]["text"]
        else:
            return data["result"]["alternatives"][0]["text"]

    def process(self, user_message: str) -> dict:
        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json",
        }

        last_error = None
        for url in self.api_urls:
            payload = self._build_payload(user_message, url)
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()
                ai_text = self._extract_text(data, url)
                self.log_to_x_hub(user_message, ai_text)
                return {
                    "response": ai_text,
                    "source": "GENIE (YandexGPT)",
                    "model": "YandexGPT",
                }
            except Exception as e:
                last_error = e
                continue

        return {"response": f"Ошибка YandexGPT: {last_error}", "source": "ERROR"}
