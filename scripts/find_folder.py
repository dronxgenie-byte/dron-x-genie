import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("YANDEX_API_KEY").strip()

print(f"🔑 Проверяем ключ: {api_key[:15]}...")

# Запрашиваем у Яндекса список всех папок, к которым у этого ключа есть доступ
url = "https://resource-manager.api.cloud.yandex.net/resource-manager/v1/folders"
headers = {
    "Authorization": f"Api-Key {api_key}"
}

try:
    response = requests.get(url, headers=headers, timeout=10)
    print(f"🔴 Статус ответа: {response.status_code}\n")
    
    if response.status_code == 200:
        data = response.json()
        folders = data.get("folders", [])
        if not folders:
            print("⚠️ У этого API-ключа НЕТ доступа ни к одной папке!")
            print("💡 Решение: Создай новый API-ключ в нужной папке через консоль Яндекса.")
        else:
            print("✅ Вот папки, к которым у этого ключа есть доступ:")
            for f in folders:
                print(f"  📁 ID: {f['id']} | Название: {f['name']}")
            
            print("\n💡 ДЕЙСТВИЕ:")
            print("1. Скопируй правильный ID папки из списка выше.")
            print("2. Открой файл .env и замени YANDEX_FOLDER_ID на этот ID.")
            print("3. Убедись, что в этой папке включена услуга 'YandexGPT' или 'AI Studio'.")
    else:
        print("❌ Ошибка доступа. Детали:")
        print(response.text)
        
except Exception as e:
    print(f"❌ Ошибка сети: {e}")