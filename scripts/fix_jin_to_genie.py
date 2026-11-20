from pathlib import Path
import glob

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
for filepath in glob.glob(str(_PROJECT_ROOT / "backend" / "*.py")):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Заменяем неверное название на правильное
    content = content.replace("'jin'", "'genie'")
    content = content.replace('"jin"', '"genie"')
    content = content.replace("или 'jin'", "или 'genie'")
    content = content.replace("или \"jin\"", "или \"genie\"")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
        
print("ГОТОВО: 'jin' заменен на 'genie' в файлах бэкенда.")
