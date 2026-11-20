"""
NOD-инструменты для Агента X.
Базовые классы с Pydantic-валидацией аргументов и конкретные реализации инструментов.
Все операции sandboxed внутри папки проекта.
"""
from __future__ import annotations

import os
import subprocess
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Type
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger("nod.tools")

BASE_DIR = Path(__file__).resolve().parent.parent


def _safe_path(path_str: str) -> str | None:
    safe = (BASE_DIR / path_str).resolve()
    if not str(safe).startswith(str(BASE_DIR)):
        return None
    return str(safe)


# === Pydantic-схемы аргументов инструментов ===

class ReadFileArgs(BaseModel):
    path: str = Field(..., description="Путь к файлу относительно корня проекта")


class RunCommandArgs(BaseModel):
    command: str = Field(..., description="Shell-команда для выполнения")
    timeout: int = Field(60, ge=1, le=300, description="Таймаут в секундах")


class SearchArgs(BaseModel):
    query: str = Field(..., description="Поисковый запрос")


class WriteFileArgs(BaseModel):
    path: str = Field(..., description="Путь к файлу относительно корня проекта")
    content: str = Field(..., description="Содержимое для записи")


# === Базовый класс инструмента NOD ===

class NodTool(ABC):
    name: str
    description: str
    args_schema: Type[BaseModel]

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        ...

    def validate_args(self, raw_args: dict[str, Any]) -> BaseModel:
        try:
            return self.args_schema(**raw_args)
        except ValidationError as e:
            raise ValueError(f"Ошибка валидации аргументов для {self.name}: {e}")


# === Конкретные инструменты ===

class ReadFileTool(NodTool):
    name = "read_file"
    description = "Читает содержимое файла из директории проекта"
    args_schema = ReadFileArgs

    async def execute(self, **kwargs: Any) -> str:
        args = self.validate_args(kwargs)
        path = _safe_path(args.path)
        if not path:
            return "ОШИБКА БЕЗОПАСНОСТИ: путь вне проекта"
        if not os.path.exists(path):
            return f"ОШИБКА: файл не найден: {args.path}"
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"ОШИБКА чтения: {str(e)}"


class RunCommandTool(NodTool):
    name = "run_command"
    description = "Выполняет shell-команду в директории проекта"
    args_schema = RunCommandArgs

    async def execute(self, **kwargs: Any) -> str:
        args = self.validate_args(kwargs)
        try:
            result = subprocess.run(
                args.command,
                shell=True,
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
                timeout=args.timeout,
                encoding="utf-8",
                errors="replace",
            )
            output = ""
            if result.stdout:
                output += f"STDOUT:\n{result.stdout}\n"
            if result.stderr:
                output += f"STDERR:\n{result.stderr}\n"
            output += f"ВЫХОДНОЙ КОД: {result.returncode}"
            return output.strip()
        except subprocess.TimeoutExpired:
            return f"ОШИБКА: команда превысила лимит времени ({args.timeout} сек)"
        except Exception as e:
            return f"ОШИБКА выполнения: {str(e)}"


class SearchTool(NodTool):
    name = "search"
    description = "Поиск информации в интернете по запросу"
    args_schema = SearchArgs

    async def execute(self, **kwargs: Any) -> str:
        args = self.validate_args(kwargs)
        return f"Поиск по запросу '{args.query}': инструмент поиска в разработке, используйте провайдера LLM для получения актуальных данных."


class WriteFileTool(NodTool):
    name = "write_file"
    description = "Создаёт или перезаписывает файл в директории проекта"
    args_schema = WriteFileArgs

    async def execute(self, **kwargs: Any) -> str:
        args = self.validate_args(kwargs)
        path = _safe_path(args.path)
        if not path:
            return "ОШИБКА БЕЗОПАСНОСТИ: путь вне проекта"
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(args.content)
            return f"Файл создан: {args.path}"
        except Exception as e:
            return f"ОШИБКА создания файла: {str(e)}"


# === Реестр инструментов ===

TOOL_REGISTRY: dict[str, NodTool] = {}


def register_tool(tool: NodTool) -> None:
    TOOL_REGISTRY[tool.name] = tool
    logger.info(f"[NOD] Зарегистрирован инструмент: {tool.name}")


def get_tool(name: str) -> NodTool | None:
    return TOOL_REGISTRY.get(name)


def list_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": t.name,
            "description": t.description,
            "args_schema": t.args_schema.model_json_schema(),
        }
        for t in TOOL_REGISTRY.values()
    ]


# Регистрация инструментов по умолчанию
for _tool in [ReadFileTool(), RunCommandTool(), SearchTool(), WriteFileTool()]:
    register_tool(_tool)
