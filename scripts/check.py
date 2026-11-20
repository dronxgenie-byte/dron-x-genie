import requests
print("=== ПРОВЕРКА СИСТЕМЫ ===")
try:
    r = requests.get("https://llm.api.cloud.yandex.net", timeout=10)
    print(f"1. TLS работает (статус: {r.status_code})")
except Exception as e:
    print(f"1. Ошибка TLS: {e}")

try:
    with open("../.env", "r", encoding="utf-8") as f:
        lines = f.readlines()
    api_key = next((l.split("=")[1].strip() for l in lines if "YANDEX_API_KEY=" in l), None)
    folder_id = next((l.split("=")[1].strip() for l in lines if "YANDEX_FOLDER_ID=" in l), None)
    print(f"2. Ключи найдены. Folder ID: {folder_id}")
    
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {"Authorization": f"Api-Key {api_key}", "x-folder-id": folder_id, "Content-Type": "application/json"}
    payload = {"modelUri": f"gpt://{folder_id}/yandexgpt/latest", "completionOptions": {"stream": False, "temperature": 0.5, "maxTokens": "50"}, "messages": [{"role": "user", "text": "привет"}]}
    
    r = requests.post(url, json=payload, headers=headers, timeout=15)
    if r.status_code == 200:
        print("3. Яндекс ответил успешно! (Статус 200)")
    else:
        print(f"3. Ответ Яндекса: Статус {r.status_code} -> {r.text[:150]}")
except Exception as e:
    print(f"2/3. Ошибка чтения или запроса: {e}")

print("=== ПРОВЕРКА ЗАВЕРШЕНА ===")
