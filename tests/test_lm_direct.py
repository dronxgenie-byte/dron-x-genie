import requests
print("--- ПРЯМОЙ ЗАПРОС К LM STUDIO ---")
try:
    payload = {
        "model": "gemma-4-e4b-agentic-sol-fable-reasoning-geminicli",
        "messages": [{"role": "user", "content": "привет"}],
        "temperature": 0.7
    }
    r = requests.post("http://127.0.0.1:1234/v1/chat/completions", json=payload, timeout=15)
    print("Статус:", r.status_code)
    if r.status_code == 200:
        print("Ответ LM Studio:", r.json()["choices"][0]["message"]["content"])
    else:
        print("Ошибка LM Studio:", r.text)
except requests.exceptions.Timeout:
    print("ВЫВОД: LM Studio зависла. Эта модель слишком тяжёлая или сломана.")
except Exception as e:
    print("Ошибка:", e)
print("--- КОНЕЦ ---")
