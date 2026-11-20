import os
import uuid
import traceback
import asyncio
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from agents import ask_dron, ask_genie
from faster_whisper import WhisperModel
import edge_tts

# === ПУТИ ===
BACKEND_DIR = Path(__file__).parent
TEMP_AUDIO_DIR = BACKEND_DIR / "temp_audio"
TEMP_AUDIO_DIR.mkdir(exist_ok=True)

# === ГЛОБАЛЬНАЯ ИНИЦИАЛИЗАЦИЯ МОДЕЛЕЙ (Делается 1 раз при старте!) ===
print("⏳ Загрузка модели Whisper (small)... Это займет несколько секунд при первом запуске.")
# device="cpu", compute_type="int8" для работы на процессоре без перегрузки
stt_model = WhisperModel("small", device="cpu", compute_type="int8")
print("✅ Whisper загружен!")

# Голоса для edge-tts (высокое качество, бесплатно, локально)
DRON_VOICE = "ru-RU-RuslanNeural"        # Мужской голос (Руслан), ниже и медленнее
DRON_VOICE_RATE = "-15%"                  # Чуть медленнее
DRON_VOICE_PITCH = "-5Hz"                 # Чуть ниже
GENIE_VOICE = "ru-RU-SvetlanaNeural"     # Мягкий, уверенный женский (Нейрофея)

app = FastAPI(title="DRON X GENIE Voice Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/temp_audio", StaticFiles(directory=str(TEMP_AUDIO_DIR)), name="temp_audio")
from fastapi.responses import HTMLResponse

TEMPLATES_DIR = BACKEND_DIR / "templates"

@app.get("/", response_class=HTMLResponse)
async def read_root():
    html_file = TEMPLATES_DIR / "index.html"
    if html_file.exists():
        return html_file.read_text(encoding="utf-8")
    return "<h1>Файл index.html не найден в папке backend/templates</h1>"
# === ИСТОРИЯ ДИАЛОГА (для контекста) ===
shared_history = []

@app.post("/api/voice_chat")
async def voice_chat(
    audio_file: UploadFile = File(...),
    agent: str = Form("dron")
):
    """Полный цикл: Голос -> Текст -> Ответ ИИ -> Голос"""
    temp_wav_path = None
    temp_mp3_path = None
    
    try:
        file_id = uuid.uuid4().hex
        temp_wav_path = TEMP_AUDIO_DIR / f"input_{file_id}.wav"
        temp_mp3_path = TEMP_AUDIO_DIR / f"output_{file_id}.mp3"
        
        # 1. Сохраняем аудио от пользователя
        with open(temp_wav_path, "wb") as f:
            f.write(await audio_file.read())

        # 2. Распознавание речи (STT) через faster-whisper
        segments, info = stt_model.transcribe(str(temp_wav_path), language="ru")
        user_text = " ".join([segment.text for segment in segments]).strip()
        
        if not user_text:
            user_text = "(неразборчиво)"
        
        print(f"🎤 Распознано ({agent}): {user_text}")

        # 3. Генерация ответа (LLM) через agents.py
        # Добавляем в историю для контекста (опционально, зависит от твоей логики в agents.py)
        if agent.lower() == "dron":
            assistant_text = ask_dron(user_text)
            voice_to_use = DRON_VOICE
        else:
            assistant_text = ask_genie(user_text)
            voice_to_use = GENIE_VOICE

        print(f"🤖 Ответ от {agent}: {assistant_text}")

        # 4. Синтез речи (TTS) через edge-tts (асинхронно, не блокирует сервер)
        if agent.lower() == "dron":
            communicate = edge_tts.Communicate(
                assistant_text,
                voice_to_use,
                rate=DRON_VOICE_RATE,
                pitch=DRON_VOICE_PITCH,
            )
        else:
            communicate = edge_tts.Communicate(assistant_text, voice_to_use)
        await communicate.save(str(temp_mp3_path))
        print(f"🔊 Аудио сохранено: {temp_mp3_path.name}")

        return {
            "user_text": user_text,
            "assistant_text": assistant_text,
            "audio_url": f"/temp_audio/output_{file_id}.mp3",
            "agent": agent
        }

    except Exception as e:
        error_detail = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ Ошибка в /api/voice_chat:\n{error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)
        
    finally:
        # Очистка временных файлов ввода (вывод оставляем, чтобы фронтенд успел его забрать)
        if temp_wav_path and temp_wav_path.exists():
            try:
                temp_wav_path.unlink()
            except Exception:
                pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)