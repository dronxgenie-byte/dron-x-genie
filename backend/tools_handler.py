import json
import os
from openai import OpenAI

def execute_tool_call(tool_call):
    if tool_call.function.name == "create_file":
        args = json.loads(tool_call.function.arguments)
        filename = args.get("filename", "test.txt")
        content = args.get("content", "")
        path = os.path.join(os.getcwd(), filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Успешно создан файл {filename}."
    return "Неизвестный инструмент."

def chat_with_tools(client, model, messages):
    tools = [
        {
            "type": "function",
            "function": {
                "name": "create_file",
                "description": "Создает текстовый файл на диске",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "Имя файла, например test.txt"},
                        "content": {"type": "string", "description": "Текст для записи в файл"}
                    },
                    "required": ["filename", "content"]
                }
            }
        }
    ]
    
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=500,
        temperature=0.7,
        tools=tools
    )
    
    message = response.choices[0].message
    
    if hasattr(message, 'tool_calls') and message.tool_calls:
        temp_messages = messages.copy()
        temp_messages.append(message.model_dump() if hasattr(message, 'model_dump') else {
            "role": "assistant",
            "content": message.content,
            "tool_calls": [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in message.tool_calls]
        })
        
        for tool_call in message.tool_calls:
            result = execute_tool_call(tool_call)
            temp_messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": tool_call.function.name,
                "content": result
            })
        
        final_response = client.chat.completions.create(
            model=model,
            messages=temp_messages,
            max_tokens=500,
            temperature=0.7
        )
        return final_response
    else:
        return response
