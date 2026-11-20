from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
env_file = str(_PROJECT_ROOT / "backend" / ".env")
correct_path = str(_PROJECT_ROOT.parent / "DRON_X_GENIE")

correct_path_obj = Path(correct_path)
print(f"Проверяю наличие Vault: {correct_path}")
if not correct_path_obj.exists():
    print(f"ОШИБКА: Папка {correct_path} не существует.")
    print("Проверь точное имя папки с памятью.")
else:
    print(f"Vault найден. Содержимое:")
    for item in list(correct_path_obj.iterdir())[:10]:
        print(f"  - {item.name}")
    
    env_file_path = Path(env_file)
    if env_file_path.exists():
        with open(env_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        new_lines = []
        for line in lines:
            if any(line.strip().startswith(p) for p in ["VAULT_PATH=", "OBSIDIAN_PATH=", "BASE_DIR=", "VAULT_DIR="]):
                new_lines.append(f"{line.split('=')[0]}={correct_path}\n")
            else:
                new_lines.append(line)
        
        with open(env_file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        print(f"\nПуть в {env_file} обновлен на: {correct_path}")
    else:
        print(f"Файл {env_file} не найден.")

print("\nПерезапусти сервер: cd backend && python main.py")