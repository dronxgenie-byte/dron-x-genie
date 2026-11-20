import requests

print("--- ПРОВЕРКА ДОСТУПНЫХ ЭНДПОИНТОВ FASTAPI ---")
try:
    resp = requests.get("http://127.0.0.1:8001/openapi.json", timeout=5)
    if resp.status_code == 200:
        data = resp.json()
        paths = data.get("paths", {})
        print("Найдены следующие маршруты (эндпоинты):")
        if not paths:
            print("ВНИМАНИЕ: Список маршрутов пуст. Возможно, роуты не подключены в main.py")
        for path, methods in paths.items():
            methods_str = ", ".join(methods.keys()).upper()
            print(f"- {path}  [Методы: {methods_str}]")
    else:
        print(f"Не удалось получить схему API. Код ответа: {resp.status_code}")
except Exception as e:
    print(f"Ошибка подключения к порту 8001: {e}")

print("\n--- КОНЕЦ ПРОВЕРКИ ---")