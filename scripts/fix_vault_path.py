from pathlib import Path

print("--- ИСПРАВЛЕНИЕ ПУТИ К VAULT В .ENV ---")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
env_file = str(_PROJECT_ROOT / ".env")
correct_path = str(_PROJECT_ROOT.parent / "DRON_X_GENIE") # Используем относительный путь к DRON_X_GENIE

# Проверяем, существует ли .env
if not os.path.exists(env_file):
    print("Файл .env не найден. Создаю новый...")
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(f"VAULT_PATH={correct_path}\n")
    print("УСПЕХ: Файл .env создан с правильным путем.")
else:
    # Читаем текущий .env
    with open(env_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Ищем строки с путем и обновляем их
    found = False
    new_lines = []
    for line in lines:
        if line.strip().startswith("VAULT_PATH=") or line.strip().startswith("OBSIDIAN_PATH=") or line.strip().startswith("BASE_DIR="):
            new_lines.append(f"{line.split('=')[0]}={correct_path}\n")
            found = True
        else:
            new_lines.append(line)
    
    # Если переменной не было, добавляем её
    if not found:
        new_lines.append(f"\nVAULT_PATH={correct_path}\n")
    
    # Записываем обратно
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print(f"УСПЕХ: Путь к Vault в файле .env обновлен на: {correct_path}")

print("\nВАЖНО: Теперь необходимо ПЕРЕЗАПУСТИТЬ сервер FastAPI (main.py),")
print("чтобы он прочитал обновленный файл .env.")
print("--- КОНЕЦ ИСПРАВЛЕНИЯ ---")