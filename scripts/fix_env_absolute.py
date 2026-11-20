import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
env_file = str(_PROJECT_ROOT / "backend" / ".env")
correct_path = str(_PROJECT_ROOT.parent / "DRON_X_GENIE")

print(f"--- ЗАПИСЬ ПУТИ В {env_file} ---")

if not os.path.exists(env_file):
    print(f"ОШИБКА: Файл {env_file} не найден.")
else:
    with open(env_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    path_vars = ["VAULT_PATH", "OBSIDIAN_PATH", "BASE_DIR", "VAULT_DIR"]
    new_lines = []
    updated = False
    
    for line in lines:
        stripped = line.strip()
        is_path_var = any(stripped.startswith(var + "=") for var in path_vars)
        
        if is_path_var:
            var_name = stripped.split("=")[0]
            new_lines.append(f"{var_name}={correct_path}\n")
            updated = True
            print(f"Обновлено: {var_name}={correct_path}")
        else:
            new_lines.append(line)
    
    if not updated:
        new_lines.append(f"\nVAULT_PATH={correct_path}\n")
        print(f"Добавлено: VAULT_PATH={correct_path}")
    
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
        
print("--- ГОТОВО ---")
