"""Работа с Vault: безопасное чтение заметок, задачи, расписание.

Правила (ТЗ 17.1):
- читаем только из явно разрешённых каталогов;
- проверяем канонический путь, запрещаем выход за корень;
- Markdown не исполняется: наружу отдаётся обычный текст.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .config import Paths

# Состояния источника (ТЗ 16.2).
READY = "ready"
UNAVAILABLE = "unavailable"
MISSING = "missing"

TASK_RE = re.compile(r"^\s*[-*]\s+\[(?P<mark>[ xX])\]\s+(?P<text>.+?)\s*$")
FRONTMATTER_RE = re.compile(r"^---\s*$(.*?)^---\s*$", re.MULTILINE | re.DOTALL)


class VaultError(Exception):
    """Нарушение правил доступа к Vault."""


def resolve_safe(root: Path, relative: str) -> Path:
    """Разрешить путь внутри root или отказать.

    Защита от `..`, абсолютных путей и выхода за корень через симлинки.
    """
    if not relative or relative.strip() == "":
        raise VaultError("Пустой путь недопустим.")

    candidate = Path(relative)
    if candidate.is_absolute() or candidate.drive:
        raise VaultError("Абсолютный путь запрещён.")

    root_resolved = root.resolve()
    target = (root_resolved / candidate).resolve()

    if target != root_resolved and root_resolved not in target.parents:
        raise VaultError("Путь выходит за разрешённый каталог.")

    return target


def is_readable(path: Path, paths: Paths) -> bool:
    """Файл лежит внутри одного из разрешённых каталогов."""
    try:
        resolved = path.resolve()
    except OSError:
        return False
    for allowed in paths.readable:
        try:
            allowed_resolved = allowed.resolve()
        except OSError:
            continue
        if resolved == allowed_resolved or allowed_resolved in resolved.parents:
            return True
    return False


@dataclass
class Task:
    id: str
    text: str
    done: bool
    source: str


@dataclass
class Event:
    id: str
    title: str
    date: str | None
    time: str | None
    duration_minutes: int | None
    participants: list[str]
    body: str
    source: str


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Минимальный разбор YAML-заголовка без внешних зависимостей."""
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    raw = match.group(1)
    body = text[match.end():].lstrip("\r\n")

    data: dict = {}
    current_list_key: str | None = None

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith("- ") and current_list_key:
            data.setdefault(current_list_key, []).append(stripped[2:].strip().strip("\"'"))
            continue

        if ":" not in stripped:
            continue

        key, _, value = stripped.partition(":")
        key = key.strip()
        value = value.strip()
        current_list_key = None

        if value == "":
            current_list_key = key
            data[key] = []
            continue

        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]

        data[key] = value

    # Пустые списки без элементов не нужны.
    for key, value in list(data.items()):
        if isinstance(value, list) and not value:
            data[key] = []

    return data, body


def read_tasks(paths: Paths, limit: int = 200) -> tuple[list[Task], str]:
    """Незавершённые задачи из 01_INBOX.

    Источником считаются строки вида `- [ ] текст`.
    """
    if not paths.inbox.is_dir():
        return [], MISSING

    tasks: list[Task] = []
    try:
        files = sorted(paths.inbox.glob("*.md"))
    except OSError:
        return [], UNAVAILABLE

    try:
        for file in files:
            if not is_readable(file, paths):
                continue
            try:
                # utf-8-sig: заметки из PowerShell/Блокнота часто с BOM,
                # иначе первый `---` не распознаётся как начало заголовка.
                content = file.read_text(encoding="utf-8-sig")
            except (OSError, UnicodeDecodeError):
                continue

            for number, line in enumerate(content.splitlines(), start=1):
                match = TASK_RE.match(line)
                if not match:
                    continue
                tasks.append(
                    Task(
                        id=f"{file.name}:{number}",
                        text=match.group("text"),
                        done=match.group("mark").lower() == "x",
                        source=f"01_INBOX/{file.name}",
                    )
                )
                if len(tasks) >= limit:
                    return tasks, READY
    except OSError:
        return [], UNAVAILABLE

    return tasks, READY


def read_events(paths: Paths, limit: int = 100) -> tuple[list[Event], str]:
    """События из 80_FAMILY/schedule (Markdown + YAML-заголовок)."""
    if not paths.schedule.is_dir():
        return [], MISSING

    events: list[Event] = []
    try:
        files = sorted(paths.schedule.glob("*.md"))
    except OSError:
        return [], UNAVAILABLE

    try:
        for file in files:
            if not is_readable(file, paths):
                continue
            try:
                content = file.read_text(encoding="utf-8-sig")
            except (OSError, UnicodeDecodeError):
                continue

            meta, body = parse_frontmatter(content)

            raw_duration = meta.get("duration_minutes")
            try:
                duration = int(raw_duration) if raw_duration not in (None, "") else None
            except (TypeError, ValueError):
                duration = None

            participants = meta.get("participants")
            if not isinstance(participants, list):
                participants = []

            events.append(
                Event(
                    id=str(meta.get("id") or file.stem),
                    title=str(meta.get("title") or file.stem),
                    date=str(meta.get("date")) if meta.get("date") else None,
                    time=str(meta.get("time")) if meta.get("time") else None,
                    duration_minutes=duration,
                    participants=[str(p) for p in participants],
                    body=body.strip()[:500],
                    source=f"80_FAMILY/schedule/{file.name}",
                )
            )
    except OSError:
        return [], UNAVAILABLE

    def sort_key(event: Event) -> tuple:
        day = event.date or "9999-99-99"
        clock = event.time or "99:99"
        return (day, clock)

    events.sort(key=sort_key)
    return events[:limit], READY


def read_note(paths: Paths, relative: str, max_chars: int = 20000) -> dict:
    """Прочитать заметку по относительному пути внутри разрешённых каталогов."""
    safe = resolve_safe(paths.vault, relative)

    if not is_readable(safe, paths):
        raise VaultError("Каталог не разрешён для чтения.")

    if not safe.is_file():
        raise VaultError("Файл не найден.")

    if safe.suffix.lower() not in {".md", ".txt", ".json"}:
        raise VaultError("Тип файла не разрешён.")

    try:
        content = safe.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise VaultError(f"Не удалось прочитать файл: {exc}") from exc

    truncated = len(content) > max_chars
    return {
        "path": relative,
        "content": content[:max_chars],
        "truncated": truncated,
    }


def vault_status(paths: Paths) -> str:
    if not paths.vault.is_dir():
        return MISSING
    try:
        next(paths.vault.iterdir(), None)
    except OSError:
        return UNAVAILABLE
    return READY


def list_notes(paths: Paths, folder: Path, limit: int = 50) -> tuple[list[dict], str]:
    """Список заметок каталога (свежие первыми)."""
    if not folder.is_dir():
        return [], MISSING

    try:
        files = [p for p in folder.glob("*.md") if p.is_file()]
    except OSError:
        return [], UNAVAILABLE

    notes = []
    for file in files:
        if not is_readable(file, paths):
            continue
        try:
            stat = file.stat()
            relative = file.relative_to(paths.vault).as_posix()
        except (OSError, ValueError):
            continue
        notes.append(
            {
                "name": file.stem,
                "path": relative,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                "mtime": stat.st_mtime,
            }
        )

    notes.sort(key=lambda item: item["mtime"], reverse=True)
    for item in notes:
        item.pop("mtime", None)

    return notes[:limit], READY


def today_iso() -> str:
    return date.today().isoformat()


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
