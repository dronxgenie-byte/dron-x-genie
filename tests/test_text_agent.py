import requests
import json
import os

# Ключи берутся из переменных окружения
api_key = os.getenv("YANDEX_API_KEY")
folder_id = os.getenv("YANDEX_FOLDER_ID")
agent_id = "aip1i1ag428a8ki54kai"  # ID твоего текстового агента GENIE

print(f"📁 Папка: {folder_id}")
print(f"🤖 Агент: {agent_id}")

# ПРАВИЛЬНЫЙ эндпоинт для Текстовых Агентов (не базовой модели!)
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
            "text": "Джинн, ты меня слышишь? Ответь коротко."
        }
    ]
}

print(f"\n📡 Отправляем запрос агенту...\n")

try:
    response = requests.post(url, json=payload, headers=headers, timeout=15)
    print(f"🔴 Статус HTTP: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        # Ответ агента обычно лежит в messages[0].text
        if "messages" in data and len(data["messages"]) > 0:
            text = data["messages"][0].get("text", "Нет текста")
        else:
            text = str(data)
            
        print(f"\n✅ УСПЕХ! Джинн ответил:")
        print(f"💬 {text}")
        print("\n🎉 ТЕПЕРЬ ЭТОТ КОД НУЖНО ВСТАВИТЬ В backend/genie.py")
    else:
        print("\n❌ Ошибка. Детальный ответ Яндекса:")
        print(response.text)
        
except Exception as e:
    print(f"❌ Ошибка сети: {e}")