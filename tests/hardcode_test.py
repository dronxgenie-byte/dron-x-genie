import requests
import os

# Данные берутся из переменных окружения
api_key = os.getenv("YANDEX_API_KEY")
folder_id = os.getenv("YANDEX_FOLDER_ID")

print(f"Проверяем папку: {folder_id}")

url = "https://llm.api.cloud.yandex.net/foundationModels/v1/chat/completion"
headers = {
    "Authorization": f"Api-Key {api_key}",
    "Content-Type": "application/json"
}

payload = {
    "modelUri": f"gpt://{folder_id}/yandexgpt/latest",
    "completionOptions": {"stream": False, "temperature": 0.6, "maxTokens": "50"},
    "messages": [{"role": "user", "text": "Скажи ОК"}]
}

response = requests.post(url, json=payload, headers=headers, timeout=10)

print(f"\n🔴 Статус HTTP: {response.status_code}")
print("📝 Ответ Яндекса:")
print(response.text)

if response.status_code == 200:
    print("\n✅ УСПЕХ! Значит, проблема была в чтении файла .env. Перезапусти сервер.")
else:
    print("\n❌ ПРОВАЛ. Значит, у этого ключа НЕТ прав на эту папку. Смотри ШАГ 2.")