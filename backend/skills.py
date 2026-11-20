"""
Модуль навыков для Дрона: read_vault, write_log, write_audit, read_audit.
Безопасность: read_vault не выходит за пределы Vault, write_* только дописывают.
"""
import os
from pathlib import Path
from datetime import datetime

# Пути
VAULT_PATH = Path(__file__).resolve().parents[1].parent / "DRON_X_GENIE"
JOURNAL_PATH = VAULT_PATH / "00_SYSTEM" / "journal.md"
AUDIT_PATH = VAULT_PATH / "00_SYSTEM" / "audit_log.md"

def read_vault(relative_path: str) -> str:
    """Читает файл из Obsidian Vault. Проверяет безопасность пути."""
    safe_path = (VAULT_PATH / relative_path).resolve()
    
    if not str(safe_path).startswith(str(VAULT_PATH.resolve())):
        return "ОШИБКА БЕЗОПАСНОСТИ: путь выходит за пределы хранилища"
    
    if not safe_path.exists():
        return f"ОШИБКА: файл не найден: {relative_path}"
    
    if not safe_path.is_file():
        return f"ОШИБКА: это не файл: {relative_path}"
    
    try:
        content = safe_path.read_text(encoding="utf-8")
        return content
    except Exception as e:
        return f"ОШИБКА чтения: {str(e)}"

def write_log(text: str) -> str:
    """Дописывает текст в журнал с временной меткой."""
    JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    if not JOURNAL_PATH.exists():
        JOURNAL_PATH.write_text("# Журнал DRON X GENIE\n\n", encoding="utf-8")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"\n## [{timestamp}]\n{text}\n"
    
    try:
        with open(JOURNAL_PATH, "a", encoding="utf-8") as f:
            f.write(entry)
        return f"Запись добавлена в журнал: {JOURNAL_PATH}"
    except Exception as e:
        return f"ОШИБКА записи: {str(e)}"

def write_audit(text: str) -> str:
    """Дописывает аудит в отдельный файл audit_log.md."""
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    if not AUDIT_PATH.exists():
        AUDIT_PATH.write_text("# Аудит DRON X GENIE\n\n", encoding="utf-8")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"\n## [{timestamp}]\n{text}\n"
    
    try:
        with open(AUDIT_PATH, "a", encoding="utf-8") as f:
            f.write(entry)
        return f"Аудит записан: {AUDIT_PATH}"
    except Exception as e:
        return f"ОШИБКА записи аудита: {str(e)}"

def read_audit() -> str:
    """Читает последние записи из audit_log.md."""
    if not AUDIT_PATH.exists():
        return "НЕТ ДАННЫХ: файл аудита пуст или не создан."
    
    try:
        content = AUDIT_PATH.read_text(encoding="utf-8")
        lines = content.split('\n')
        # Берём последние 50 строк (примерно 3-5 последних записей)
        return '\n'.join(lines[-50:])
    except Exception as e:
        return f"ОШИБКА чтения аудита: {str(e)}"