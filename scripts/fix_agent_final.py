import os, json, glob
files = list(set(item for p in ["**/*pi*lmstudio*.json", "**/config.json", "**/agent_config.json"] for item in glob.glob(p, recursive=True)))
if not files:
    print("Конфиги не найдены. Укажи точное имя файла.")
else:
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as file: cfg = json.load(file)
            cfg['api_base'] = "http://127.0.0.1:1234/v1"
            cfg['model'] = "gemma-4-e4b-agentic-sol-fable-reasoning-geminicli"
            cfg['timeout'] = 30
            with open(f, 'w', encoding='utf-8') as file: json.dump(cfg, file, indent=2, ensure_ascii=False)
            print(f"УСПЕХ: {os.path.abspath(f)} обновлен.")
        except Exception as e:
            print(f"Пропуск или ошибка в {f}: {e}")
