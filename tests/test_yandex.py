import requests
import os

api_key = os.getenv("YANDEX_API_KEY")
folder_id = os.getenv("YANDEX_FOLDER_ID")
model = "yandexgpt/latest"

url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

headers = {
    "Authorization": f"Api-Key {api_key}",
    "x-folder-id": folder_id,
    "Content-Type": "application/json"
}

payload = {
    "modelUri": f"gpt://{folder_id}/{model}",
    "completionOptions": {"stream": False, "temperature": 0.5, "maxTokens": "2000"},
    "messages": [
        {"role": "system", "text": "Ты полезный ассистент."},
        {"role": "user", "text": "привет, как дела?"}
    ]
}

response = requests.post(url, json=payload, headers=headers)
print(f"Статус: {response.status_code}")
print(f"Ответ: {response.text}")
