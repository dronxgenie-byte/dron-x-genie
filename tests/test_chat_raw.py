import requests
print("--- ПОЛНЫЙ ОТВЕТ СЕРВЕРА ---")
try:
    payload = {
        "message": "привет, как дела?",
        "model": "gemma-4-e4b-agentic-sol-fable-reasoning-geminicli"
    }
    r = requests.post("http://127.0.0.1:8001/chat", json=payload, timeout=30)
    print("Статус:", r.status_code)
    print("Сырой JSON:", r.json())
except Exception as e:
    print("Ошибка:", e)
print("--- КОНЕЦ ---")
