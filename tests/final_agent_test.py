import requests
import os

# Вставь сюда ТОЧНЫЙ ID из адресной строки браузера
AGENT_ID = "aip1i1ag428a8ki54kai"  # <-- ЗАМЕНИ ЭТОТ ID на свой актуальный
API_KEY = os.getenv("YANDEX_API_KEY")
FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")

print(f"Проверяем агента: {AGENT_ID}")

# Пробуем оба актуальных эндпоинта Яндекса для агентов
urls_to_try = [
    f"https://llm.api.cloud.yandex.net/ai-foundry/v1/agents/{AGENT_ID}:run",
    f"https://llm.api.cloud.yandex.net/foundationModels/v1/agents/{AGENT_ID}/completion"
]

payload = {
    "folderId": FOLDER_ID,
    "messages": [{"role": "user", "text": "Джинн, ты здесь? Ответь коротко."}]
}

headers = {
    "Authorization": f"Api-Key {API_KEY}",
    "Content-Type": "application/json"
}

for url in urls_to_try:
    print(f"\n📡 Стучусь в: {url}")
    response = requests.post(url, json=payload, headers=headers, timeout=15)
    print(f"🔴 HTTP Код: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        text = data.get("messages", [{}])[0].get("text", str(data))
        print(f"\n✅ УСПЕХ! Джинн ответил:\n💬 {text}")
        print("\n🎉 НАЙДЕН РАБОЧИЙ ЭНДПОИНТ! Теперь обновим backend/genie.py")
        break
    else:
        print(f"❌ Ответ: {response.text}")