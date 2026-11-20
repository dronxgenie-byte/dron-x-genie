import re

from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
files = [
    str(_PROJECT_ROOT / "backend" / "agents.py"),
    str(_PROJECT_ROOT / "backend" / "dron.py")
]

target_model = "gemma-4-e4b-agentic-sol-fable-reasoning-geminicli"

for filepath in files:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if "agents.py" in filepath:
            content = re.sub(r'MODEL\s*=\s*".*?"', f'MODEL = "{target_model}"', content)
        
        if "dron.py" in filepath:
            content = re.sub(r'self\.fast_model\s*=\s*".*?"', f'self.fast_model = "{target_model}"', content)
            content = re.sub(r'self\.main_model\s*=\s*".*?"', f'self.main_model = "{target_model}"', content)
            
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"УСПЕХ: Модель обновлена в {filepath}")
    except Exception as e:
        print(f"ОШИБКА в {filepath}: {e}")
