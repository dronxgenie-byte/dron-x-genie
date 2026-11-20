"""Голос Дрона: локальный TTS (Piper) + опциональная «грубость» через ffmpeg.

Никакого облака: если сети нет, Дрон всё равно говорит.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
import threading
from collections import OrderedDict
from pathlib import Path

from .config import Paths

READY = "ready"
UNAVAILABLE = "unavailable"
MISSING = "missing"

_MODEL_CACHE: dict[str, object] = {}
_AUDIO_CACHE: OrderedDict[str, bytes] = OrderedDict()
_LOCK = threading.Lock()
_CACHE_LIMIT = 48


def _ffmpeg_path() -> str | None:
    return shutil.which("ffmpeg")


def model_path(paths: Paths, model_name: str) -> Path:
    return paths.tts_models / f"{model_name}.onnx"


def status(paths: Paths) -> dict:
    try:
        import piper  # noqa: F401
        piper_ok = True
    except Exception:  # pragma: no cover - зависит от окружения
        piper_ok = False

    ffmpeg = _ffmpeg_path()
    models = []
    if paths.tts_models.is_dir():
        models = sorted(p.stem for p in paths.tts_models.glob("*.onnx"))

    if not piper_ok:
        state = UNAVAILABLE
    elif not models:
        state = MISSING
    else:
        state = READY

    return {
        "status": state,
        "piper": piper_ok,
        "ffmpeg": bool(ffmpeg),
        "models": models,
    }


def _load_voice(model_file: Path):
    cache_key = str(model_file)
    voice = _MODEL_CACHE.get(cache_key)
    if voice is not None:
        return voice

    from piper import PiperVoice

    voice = PiperVoice.load(str(model_file))
    _MODEL_CACHE[cache_key] = voice
    return voice


def _remember(key: str, payload: bytes) -> None:
    _AUDIO_CACHE[key] = payload
    while len(_AUDIO_CACHE) > _CACHE_LIMIT:
        _AUDIO_CACHE.popitem(last=False)


def synthesize(
    paths: Paths,
    text: str,
    model_name: str,
    length_scale: float = 1.0,
    pitch_factor: float = 1.0,
    bass_gain: int | None = None,
) -> bytes:
    """Синтезировать реплику и вернуть WAV байтами.

    pitch_factor < 1 понижает тон, не меняя длительность (через ffmpeg).
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("Пустой текст для озвучивания.")

    model_file = model_path(paths, model_name)
    if not model_file.is_file():
        raise FileNotFoundError(f"Голосовая модель не найдена: {model_name}")

    key_src = f"{model_name}|{length_scale}|{pitch_factor}|{bass_gain}|{text}"
    key = hashlib.sha256(key_src.encode("utf-8")).hexdigest()

    with _LOCK:
        cached = _AUDIO_CACHE.get(key)
        if cached is not None:
            _AUDIO_CACHE.move_to_end(key)
            return cached

    import wave

    from piper import SynthesisConfig

    voice = _load_voice(model_file)
    config = SynthesisConfig(length_scale=length_scale)

    with tempfile.TemporaryDirectory(prefix="ananisim_tts_") as tmp:
        raw_path = Path(tmp) / "raw.wav"
        with wave.open(str(raw_path), "wb") as handle:
            voice.synthesize_wav(text, handle, syn_config=config)

        payload = raw_path.read_bytes()

        ffmpeg = _ffmpeg_path()
        needs_shift = abs(pitch_factor - 1.0) > 0.001
        if needs_shift and ffmpeg:
            shifted = Path(tmp) / "shifted.wav"
            rate = int(22050 * pitch_factor)
            tempo = 1.0 / pitch_factor
            filters = [
                f"asetrate={rate}",
                "aresample=22050",
                f"atempo={tempo:.6f}",
            ]
            if bass_gain:
                filters.append(f"bass=g={bass_gain}")

            cmd = [
                ffmpeg,
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(raw_path),
                "-af",
                ",".join(filters),
                str(shifted),
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            if result.returncode == 0 and shifted.is_file() and shifted.stat().st_size > 44:
                payload = shifted.read_bytes()

    with _LOCK:
        _remember(key, payload)

    return payload
