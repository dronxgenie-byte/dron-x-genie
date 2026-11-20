"""Модуль связи: звонки и сообщения из ANANISIM OS.

Каналы:
- `phone`  — звонок/СМС с сопряжённого телефона через ADB (USB или Wi-Fi отладка).
- `telegram` — Telegram Bot API (нужен токен бота и chat_id).
- `max`    — MAX Bot API (мессенджер MAX, нужен токен и chat_id).
- `whatsapp` — Cloud API (официально) или локальный bridge (Node + whatsapp-web.js).

Безопасность: по умолчанию `COMMS_DRY_RUN=1` — команды только проверяются и
пишутся в журнал, ничего не отправляется и никто не звонит. Реальная отправка
включается явно: `COMMS_DRY_RUN=0` в `.env`.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "data" / "logs"
COMMS_LOG = LOG_DIR / "comms.log"

TELEGRAM_API = "https://api.telegram.org"
MAX_API = "https://botapi.max.ru"
WHATSAPP_GRAPH = "https://graph.facebook.com/v20.0"

READY = "ready"
UNCONFIGURED = "unconfigured"
UNAVAILABLE = "unavailable"


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def dry_run() -> bool:
    return _env("COMMS_DRY_RUN", "1") not in {"0", "false", "False", "no"}


def _log(entry: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    entry = {"ts": datetime.now().isoformat(timespec="seconds"), **entry}
    with COMMS_LOG.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(entry, ensure_ascii=False) + "\n")


def normalize_phone(value: str) -> str:
    """Оставить только цифры и ведущий +, чтобы не улетело в чужой номер."""
    digits = re.sub(r"[^\d+]", "", (value or "").strip())
    if digits.startswith("8") and len(digits) == 11:
        digits = "+7" + digits[1:]
    elif digits.startswith("7") and len(digits) == 11 and not digits.startswith("+"):
        digits = "+" + digits
    return digits


def adb_path() -> str | None:
    candidate = _env("ADB_PATH", "adb")
    found = shutil.which(candidate)
    return found or (candidate if Path(candidate).is_file() else None)


def _adb_devices() -> list[str]:
    adb = adb_path()
    if not adb:
        return []
    try:
        result = subprocess.run(
            [adb, "devices"], capture_output=True, text=True, timeout=10, check=False
        )
    except Exception:
        return []
    devices = []
    for line in result.stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
    return devices


def phone_status() -> dict:
    adb = adb_path()
    if not adb:
        return {
            "status": UNCONFIGURED,
            "reason": "ADB не найден: установите platform-tools или пропишите ADB_PATH",
        }
    devices = _adb_devices()
    if not devices:
        return {
            "status": UNAVAILABLE,
            "reason": "Телефон не подключён: включите отладку по USB или беспроводную отладку",
            "adb": adb,
        }
    return {"status": READY, "device": devices[0], "adb": adb}


def telegram_status() -> dict:
    token = _env("TELEGRAM_BOT_TOKEN")
    chat = _env("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return {
            "status": UNCONFIGURED,
            "reason": "Нужны TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID в .env",
        }
    return {"status": READY, "chat_id": chat}


def max_status() -> dict:
    token = _env("MAX_BOT_TOKEN")
    chat = _env("MAX_CHAT_ID")
    if not token or not chat:
        return {"status": UNCONFIGURED, "reason": "Нужны MAX_BOT_TOKEN и MAX_CHAT_ID в .env"}
    return {"status": READY, "chat_id": chat}


def whatsapp_status() -> dict:
    provider = _env("WHATSAPP_PROVIDER", "").lower()

    if provider == "bridge":
        url = _env("WHATSAPP_BRIDGE_URL", "http://127.0.0.1:3100")
        return {"status": READY, "provider": "bridge", "url": url}

    token = _env("WHATSAPP_TOKEN")
    phone_id = _env("WHATSAPP_PHONE_ID")
    if not token or not phone_id:
        return {
            "status": UNCONFIGURED,
            "reason": (
                "Либо WHATSAPP_PROVIDER=bridge (локальный Node-мост), "
                "либо WHATSAPP_TOKEN и WHATSAPP_PHONE_ID для Cloud API"
            ),
        }
    return {"status": READY, "provider": "cloud", "phone_id": phone_id}


def status() -> dict:
    return {
        "dry_run": dry_run(),
        "channels": {
            "phone": phone_status(),
            "telegram": telegram_status(),
            "max": max_status(),
            "whatsapp": whatsapp_status(),
        },
    }


# ------------------------------------------------------------------ звонки


async def call(number: str, *, reason: str | None = None) -> dict:
    """Позвонить с сопряжённого телефона через ADB."""
    phone = normalize_phone(number)
    if len(phone) < 6:
        return {"ok": False, "error": "Некорректный номер"}

    state = phone_status()
    if state["status"] != READY:
        return {"ok": False, "error": state["reason"], "channel": "phone"}

    command = [
        state["adb"],
        "-s",
        state["device"],
        "shell",
        "am",
        "start",
        "-a",
        "android.intent.action.CALL",
        "-d",
        f"tel:{phone}",
    ]

    if dry_run():
        _log({"channel": "phone", "action": "call", "to": phone, "dry_run": True, "reason": reason})
        return {"ok": True, "dry_run": True, "channel": "phone", "action": "call", "to": phone}

    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=25, check=False)
    except Exception as exc:  # noqa: BLE001
        _log({"channel": "phone", "action": "call", "to": phone, "error": str(exc)})
        return {"ok": False, "error": f"ADB не смог позвонить: {exc}", "channel": "phone"}

    ok = result.returncode == 0
    _log(
        {
            "channel": "phone",
            "action": "call",
            "to": phone,
            "ok": ok,
            "stderr": (result.stderr or "")[:400],
        }
    )
    if not ok:
        return {
            "ok": False,
            "error": (result.stderr or "телефон отклонил команду").strip()[:400],
            "channel": "phone",
        }
    return {"ok": True, "channel": "phone", "action": "call", "to": phone}


# --------------------------------------------------------------- сообщения


async def send(channel: str, to: str, text: str) -> dict:
    """Отправить сообщение в выбранный канал."""
    channel = (channel or "").lower().strip()
    text = (text or "").strip()
    if not text:
        return {"ok": False, "error": "Пустое сообщение"}
    if len(text) > 4000:
        return {"ok": False, "error": "Слишком длинное сообщение (максимум 4000)"}

    handlers = {
        "telegram": _send_telegram,
        "max": _send_max,
        "whatsapp": _send_whatsapp,
        "phone": _send_sms,
    }
    handler = handlers.get(channel)
    if not handler:
        return {
            "ok": False,
            "error": f"Неизвестный канал «{channel}». Есть: telegram, max, whatsapp, phone (СМС)",
        }
    return await handler(to, text)


async def _send_telegram(to: str, text: str) -> dict:
    state = telegram_status()
    if state["status"] != READY:
        return {"ok": False, "error": state["reason"], "channel": "telegram"}

    payload = {"chat_id": to or state["chat_id"], "text": text}
    if dry_run():
        _log({"channel": "telegram", "action": "send", "dry_run": True, **payload})
        return {"ok": True, "dry_run": True, "channel": "telegram", "to": payload["chat_id"]}

    token = _env("TELEGRAM_BOT_TOKEN")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{TELEGRAM_API}/bot{token}/sendMessage", json=payload)
        data = response.json()
    except Exception as exc:  # noqa: BLE001
        _log({"channel": "telegram", "action": "send", "error": str(exc)})
        return {"ok": False, "error": f"Telegram недоступен: {exc}", "channel": "telegram"}

    ok = bool(data.get("ok"))
    _log({"channel": "telegram", "action": "send", "ok": ok, "to": payload["chat_id"]})
    if not ok:
        return {
            "ok": False,
            "error": str(data.get("description") or "Telegram отказал")[:300],
            "channel": "telegram",
        }
    return {"ok": True, "channel": "telegram", "to": payload["chat_id"]}


async def _send_max(to: str, text: str) -> dict:
    state = max_status()
    if state["status"] != READY:
        return {"ok": False, "error": state["reason"], "channel": "max"}

    chat_id = to or state["chat_id"]
    if dry_run():
        _log({"channel": "max", "action": "send", "dry_run": True, "to": chat_id, "text": text})
        return {"ok": True, "dry_run": True, "channel": "max", "to": chat_id}

    token = _env("MAX_BOT_TOKEN")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{MAX_API}/messages",
                params={"access_token": token, "chat_id": chat_id},
                json={"text": text},
            )
        data = response.json()
    except Exception as exc:  # noqa: BLE001
        _log({"channel": "max", "action": "send", "error": str(exc)})
        return {"ok": False, "error": f"MAX недоступен: {exc}", "channel": "max"}

    ok = response.status_code < 400
    _log({"channel": "max", "action": "send", "ok": ok, "to": chat_id})
    if not ok:
        return {
            "ok": False,
            "error": str(data)[:300],
            "channel": "max",
        }
    return {"ok": True, "channel": "max", "to": chat_id}


async def _send_whatsapp(to: str, text: str) -> dict:
    state = whatsapp_status()
    if state["status"] != READY:
        return {"ok": False, "error": state["reason"], "channel": "whatsapp"}
    if not to:
        return {"ok": False, "error": "Нужен номер получателя", "channel": "whatsapp"}

    number = normalize_phone(to).lstrip("+")

    if dry_run():
        _log({"channel": "whatsapp", "action": "send", "dry_run": True, "to": number, "text": text})
        return {"ok": True, "dry_run": True, "channel": "whatsapp", "to": number}

    if state["provider"] == "bridge":
        url = state["url"].rstrip("/") + "/send"
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json={"to": number, "text": text})
            ok = response.status_code < 400
            _log({"channel": "whatsapp", "action": "send", "ok": ok, "to": number, "provider": "bridge"})
            if not ok:
                return {"ok": False, "error": response.text[:300], "channel": "whatsapp"}
            return {"ok": True, "channel": "whatsapp", "to": number, "provider": "bridge"}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"Мост WhatsApp недоступен: {exc}", "channel": "whatsapp"}

    token = _env("WHATSAPP_TOKEN")
    phone_id = state["phone_id"]
    body = {
        "messaging_product": "whatsapp",
        "to": number,
        "type": "text",
        "text": {"body": text},
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{WHATSAPP_GRAPH}/{phone_id}/messages",
                headers={"Authorization": f"Bearer {token}"},
                json=body,
            )
        data = response.json()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"WhatsApp недоступен: {exc}", "channel": "whatsapp"}

    ok = response.status_code < 400
    _log({"channel": "whatsapp", "action": "send", "ok": ok, "to": number, "provider": "cloud"})
    if not ok:
        return {"ok": False, "error": str(data)[:300], "channel": "whatsapp"}
    return {"ok": True, "channel": "whatsapp", "to": number, "provider": "cloud"}


async def _send_sms(to: str, text: str) -> dict:
    """СМС с телефона через ADB."""
    phone = normalize_phone(to)
    state = phone_status()
    if state["status"] != READY:
        return {"ok": False, "error": state["reason"], "channel": "phone"}

    command = [
        state["adb"],
        "-s",
        state["device"],
        "shell",
        "am",
        "start",
        "-a",
        "android.intent.action.SENDTO",
        "-d",
        f"sms:{phone}",
        "--es",
        "sms_body",
        text,
    ]

    if dry_run():
        _log({"channel": "phone", "action": "sms", "dry_run": True, "to": phone})
        return {"ok": True, "dry_run": True, "channel": "phone", "action": "sms", "to": phone}

    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=25, check=False)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"ADB не смог отправить СМС: {exc}", "channel": "phone"}

    ok = result.returncode == 0
    _log({"channel": "phone", "action": "sms", "to": phone, "ok": ok})
    if not ok:
        return {"ok": False, "error": (result.stderr or "").strip()[:300], "channel": "phone"}
    return {"ok": True, "channel": "phone", "action": "sms", "to": phone}


def log_tail(limit: int = 20) -> list[dict]:
    if not COMMS_LOG.is_file():
        return []
    lines = COMMS_LOG.read_text(encoding="utf-8").splitlines()[-limit:]
    entries = []
    for line in lines:
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


# --------------------------------------------------- команды человеческим языком

CALL_RE = re.compile(
    r"(?:позвони|позвонил|позвонила|позвонить|набери|звони)\s+"
    r"(?:на\s+|к\s+)?(?P<who>[^\s,.;!?]{2,40})",
    re.IGNORECASE,
)
SEND_RE = re.compile(
    r"^\s*(?:напиши|отправь|сообщи|скинь)\s+"
    r"(?:(?:в|во)\s+)?(?P<channel>телеграм\w*|тг|макс|max|ватсап\w*|whatsapp|смс|sms)\s+"
    r"(?P<rest>.+)$",
    re.IGNORECASE,
)

CHANNEL_ALIASES = {
    "телеграм": "telegram",
    "телеграмма": "telegram",
    "телеграмме": "telegram",
    "тг": "telegram",
    "макс": "max",
    "max": "max",
    "ватсап": "whatsapp",
    "ватсапп": "whatsapp",
    "whatsapp": "whatsapp",
    "смс": "phone",
    "sms": "phone",
}


def parse_command(message: str) -> dict | None:
    """Распознать команду связи в любой фразе — даже с ошибкой распознавания."""
    source = fix_speech(message)
    text = (source or "").strip()
    if not text:
        return None

    text = re.sub(
        r"^\s*(?:дрон|джинни|джин|босс)\s*[,!.…:;—–-]*\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    match = CALL_RE.search(text)
    if match:
        who = match.group("who").strip(" ,.!?")
        if re.fullmatch(r"[+\d][\d\s\-()]{4,}", who):
            return {"action": "call", "number": normalize_phone(who)}

        contact = resolve_contact(who)
        if contact:
            return {
                "action": "call",
                "number": normalize_phone(contact["value"]),
                "contact": contact["name"],
            }
        return {
            "action": "unknown_contact",
            "name": who,
            "contacts": sorted(load_contacts()),
        }

    match = SEND_RE.search(text)
    if match:
        raw_channel = match.group("channel").lower()
        channel = CHANNEL_ALIASES.get(raw_channel, raw_channel)
        rest = match.group("rest").strip()

        to = ""
        body = rest
        if ":" in rest:
            head, tail = rest.split(":", 1)
            if re.fullmatch(r"[\w@.\-+]{2,64}", head.strip()):
                to = head.strip()
                body = tail.strip()
        else:
            first, _, tail = rest.partition(" ")
            contact = resolve_contact(first)
            if contact:
                to = contact["value"]
                body = tail.strip() or rest

        return {"action": "send", "channel": channel, "to": to, "text": body}

    return None


async def run_command(command: dict) -> dict:
    """Выполнить распознанную команду связи."""
    if command.get("action") == "unknown_contact":
        known = ", ".join(command.get("contacts") or []) or "пока никого"
        name = command.get("name")
        return {
            "ok": False,
            "error": (
                "Не знаю номера для «" + str(name) + "». "
                "Добавьте контакт в настройках. Известные: " + known
            ),
        }

    if command.get("action") == "call":
        return await call(command.get("number", ""), reason="команда Дрону")
    if command.get("action") == "send":
        return await send(command.get("channel", ""), command.get("to", ""), command.get("text", ""))
    return {"ok": False, "error": "Непонятная команда связи"}


# ------------------------------------------------------------- контакты

CONTACTS_FILE = ROOT / "data" / "contacts.json"

ASR_ALIASES = {
    "зрон": "дрон",
    "дронн": "дрон",
    "джин": "джинни",
    "джини": "джинни",
}


def fix_speech(text: str) -> str:
    """Поправить типичные ошибки распознавания речи."""
    words = (text or "").split()
    fixed = []
    for word in words:
        clean = word.strip(",.!?;:—-").lower()
        replacement = ASR_ALIASES.get(clean)
        if replacement:
            word = word.lower().replace(clean, replacement, 1)
        fixed.append(word)
    return " ".join(fixed)


def load_contacts() -> dict:
    if not CONTACTS_FILE.is_file():
        return {}
    try:
        data = json.loads(CONTACTS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def save_contact(name: str, value: str, channel: str = "phone") -> dict:
    key = (name or "").strip().lower()
    if not key or not value:
        return {"ok": False, "error": "Нужны имя и номер/chat_id"}
    contacts = load_contacts()
    contacts[key] = {"value": value.strip(), "channel": channel}
    CONTACTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONTACTS_FILE.write_text(
        json.dumps(contacts, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"ok": True, "name": key, "contact": contacts[key], "total": len(contacts)}


def delete_contact(name: str) -> dict:
    key = (name or "").strip().lower()
    contacts = load_contacts()
    if key not in contacts:
        return {"ok": False, "error": "Такого контакта нет"}
    contacts.pop(key)
    CONTACTS_FILE.write_text(
        json.dumps(contacts, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"ok": True, "removed": key}


def resolve_contact(name: str) -> dict | None:
    """Найти контакт по имени: «мама», «маме», «Ване».С"""
    raw = (name or "").strip().lower()
    if not raw:
        return None
    contacts = load_contacts()
    if raw in contacts:
        return {"name": raw, **contacts[raw]}

    for suffix in ("е", "у", "а", "я", "ой", "ей", "ам", "ом"):
        if raw.endswith(suffix) and len(raw) > len(suffix):
            stem = raw[: -len(suffix)]
            for candidate, info in contacts.items():
                if candidate == stem or candidate.startswith(stem):
                    return {"name": candidate, **info}
    for candidate, info in contacts.items():
        if candidate.startswith(raw) or raw.startswith(candidate):
            return {"name": candidate, **info}
    return None

# ------------------------------------------------- Phone Link (Связь с телефоном)
# Официального API у Phone Link нет, поэтому управляем окном через UI Automation.
# Скрипт backend/agent/phone_link.ps1 умеет: status, open, call.

POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")
PHONE_SCRIPT = ROOT / "backend" / "agent" / "phone_link.ps1"


def _phonelink(action: str = "status", number: str = "", text: str = "") -> dict:
    """Вызвать UI Automation скрипт Phone Link и вернуть его JSON."""
    if not POWERSHELL:
        return {"ok": False, "error": "PowerShell не найден"}
    if not PHONE_SCRIPT.is_file():
        return {"ok": False, "error": "phone_link.ps1 не найден"}

    command = [
        POWERSHELL,
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(PHONE_SCRIPT),
        "-Action",
        action,
    ]
    if number:
        command += ["-Number", number]
    if text:
        command += ["-Text", text]

    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace"
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"UI Automation упал: {exc}"}

    output = ((result.stdout or "").strip().splitlines() or [""])[-1]
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {
            "ok": False,
            "error": f"Не разобрал ответ Phone Link: {output[:200]} {result.stderr[:200]}",
        }


def _phonelink_backend() -> str:
    return _env("PHONE_CALL_BACKEND", "auto").lower()


def phone_status() -> dict:
    backend = _phonelink_backend()

    if backend in {"auto", "phonelink"}:
        state = _phonelink("status")
        if state.get("state") == "ready":
            return {
                "status": READY,
                "backend": "phonelink",
                "device": state.get("device") or "телефон",
                "reason": "",
            }
        if backend == "phonelink":
            return {
                "status": UNAVAILABLE,
                "backend": "phonelink",
                "reason": state.get("error") or "Phone Link не готов",
                "hint": state.get("hint", ""),
            }

    adb = adb_path()
    if backend in {"auto", "adb"}:
        if adb:
            devices = _adb_devices()
            if devices:
                return {"status": READY, "backend": "adb", "device": devices[0], "adb": adb}
            link = _phonelink("status") if backend == "auto" else {}
            link_error = link.get("error") or ""
            reason = "Телефон не подключён по ADB: включите отладку по USB или беспроводную отладку"
            if link_error:
                reason = "Phone Link: " + link_error + ". Кроме того, " + reason.lower()
            return {
                "status": UNAVAILABLE,
                "backend": "adb",
                "reason": reason,
                "adb": adb,
            }

    if backend == "auto":
        link = _phonelink("status")
        adb_hint = "ADB не подключён: включите отладку по USB и подключите кабелем"
        reason = (link.get("error") or "Phone Link не готов") + ". " + adb_hint
        return {
            "status": UNAVAILABLE,
            "reason": reason,
            "hint": link.get("hint", ""),
            "backends": {"phonelink": link.get("state"), "adb": "no devices"},
        }

    return {"status": UNCONFIGURED, "reason": "ADB не найден: установите platform-tools или ADB_PATH"}


async def call(number: str, *, reason: str | None = None) -> dict:
    """Позвонить: сначала Phone Link, затем ADB."""
    phone = normalize_phone(number)
    if len(phone) < 6:
        return {"ok": False, "error": "Некорректный номер", "channel": "phone"}

    backend = _phonelink_backend()
    state = phone_status()

    if state.get("status") != READY:
        return {
            "ok": False,
            "channel": "phone",
            "error": state.get("reason") or "Телефон не готов",
            "hint": state.get("hint", ""),
        }

    if state.get("backend") == "phonelink":
        if dry_run():
            _log({"channel": "phone", "action": "call", "to": phone, "dry_run": True, "backend": "phonelink"})
            return {
                "ok": True,
                "dry_run": True,
                "channel": "phone",
                "to": phone,
                "backend": "phonelink",
                "device": state.get("device"),
            }
        result = _phonelink("call", phone)
        _log({"channel": "phone", "action": "call", "to": phone, "backend": "phonelink", "ok": result.get("ok")})
        if result.get("ok"):
            return {"ok": True, "channel": "phone", "to": phone, "backend": "phonelink"}
        return {
            "ok": False,
            "channel": "phone",
            "error": result.get("error") or "Phone Link отказал",
        }

    if backend == "phonelink":
        return {"ok": False, "channel": "phone", "error": "Phone Link выбран, но не готов"}

    return await _call_adb(phone, reason)


async def _call_adb(phone: str, reason: str | None = None) -> dict:
    """Позвонить через ADB, если Phone Link недоступен."""
    state = phone_status()
    if state.get("backend") != "adb" or state.get("status") != READY:
        return {"ok": False, "channel": "phone", "error": state.get("reason") or "ADB не готов"}

    command = [
        state["adb"],
        "-s",
        state["device"],
        "shell",
        "am",
        "start",
        "-a",
        "android.intent.action.CALL",
        "-d",
        f"tel:{phone}",
    ]

    if dry_run():
        _log({"channel": "phone", "action": "call", "to": phone, "dry_run": True, "backend": "adb"})
        return {"ok": True, "dry_run": True, "channel": "phone", "action": "call", "to": phone}

    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=25, check=False)
    except Exception as exc:  # noqa: BLE001
        _log({"channel": "phone", "action": "call", "to": phone, "error": str(exc)})
        return {"ok": False, "error": f"ADB не смог позвонить: {exc}", "channel": "phone"}

    ok = result.returncode == 0
    _log({"channel": "phone", "action": "call", "to": phone, "ok": ok, "backend": "adb"})
    if not ok:
        return {"ok": False, "error": (result.stderr or "").strip()[:300], "channel": "phone"}
    return {"ok": True, "channel": "phone", "action": "call", "to": phone}
