import os
import json
import glob

print("--- НАСТРОЙКА КОНФИГА PI-LMSTUDIO ---")

patterns = ["*pi*lmstudio*.json", "*pi*lmstudio*.yaml", "*pi*lmstudio*.yml", "config.json", "agent_config.json"]
found_files = list(set(glob.glob(p, recursive=True) for p in patterns))
found_files = [item for sublist in found_files for item in sublist] # Flatten list

if not found_files:
    print("ОШИБКА: Файлы конфигурации не найдены.")
    print("Напиши точное имя файла конфига, и я дам команду для его точечного исправления.")
else:
    print(f"Найдено файлов: {len(found_files)}")
    for file_path in found_files:
        abs_path = os.path.abspath(file_path)
        print(f"\nОбрабатываю: {abs_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Жесткая установка целевой модели и адреса
            config['api_base'] = "http://127.0.0.1:1234/v1"
            config['model'] = "gemma-4-e4b-agentic-sol-fable-reasoning-geminicli"
            config['timeout'] = 30
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            print("УСПЕХ: Конфиг обновлен. Модель: gemma-4-e4b-agentic-sol-fable-reasoning-geminicli")
        except json.JSONDecodeError:
            print(f"ПРЕДУПРЕЖДЕНИЕ: Файл {abs_path} не является JSON (возможно, YAML).")
            print("Скопируй сюда первые 5 строк этого файла, и я напишу скрипт под YAML.")
        except Exception as e:
            print(f"ОШИБКА: {e}")

print("\n--- ГОТОВО ---")