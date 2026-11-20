import os
import json
import logging

logger = logging.getLogger(__name__)

# Автоматически находим папку configs в корне проекта
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIGS_DIR = os.path.join(BASE_DIR, "configs")

def load_agent_configs():
    configs = {}
    if not os.path.exists(CONFIGS_DIR):
        logger.error(f"Папка {CONFIGS_DIR} не найдена!")
        return configs

    for filename in os.listdir(CONFIGS_DIR):
        if filename.endswith(".json") and filename != "settings.json":
            try:
                with open(os.path.join(CONFIGS_DIR, filename), 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    agent_name = filename.replace(".json", "")
                    configs[agent_name] = config
            except Exception as e:
                logger.error(f"Ошибка чтения конфига {filename}: {e}")
    return configs

async def route_request(query: str, agent: str = None):
    # Если агент передан явно через API (например, "x" или "dron")
    if agent:
        if agent == "council":
            from main import process_council
            return await process_council(query)
        return {"response": f"Агент {agent} получил запрос: {query}", "agent": agent}

    # Если агент не передан, ищем по триггерам
    configs = load_agent_configs()
    query_lower = query.lower()
    
    # Проверяем триггеры (сначала Совет, потом остальные)
    if "совет" in query_lower:
        from main import process_council
        return await process_council(query)

    for agent_name, config in configs.items():
        triggers = config.get("triggers", [])
        for trigger in triggers:
            if trigger in query_lower:
                # Здесь мы должны вызвать логику конкретного агента
                return {"response": f"Ответ от {agent_name}: {query}", "agent": agent_name}
                
    # Если ничего не нашли — отвечает Дрон по умолчанию
    return {"response": f"Дрон [LOCAL] на связи. Чем помочь, Капитан? (Запрос: {query})", "agent": "dron"}
