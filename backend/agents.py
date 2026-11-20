import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения из .env
load_dotenv()


def ask_dron(user_text: str) -> str:
    """
    Вызывает локальную модель Дрона через OpenAI-совместимый API.
    Работает с LM Studio (порт 1234) и Ollama (порт 11434/v1).
    """
    config_path = Path(__file__).resolve().parent.parent / "configs" / "dron.json"
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        return f"КРИТИЧЕСКАЯ ОШИБКА: не удалось прочитать dron.json: {e}"
    
    # 1. Читаем настройки из конфига
    model_config = config.get("model", {})
    # По умолчанию порт LM Studio. Если Ollama, в dron.json должно быть http://127.0.0.1:11434/v1
    base_url = model_config.get("base_url", "http://127.0.0.1:1234/v1")
    model_name = model_config.get("name", "qwen2.5-7b-instruct")
    temperature = model_config.get("temperature", 0.2)
    
    # 2. Собираем системный промпт из массива строк в один текст
    system_prompt = "\n".join(config.get("system_prompt", []))
    
    # 3. Формируем запрос в формате OpenAI Chat Completions
    url = f"{base_url.rstrip('/')}/chat/completions"
    
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ],
        "temperature": temperature,
        "stream": False
    }
    
    # 4. Отправляем запрос
    try:
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        
        # Извлекаем ответ из стандартного формата OpenAI
        reply = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        
        if not reply:
            return "ОШИБКА: Модель вернула пустой ответ."
            
        return reply
        
    except requests.exceptions.ConnectionError:
        return f"ОШИБКА: Не удалось подключиться к {url}. Убедись, что LM Studio (Local Server) запущен."
    except requests.exceptions.Timeout:
        return "ОШИБКА: Превышено время ожидания ответа от модели."
    except Exception as e:
        return f"ОШИБКА при запросе к модели: {str(e)}"


def ask_genie(user_text: str) -> str:
    """
    Вызывает облачную модель Джина через YandexGPT API.
    """
    config_path = Path(__file__).resolve().parent.parent / "configs" / "genie.json"
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        return f"КРИТИЧЕСКАЯ ОШИБКА: не удалось прочитать genie.json: {e}"
    
    api_key = os.getenv("YANDEX_API_KEY")
    folder_id = os.getenv("YANDEX_FOLDER_ID")
    
    if not api_key or not folder_id:
        return "ОШИБКА: Не найдены переменные окружения YANDEX_API_KEY или YANDEX_FOLDER_ID в файле .env"
    
    model_config = config.get("model", {})
    model_name = model_config.get("name", "yandexgpt/latest")
    temperature = model_config.get("temperature", 0.7)
    
    # Формируем URI модели
    model_uri = f"gpt://{folder_id}/{model_name}"
    # Эндпоинты YandexGPT: пробуем chat/completion, затем completion (фолбэк)
    api_urls = [
        "https://llm.api.cloud.yandex.net/foundationModels/v1/chat/completion",
        "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
    ]

    # Собираем системный промпт
    system_prompt = "\n".join(config.get("system_prompt", []))
    
    last_error = None
    for url in api_urls:
        # chat/completion ожидает messages, completion — строку text
        if "/chat/completion" in url:
            payload = {
                "modelUri": model_uri,
                "completionOptions": {
                    "stream": False,
                    "temperature": temperature,
                    "maxTokens": 2000,
                },
                "messages": [
                    {"role": "system", "text": system_prompt},
                    {"role": "user", "text": user_text},
                ],
            }
        else:
            payload = {
                "modelUri": model_uri,
                "completionOptions": {
                    "stream": False,
                    "temperature": temperature,
                    "maxTokens": 2000,
                },
                "text": f"{system_prompt}\n\nПользователь: {user_text}",
            }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Api-Key {api_key}",
            "x-folder-id": folder_id,
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            result = response.json()

            if "/chat/completion" in url:
                reply = result.get("result", {}).get("alternatives", [{}])[0].get("message", {}).get("text", "").strip()
            else:
                reply = result.get("result", {}).get("alternatives", [{}])[0].get("text", "").strip()

            if not reply:
                return "ОШИБКА: YandexGPT вернул пустой ответ."

            return reply
        except requests.exceptions.RequestException as e:
            last_error = e
            continue

    return f"ОШИБКА при запросе к YandexGPT: {str(last_error)}"