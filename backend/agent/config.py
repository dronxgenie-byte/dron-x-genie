"""Конфигурация ANANISIM OS.

Секреты читаются только здесь и никогда не возвращаются в браузер.
Наружу отдаётся лишь признак «настроен / не настроен».
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Единая структура ANANISIM OS:
#   PROJECT_ROOT = <project>/dron-x-genie   (код: backend/frontend/data)
#   VAULT_ROOT   = <projects>/DRON_X_GENIE   (память: Obsidian)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
VAULT_ROOT = Path(__file__).resolve().parents[3] / "DRON_X_GENIE"
ROOT = PROJECT_ROOT  # совместимость со старым кодом

# .env может лежать в проекте или в корне волта — читаем оба, без перезаписи.
for _env_file in (PROJECT_ROOT / ".env", VAULT_ROOT / ".env"):
    if _env_file.is_file():
        load_dotenv(_env_file, override=False)

# Effective Vault path after loading environment settings.
VAULT_ROOT = Path(os.getenv("VAULT_PATH") or str(VAULT_ROOT)).expanduser().resolve()

DEFAULT_TZ = "Europe/Moscow"

DEFAULT_SETTINGS: dict = {
    "profile": "dron",
    "theme": "neon",
    "scale": 1.0,
    "large_mode": False,
    "sound": True,
    "animation": True,
    "theater_mode": True,
    "timezone": DEFAULT_TZ,
    "default_agent": "dron",
    "panels_collapsed": False,
    "duet_mode": True,
    "dron_temperature": 0.35,
    "dron_max_tokens": 220,
    "voice_model": "ru_RU-dmitri-medium",
    "voice_autoplay": True,
    "voice_length_scale": 1.0,
    "voice_pitch_factor": 1.0,
    "voice_bass_gain": 0,
}


@dataclass(frozen=True)
class Paths:
    """Пути, разрешённые для чтения и записи."""

    vault: Path
    data: Path
    settings_file: Path
    inbox: Path
    schedule: Path
    vanya: Path
    finance: Path
    council: Path
    tts_models: Path
    db: Path | None

    # Каталоги, внутри которых разрешено чтение заметок.
    readable: tuple[Path, ...] = field(default=())


def _p(env_name: str, default: str) -> Path:
    raw = os.getenv(env_name) or default
    return Path(raw).expanduser().resolve()


def load_paths() -> Paths:
    vault = _p("VAULT_PATH", str(VAULT_ROOT))
    data = _p("DRON_UI_DATA_PATH", str(PROJECT_ROOT / "data" / "dron_ui"))

    db_raw = (os.getenv("DATABASE_PATH") or "").strip()
    db = Path(db_raw).expanduser().resolve() if db_raw else (PROJECT_ROOT / "data" / "dron_x_genie.db")

    inbox = vault / "01_INBOX"
    schedule = vault / "80_FAMILY" / "schedule"
    vanya = vault / "80_FAMILY" / "vanya"
    finance = vault / "60_FINANCE"
    council = vault / "80_FAMILY" / "council"

    readable = tuple(p for p in (inbox, schedule, vanya, finance, council) if p.exists())

    return Paths(
        vault=vault,
        data=data,
        settings_file=data / "settings.json",
        inbox=inbox,
        schedule=schedule,
        vanya=vanya,
        finance=finance,
        council=council,
        tts_models=PROJECT_ROOT / "data" / "models" / "piper",
        db=db,
        readable=readable,
    )


def load_settings(paths: Paths) -> dict:
    """Настройки: значения по умолчанию, поверх — то, что есть на диске."""
    settings = dict(DEFAULT_SETTINGS)
    try:
        if paths.settings_file.is_file():
            stored = json.loads(paths.settings_file.read_text(encoding="utf-8-sig"))
            if isinstance(stored, dict):
                for key, value in stored.items():
                    if key in DEFAULT_SETTINGS:
                        settings[key] = value
    except (OSError, ValueError):
        # Битый settings.json не должен ломать запуск: работаем на умолчаниях.
        pass
    return settings


def save_settings(paths: Paths, settings: dict) -> None:
    paths.data.mkdir(parents=True, exist_ok=True)
    clean = {k: settings[k] for k in DEFAULT_SETTINGS if k in settings}
    paths.settings_file.write_text(
        json.dumps(clean, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


@dataclass(frozen=True)
class Cloud:
    """Состояние облачных сервисов.

    Ключ лежит внутри объекта, но наружу (в JSON ответов) уходит только
    признак `api_key_set`: маршруты обязаны не сериализовать этот dataclass
    целиком.
    """

    api_key: str
    folder_id: str | None
    prompt_id: str | None
    realtime_model: str | None
    text_model: str | None
    realtime_wss: str | None = None
    service_name: str | None = None

    @property
    def api_key_set(self) -> bool:
        return bool(self.api_key)

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.folder_id)


def load_cloud() -> Cloud:
    return Cloud(
        api_key=(os.getenv("YANDEX_API_KEY") or "").strip(),
        folder_id=(os.getenv("YANDEX_FOLDER_ID") or "").strip() or None,
        prompt_id=(os.getenv("YANDEX_PROMPT_ID") or "").strip() or None,
        realtime_model=(os.getenv("YANDEX_REALTIME_MODEL") or "").strip() or None,
        text_model=(os.getenv("YANDEX_TEXT_MODEL") or "").strip() or None,
        realtime_wss=(os.getenv("YANDEX_REALTIME_WSS") or "").strip() or None,
        service_name=(os.getenv("YANDEX_PROMPT_SERVICE_NAME") or "").strip() or None,
    )


@dataclass(frozen=True)
class LocalModel:
    url: str
    model: str


def load_local_model() -> LocalModel:
    return LocalModel(
        url=((os.getenv("LM_STUDIO_URL") or "http://127.0.0.1:1234/v1").strip()).rstrip("/"),
        model=(os.getenv("LM_STUDIO_MODEL") or "google/gemma-4-e4b").strip(),
    )
