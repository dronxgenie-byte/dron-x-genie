import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("YANDEX_API_KEY").strip()
folder_id = os.getenv("YANDEX_FOLDER_ID").strip()
agent_id = os.getenv("YANDEX_AGENT_ID").strip()

print("="*60)
print("🔧 ДИАГНОСТИКА АГЕНТА YANDEX AI STUDIO")
print("="*60)
print(f"📁 Folder ID: {folder_id}")
print(f"🤖 Agent ID:  {agent_id}")
print(f"🔑 API Key:   {api_key[:15]}...{api_key[-5:]}")
print("="*60)

# Официальный endpoint для вызова Текстового Агента
url = f"https://llm.api.cloud.yandex.net/foundationModels/v1/agents/{agent_id}/completion"

headers = {
    "Authorization": f"Api-Key {api_key}",
    "Content-Type": "application/json"
}

payload = {
    "folderId": folder_id,
    "messages": [
        {
            "role": "user",
            "text": "Привет, Джинн. Ты меня слышишь?"
        }
    ]
}

print(f"\n📡 Отправляем запрос на:\n{url}\n")

try:
    response = requests.post(url, json=payload, headers=headers, timeout=15)
    print(f"🔴 HTTP Статус: {response.status_code}")
    
    print("\n📝 Полный ответ от Яндекса:")
    try:
        # Пытаемся вывести красивый JSON
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        # Если это не JSON, выводим как текст
        print(response.text)
        
    if response.status_code == 200:
        print("\n🎉 УСПЕХ! Агент работает. Теперь перенесём этот URL в основной код.")
    elif response.status_code == 404:
        print("\n⚠️ ВАЖНО: 404 для агента означает:")
        print("1. Агент НЕ ОПУБЛИКОВАН в интерфейсе AI Studio.")
        print("2. Неверный Agent ID (проверь URL в браузере).")
        print("3. У API-ключа нет роли 'ai.languageModels.user' на эту папку.")
        
except Exception as e:
    print(f"❌ Ошибка сети: {e}")