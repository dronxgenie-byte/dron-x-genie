import json
import os
import wave
import numpy as np
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from piper.voice import PiperVoice

# Пути
VOICE_DIR = os.path.join(os.path.dirname(__file__), "voice_models")
ATLAS_VOICE = os.path.join(VOICE_DIR, "ru_RU-dmitrii-medium.onnx")
ORBITA_VOICE = os.path.join(VOICE_DIR, "ru_RU-svetlana-medium.onnx")
VOSK_MODEL = os.path.join(VOICE_DIR, "vosk-model-small-ru-0.22")


class SpeechToText:
    """Распознавание речи через Vosk (локально)"""
    
    def __init__(self):
        if not os.path.exists(VOSK_MODEL):
            raise FileNotFoundError(f"Модель Vosk не найдена: {VOSK_MODEL}\nСкачай с https://alphacephei.com/vosk/models")
        
        self.model = Model(VOSK_MODEL)
        self.sample_rate = 16000
    
    def recognize(self, audio_data):
        """Распознаёт речь из аудио"""
        recognizer = KaldiRecognizer(self.model, self.sample_rate)
        audio_bytes = audio_data.tobytes()
        
        if recognizer.AcceptWaveform(audio_bytes):
            result = json.loads(recognizer.Result())
            return result.get("text", "")
        else:
            return ""


class TextToSpeech:
    """Синтез речи через Piper (локально, два голоса)"""
    
    def __init__(self):
        self.voices = {}
        
        if os.path.exists(ATLAS_VOICE):
            self.voices["atlas"] = PiperVoice.load(ATLAS_VOICE)
        else:
            print(f"⚠️ Голос Атласа не найден: {ATLAS_VOICE}")
        
        if os.path.exists(ORBITA_VOICE):
            self.voices["orbita"] = PiperVoice.load(ORBITA_VOICE)
        else:
            print(f"⚠️ Голос Орбиты не найден: {ORBITA_VOICE}")
    
    def speak(self, text: str, robot: str = "atlas", output_file: str = "response.wav"):
        """Синтезирует речь и сохраняет в файл"""
        if robot not in self.voices:
            raise ValueError(f"Голос {robot} не загружен")
        
        voice = self.voices[robot]
        voice.synthesize(text, output_file)
        return output_file