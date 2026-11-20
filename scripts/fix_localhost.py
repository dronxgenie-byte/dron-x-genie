from pathlib import Path
filepath = str(Path(__file__).resolve().parent.parent / "backend" / "dron.py")
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("http://localhost:1234", "http://127.0.0.1:1234")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
    
print("УСПЕХ: localhost заменен на 127.0.0.1 в dron.py")
