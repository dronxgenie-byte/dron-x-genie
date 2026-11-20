import requests
print("--- ПРОВЕРКА ОТВЕТА ДРОНА ---")
try:
    payload = {
        "message": "привет, как дела?",
        "model": "gemma-4-e4b-agentic-sol-fable-reasoning-geminicli"
    }
    r = requests.post("http://127.0.0.1:8001/chat", json=payload, timeout=30)
    print("Статус:", r.status_code)
    if r.status_code == 200:
        print("Ответ Дрона:", r.json().get("response", "Нет текста ответа"))
    else:
        print("Текст ошибки:", r.text)
except Exception as e:
    print("Ошибка подключения:", e)
print("--- КОНЕЦ ---")
