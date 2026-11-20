"""
NOD API Key Vault — зашифрованное хранилище ключей.

Все ключи хранятся в зашифрованном виде в файле backend/data/nod_vault.json.
Мастер-ключ берется из переменной окружения NOD_VAULT_PASSWORD
или из файла backend/data/.vault_password.

Если библиотека cryptography недоступна — используется простой XOR-шифр
с ключом, производным от мастер-пароля (не криптостойко, но защищает от
случайного просмотра).
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

VAULT_DIR = Path(__file__).resolve().parent / "data"
VAULT_FILE = VAULT_DIR / "nod_vault.json"
PASSWORD_FILE = VAULT_DIR / ".vault_password"


def _get_master_key() -> bytes:
    """Получить мастер-ключ для шифрования."""
    password = os.getenv("NOD_VAULT_PASSWORD")
    if not password and PASSWORD_FILE.exists():
        password = PASSWORD_FILE.read_text(encoding="utf-8").strip()
    if not password:
        # Генерация пароля по умолчанию на основе machine-id / hostname
        import uuid as _uuid
        import socket as _socket
        password = f"{_socket.gethostname()}:{_uuid.getnode()}"
        # Сохраняем, чтобы не менялся при перезапуске
        try:
            PASSWORD_FILE.parent.mkdir(parents=True, exist_ok=True)
            PASSWORD_FILE.write_text(password, encoding="utf-8")
        except OSError:
            pass
    # Производный ключ (SHA256 через hashlib)
    import hashlib as _hashlib
    return _hashlib.sha256(password.encode("utf-8")).digest()


def _xor_crypt(data: bytes, key: bytes) -> bytes:
    """Простой XOR-шифр (обфускация, не криптография)."""
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def _try_cryptography() -> Any:
    """Попробовать импортировать cryptography.Fernet."""
    try:
        from cryptography.fernet import Fernet  # type: ignore
        return Fernet
    except ImportError:
        return None


def encrypt_value(plaintext: str) -> str:
    """Зашифровать строку. Возвращает base64-строку."""
    data = plaintext.encode("utf-8")
    key = _get_master_key()
    fernet_cls = _try_cryptography()
    if fernet_cls is not None:
        fernet = fernet_cls(base64.urlsafe_b64encode(key))
        return fernet.encrypt(data).decode("utf-8")
    # Fallback: XOR + base64
    encrypted = _xor_crypt(data, key)
    return base64.b64encode(encrypted).decode("utf-8")


def decrypt_value(ciphertext_b64: str) -> str:
    """Расшифровать строку из base64."""
    key = _get_master_key()
    fernet_cls = _try_cryptography()
    if fernet_cls is not None:
        try:
            fernet = fernet_cls(base64.urlsafe_b64encode(key))
            return fernet.decrypt(ciphertext_b64.encode("utf-8")).decode("utf-8")
        except Exception:
            # Fernet не расшифровал — пробуем XOR fallback
            pass
    # Fallback: XOR + base64. Пробуем стандартный b64decode, затем urlsafe.
    for decode_fn in (base64.b64decode, base64.urlsafe_b64decode):
        try:
            data = decode_fn(ciphertext_b64)
            break
        except Exception:
            continue
    else:
        # Последняя попытка: добавить padding
        data = base64.urlsafe_b64decode(ciphertext_b64 + "==")
    decrypted = _xor_crypt(data, key)
    return decrypted.decode("utf-8")


# ---------------------------------------------------------------
# Работа с vault файлом
# ---------------------------------------------------------------

def _load_vault() -> dict[str, Any]:
    if not VAULT_FILE.exists():
        return {"keys": {}}
    try:
        return json.loads(VAULT_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"keys": {}}


def _save_vault(data: dict[str, Any]) -> None:
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    VAULT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def store_key(key_id: str, plaintext_key: str) -> None:
    """Сохранить зашифрованный ключ по его идентификатору."""
    vault = _load_vault()
    vault["keys"][key_id] = {
        "encrypted": encrypt_value(plaintext_key),
        "updated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }
    _save_vault(vault)


def get_key(key_id: str) -> str | None:
    """Получить расшифрованный ключ по идентификатору."""
    vault = _load_vault()
    entry = vault.get("keys", {}).get(key_id)
    if not entry:
        return None
    return decrypt_value(entry["encrypted"])


def delete_key(key_id: str) -> bool:
    """Удалить ключ из vault."""
    vault = _load_vault()
    if key_id in vault.get("keys", {}):
        del vault["keys"][key_id]
        _save_vault(vault)
        return True
    return False


def list_key_ids() -> list[str]:
    vault = _load_vault()
    return list(vault.get("keys", {}).keys())


# ---------------------------------------------------------------
# API Token для доступа к HTTP API монитора
# ---------------------------------------------------------------

import secrets as _secrets


def generate_api_token(length: int = 32) -> str:
    """Сгенерировать случайный API токен."""
    return _secrets.token_urlsafe(length)


def store_api_token(token: str) -> None:
    """Сохранить API токен в Vault под ключом 'nod_api_token'."""
    store_key("nod_api_token", token)


def get_api_token() -> str | None:
    """Получить API токен из Vault."""
    return get_key("nod_api_token")


def ensure_api_token() -> str:
    """Получить существующий токен или создать новый и сохранить."""
    token = get_api_token()
    if token is None:
        token = generate_api_token()
        store_api_token(token)
        print(f"[NOD] Сгенерирован новый API токен: {token}")
        print(f"[NOD] Сохранён в Vault. Используйте заголовок X-NOD-Token для доступа к API.")
    return token


def verify_api_token(token: str | None) -> bool:
    """Проверить валидность API токена."""
    if token is None:
        return False
    stored = get_api_token()
    if stored is None:
        return False
    return _secrets.compare_digest(token, stored)
