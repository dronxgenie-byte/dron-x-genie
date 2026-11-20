"""
Модуль инструментов кодера для Дрона: выполнение команд, работа с файлами.
Безопасность: все операции ограничены корневой папкой проекта.
"""
import os
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _safe_path(path_str: str) -> str:
    safe = (BASE_DIR / path_str).resolve()
    if not str(safe).startswith(str(BASE_DIR)):
        return None
    return str(safe)


def run_command(command: str, timeout: int = 60) -> str:
    """Выполняет shell-команду в безопасной директории проекта."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        output = ""
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
        output += f"ВЫХОДНОЙ КОД: {result.returncode}"
        return output.strip()
    except subprocess.TimeoutExpired:
        return f"ОШИБКА: команда превысила лимит времени ({timeout} сек)"
    except Exception as e:
        return f"ОШИБКА выполнения: {str(e)}"


def create_file(path_str: str, content: str) -> str:
    """Создаёт или перезаписывает файл в директории проекта."""
    path = _safe_path(path_str)
    if not path:
        return "ОШИБКА БЕЗОПАСНОСТИ: путь вне проекта"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Файл создан: {path_str}"
    except Exception as e:
        return f"ОШИБКА создания файла: {str(e)}"


def read_file(path_str: str) -> str:
    """Читает файл из директории проекта."""
    path = _safe_path(path_str)
    if not path:
        return "ОШИБКА БЕЗОПАСНОСТИ: путь вне проекта"
    if not os.path.exists(path):
        return f"ОШИБКА: файл не найден: {path_str}"
    try:
        return open(path, "r", encoding="utf-8").read()
    except Exception as e:
        return f"ОШИБКА чтения: {str(e)}"


def edit_file(path_str: str, old_string: str, new_string: str) -> str:
    """Заменяет старую строку на новую в файле."""
    path = _safe_path(path_str)
    if not path:
        return "ОШИБКА БЕЗОПАСНОСТИ: путь вне проекта"
    if not os.path.exists(path):
        return f"ОШИБКА: файл не найден: {path_str}"
    try:
        content = open(path, "r", encoding="utf-8").read()
        if old_string not in content:
            return f"ОШИБКА: строка не найдена в файле {path_str}"
        new_content = content.replace(old_string, new_string, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return f"Файл отредактирован: {path_str}"
    except Exception as e:
        return f"ОШИБКА редактирования: {str(e)}"


def list_files(path_str: str = ".") -> str:
    """Список файлов в директории проекта."""
    path = _safe_path(path_str)
    if not path:
        return "ОШИБКА БЕЗОПАСНОСТИ: путь вне проекта"
    if not os.path.isdir(path):
        return f"ОШИБКА: не директория: {path_str}"
    try:
        entries = os.listdir(path)
        return "\n".join(sorted(entries))
    except Exception as e:
        return f"ОШИБКА списка: {str(e)}"


CODER_TOOLS = {
    "run_command": run_command,
    "create_file": create_file,
    "read_file": read_file,
    "edit_file": edit_file,
    "list_files": list_files,
}
