from fastapi import APIRouter, HTTPException
import os
import glob

router = APIRouter()

@router.get("/diary")
def get_latest_diary():
    try:
        # Ищем папку 01_INBOX в корне проекта или в папке vault
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        possible_paths = [
            os.path.join(base_dir, "vault", "01_INBOX"),
            os.path.join(base_dir, "01_INBOX"),
            os.path.join(base_dir, "vault")
        ]
        
        vault_path = None
        for p in possible_paths:
            if os.path.exists(p):
                vault_path = p
                break
                
        if not vault_path:
            return {"content": "Папка 01_INBOX не найдена. Проверьте путь к Vault."}
            
        # Ищем все md-файлы
        files = glob.glob(os.path.join(vault_path, "**", "*.md"), recursive=True)
        if not files:
            return {"content": f"В папке {vault_path} нет файлов .md"}
        
        # Берем самый свежий файл
        latest_file = max(files, key=os.path.getmtime)
        
        with open(latest_file, "r", encoding="utf-8") as f:
            content = f.read()
            
        return {
            "filename": os.path.basename(latest_file),
            "content": content
        }
    except Exception as e:
        return {"content": f"Ошибка чтения: {str(e)}"}
