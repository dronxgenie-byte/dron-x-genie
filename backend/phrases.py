import random

PHRASES = {
    "thinking": {
        "dron": "Сканирую память... Держи курс.",
        "genie": "Морщу чело, повелитель... Взираю в хрустальный шар..."
    },
    "saving": {
        "dron": "Запись в бортовой журнал выполнена.",
        "genie": "Кладу в ковчег входящих. Да будет так!"
    },
    "error": {
        "dron": "Сбой навигации. Проверь подключение к локальной модели.",
        "genie": "Туман сгустился над бездной... Джинн теряет связь с эфиром!"
    },
    "ritual": [
        "Дох-кибиток!",
        "Абра-кадабра!",
        "Вырываю волосок из бороды...",
        "Тысячу лет я ждал этого момента..."
    ]
}

def get_phrase(key: str, mode: str = "x") -> str:
    """Возвращает фразу в зависимости от режима: 'dron', 'genie' или 'x' (оба)"""
    if key == "ritual":
        return random.choice(PHRASES["ritual"])
    
    phrase_data = PHRASES.get(key, {"dron": "Готово.", "genie": "Свершилось!"})
    
    if mode == "dron":
        return f"[DRON] {phrase_data['dron']}"
    elif mode == "genie":
        return f"[GENIE] {phrase_data['genie']}"
    else:
        return f"{phrase_data['dron']} \n✨ {phrase_data['genie']}"
