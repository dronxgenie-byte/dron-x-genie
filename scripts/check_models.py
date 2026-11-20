import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("YANDEX_API_KEY").strip()
folder_id = os.getenv("YANDEX_FOLDER_ID").strip()

print(f"🔑 Ключ: {api_key[:15]}...")
print(f"📁 Проверяем папку: {folder_id}\n")

# Запрашиваем список доступных моделей в этой папке
url = f"https://llm.api.cloud.yandex.net/foundationModels/v1/models"
headers = {
    "Authorization": f"Api-Key {api_key}"
}

try:
    response = requests.get(url, headers=headers, timeout=10)
    print(f"🔴 Статус ответа: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Вот модели, доступные в этой папке:")
        for model in data.get("modelVersions", []):
            print(f"  - {model.get('uri')}")
    else:
        print("❌ Ошибка доступа. Детали:")
        print(response.text)
        
except Exception as e:
    print(f"❌ Ошибка сети: {e}")