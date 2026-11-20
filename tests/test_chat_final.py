import requests
print("--- ПРОВЕРКА ОТВЕТА ДРОНА (ПРАВИЛЬНЫЙ ЗАПРОС) ---")
try:
    payload = {
        "message": "привет, как дела?",
        "model": "dron"
    }
    r = requests.post("http://127.0.0.1:8001/chat", json=payload, timeout=30)
    print("Статус:", r.status_code)
    data = r.json()
    print("Ответ Дрона:", data.get("reply", "Нет текста ответа"))
    print("Использованная модель:", data.get("model"))
except Exception as e:
    print("Ошибка:", e)
print("--- КОНЕЦ ---")
