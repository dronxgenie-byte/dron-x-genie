"""Голосовой ввод: распознавание речи локально (faster-whisper).

Полностью офлайн: модель уже в кэше HuggingFace.
Аудио с микрофона приходит из браузера (webm/ogg/wav), ffmpeg приводит к
16 кГц моно PCM, затем модель выдаёт текст.
"""

from __future__ import annotations

import base64
import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

READY = "ready"
UNAVAILABLE = "unavailable"
UNCONFIGURED = "unconfigured"

# Модель можно переключить в .env: STT_MODEL=small (точнее, но медленнее).
# В кэше HuggingFace уже есть tiny, base, small — скачивать не нужно.
MODEL_SIZE = (os.getenv("STT_MODEL") or "base").strip() or "base"
LANGUAGE = (os.getenv("STT_LANGUAGE") or "ru").strip() or "ru"
MAX_BYTES = 12 * 1024 * 1024

_MODEL = None
_LOCK = threading.Lock()


def _ffmpeg() -> str | None:
    return shutil.which("ffmpeg")


def status() -> dict:
    try:
        import faster_whisper  # noqa: F401
        imported = True
    except Exception:
        imported = False

    return {
        "status": READY if imported and _ffmpeg() else UNAVAILABLE,
        "engine": "faster-whisper",
        "model": MODEL_SIZE,
        "language": LANGUAGE,
        "ffmpeg": bool(_ffmpeg()),
        "loaded": _MODEL is not None,
        "offline": True,
    }


def _load_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    with _LOCK:
        if _MODEL is None:
            from faster_whisper import WhisperModel

            _MODEL = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    return _MODEL


def _decode_base64(payload: str) -> bytes:
    text = (payload or "").strip()
    if text.startswith("data:"):
        _, _, text = text.partition(",")
    try:
        raw = base64.b64decode(text, validate=False)
    except Exception as exc:  # pragma: no cover
        raise ValueError(f"Некорректные данные аудио: {exc}") from exc
    if not raw:
        raise ValueError("Пустое аудио.")
    if len(raw) > MAX_BYTES:
        raise ValueError("Аудио слишком длинное.")
    return raw


def transcribe(audio_base64: str, source_format: str = "webm") -> dict:
    """Распознать речь из base64-аудио и вернуть текст."""
    raw = _decode_base64(audio_base64)

    ffmpeg = _ffmpeg()
    if not ffmpeg:
        raise RuntimeError("ffmpeg не найден: конвертация аудио невозможна.")

    suffix = "." + "".join(ch for ch in source_format if ch.isalnum())[:8] or ".webm"

    with tempfile.TemporaryDirectory(prefix="ananisim_stt_") as tmp:
        incoming = Path(tmp) / f"incoming{suffix}"
        incoming.write_bytes(raw)

        prepared = Path(tmp) / "prepared.wav"
        command = [
            ffmpeg,
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(incoming),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(prepared),
        ]
        result = subprocess.run(command, capture_output=True, timeout=120)
        if result.returncode != 0 or not prepared.is_file():
            detail = (result.stderr or b"").decode("utf-8", "ignore")[:300]
            raise RuntimeError(f"Не удалось прочитать аудио: {detail or 'формат не поддержан'}")

        model = _load_model()
        segments, info = model.transcribe(
            str(prepared), language=LANGUAGE, beam_size=1, vad_filter=True
        )
        pieces = [segment.text.strip() for segment in segments]
        text = " ".join(piece for piece in pieces if piece).strip()

    return {
        "text": text,
        "language": getattr(info, "language", LANGUAGE),
        "language_probability": round(float(getattr(info, "language_probability", 1.0)), 3),
        "duration_seconds": round(float(getattr(info, "duration", 0.0)), 2),
        "engine": "faster-whisper",
        "model": MODEL_SIZE,
    }
