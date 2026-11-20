from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
import os, requests, json, tempfile
from datetime import datetime
from pathlib import Path

# Пытаемся загрузить голосовые модули
VOICE_ENABLED = False
stt = None
tts = None

try:
    from voice_engine import SpeechToText, TextToSpeech
    stt = SpeechToText()
    tts = TextToSpeech()
    VOICE_ENABLED = True
    print("✅ Голосовые модули (Vosk/Piper) загружены")
except Exception as e:
    print(f"⚠️ Голосовые модули не загружены (проверь наличие моделей): {e}")

app = FastAPI(title="МЕХАДУЭТ: Атлас")
LM_STUDIO_URL = "http://127.0.0.1:1234/v1/chat/completions"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARENA_PATH = os.path.join(BASE_DIR, "arena.html")
VAULT_PATH = str(Path(__file__).resolve().parents[2].parent / "DRON_X_GENIE" / "MECHDUET")

def load_memory(query: str) -> str:
    context = ""
    folders = ["01_СЕМЬЯ", "02_УЧЁБА", "03_ИНТЕРЕСЫ"]
    for folder in folders:
        folder_path = os.path.join(VAULT_PATH, folder)
        if os.path.exists(folder_path):
            for filename in os.listdir(folder_path):
                if filename.endswith(".md"):
                    filepath = os.path.join(folder_path, filename)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            context += f"\n--- {filename} ---\n{f.read()}\n"
                    except: pass
    return context if context else "Память пуста."

def log_question(question: str, answer: str):
    log_path = os.path.join(VAULT_PATH, "99_ЛОГИ", "daily_log.md")
    if not os.path.exists(log_path):
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "w", encoding="utf-8") as f: f.write("# Лог вопросов Вани\n\n")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"- {datetime.now().strftime('%Y-%m-%d %H:%M')} — \"{question}\" → {answer[:100]}...\n")

@app.get("/", response_class=HTMLResponse)
def index():
    with open(ARENA_PATH, "r", encoding="utf-8") as f: return f.read()

@app.get("/ask")
def ask(question: str):
    try:
        memory = load_memory(question)
        system_prompt = f"Ты — Атлас, серьёзный робот-помощник. Объясняй 10-летнему школьнику Ване просто и понятно. Уложись в 3-4 предложения.\nКонтекст: {memory}"
        payload = {
            "model": "local-model",
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": question}],
            "temperature": 0.2, "max_tokens": 220, "stream": False
        }
        response = requests.post(LM_STUDIO_URL, json=payload, timeout=180)
        response.raise_for_status()
        answer = response.json().get("choices", [{}])[0].get("message", {}).get("content", "Нет ответа")
        log_question(question, answer)
        return {"robot": "Атлас", "status": "success", "answer": answer}
    except requests.exceptions.ConnectionError:
        return {"robot": "Атлас", "status": "error", "answer": "LM Studio не отвечает на порту 1234."}
    except Exception as e:
        return {"robot": "Атлас", "status": "error", "answer": str(e)}

@app.post("/api/voice")
async def voice_input(audio: UploadFile = File(...)):
    """Принимает аудио от браузера, конвертирует в 16kHz WAV и распознаёт через Vosk"""
    if not VOICE_ENABLED:
        return {"status": "error", "answer": "Голосовые модули не инициализированы."}
    
    try:
        from pydub import AudioSegment
        import wave
        import numpy as np

        temp_in = os.path.join(tempfile.gettempdir(), "input_audio.webm")
        temp_wav = os.path.join(tempfile.gettempdir(), "input_audio.wav")
        
        with open(temp_in, "wb") as f:
            f.write(await audio.read())
        
        # Конвертация в строгий формат Vosk: 16000 Hz, Mono
        sound = AudioSegment.from_file(temp_in)
        sound = sound.set_frame_rate(16000).set_channels(1)
        sound.export(temp_wav, format="wav")
        
        with wave.open(temp_wav, "rb") as wf:
            audio_array = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
        
        text = stt.recognize(audio_array)
        
        # Очистка временных файлов
        if os.path.exists(temp_in): os.remove(temp_in)
        if os.path.exists(temp_wav): os.remove(temp_wav)
        
        return {"status": "success", "text": text}
    except Exception as e:
        return {"status": "error", "answer": f"Ошибка обработки аудио: {str(e)}"}

@app.get("/api/tts")
def text_to_speech(text: str, robot: str = "atlas"):
    if not VOICE_ENABLED:
        return {"status": "error", "answer": "Голосовые модули не инициализированы."}
    try:
        output_file = os.path.join(tempfile.gettempdir(), f"response_{robot}.wav")
        tts.speak(text, robot, output_file)
        return FileResponse(output_file, media_type="audio/wav")
    except Exception as e:
        return {"status": "error", "answer": str(e)}
