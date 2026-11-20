import requests
import os

# Ключи берутся из переменных окружения
API_KEY = os.getenv("YANDEX_API_KEY")
AGENT_ID = "aip1i1ag428a8ki54kai"
FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")

# Официальный endpoint для Текстовых Агентов
url = f"https://llm.api.cloud.yandex.net/ai-foundry/v1/agents/{AGENT_ID}:run"

headers = {
    "Authorization": f"Api-Key {API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "folderId": FOLDER_ID,
    "messages": [
        {
            "role": "user",
            "text": "Джинн, ты меня слышишь? Ответь коротко."
        }
    ]
}

print(f"📡 Отправляем запрос агенту: {AGENT_ID}")
print(f"🔗 URL: {url}\n")

try:
    response = requests.post(url, json=payload, headers=headers, timeout=15)
    print(f"🔴 HTTP Статус: {response.status_code}")
    print("📝 Полный ответ Яндекса:")
    print(response.text)
    
    if response.status_code == 200:
        print("\n✅ УСПЕХ! Мы нашли правильную дверь!")
    else:
        print("\n⚠️ Если тут 404, значит ID агента неверный или он не опубликован.")
        
except Exception as e:
    print(f"❌ Ошибка сети: {e}")