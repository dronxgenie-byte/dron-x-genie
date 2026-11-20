import requests
import json

print("--- ПРОВЕРКА СТРУКТУРЫ VAULT (ПАМЯТИ) ---")
try:
    resp = requests.get("http://127.0.0.1:8001/vault-structure", timeout=5)
    if resp.status_code == 200:
        data = resp.json()
        print("УСПЕХ: Бэкенд видит следующую структуру:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"ОШИБКА: Статус ответа {resp.status_code}")
        print(f"Текст ответа: {resp.text}")
except Exception as e:
    print(f"Ошибка подключения к порту 8001: {e}")

print("--- КОНЕЦ ПРОВЕРКИ ---")