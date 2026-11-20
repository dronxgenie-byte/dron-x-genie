"""Семейный совет: повестка вечера из Markdown.

Заметка совета лежит в `80_FAMILY/council/<ГГГГ-ММ-ДД>.md`.
Разделы читаются по заголовкам `## Название`, пункты — по строкам `- ...`.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from .config import Paths
from .vault import READY, MISSING, UNAVAILABLE, is_readable, parse_frontmatter

DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")
ITEM_RE = re.compile(r"^\s*[-*]\s+(?P<box>\[[ xX]\]\s*)?(?P<text>.+?)\s*$")

# Разделы, которые показываем в интерфейсе, в нужном порядке.
SECTION_TITLES = {
    "повестка": "Повестка",
    "что сделано": "Что сделано",
    "на завтра": "На завтра",
    "задания": "Задания",
    "напоминания": "Напоминания",
    "поощрения": "Поощрения",
    "штрафы": "Штрафы",
    "решения": "Решения",
}


def council_dir(paths: Paths) -> Path:
    return paths.council


def available_dates(paths: Paths) -> list[str]:
    folder = council_dir(paths)
    if not folder.is_dir():
        return []
    try:
        names = []
        for item in folder.iterdir():
            match = DATE_RE.match(item.name)
            if match:
                names.append(match.group(1))
    except OSError:
        return []
    return sorted(names)


def _parse_sections(body: str) -> dict:
    sections: dict[str, list[dict]] = {}
    current = None

    for line in body.splitlines():
        if line.startswith("## "):
            title = line[3:].strip().lower()
            current = title
            sections.setdefault(current, [])
            continue
        if current is None:
            continue
        match = ITEM_RE.match(line)
        if not match:
            continue
        text = match.group("text").strip()
        if not text:
            continue
        box = match.group("box")
        sections[current].append(
            {
                "text": text,
                "checked": bool(box and "x" in box.lower()),
                "is_task": bool(box),
            }
        )

    return sections


def read_council(paths: Paths, day: str | None = None) -> dict:
    """Прочитать повестку совета за день (по умолчанию — последнюю доступную)."""
    folder = council_dir(paths)

    if not folder.is_dir():
        return {"status": MISSING, "date": None, "sections": [], "source": None}

    dates = available_dates(paths)
    if not dates:
        return {"status": MISSING, "date": None, "sections": [], "source": None}

    chosen = day or dates[-1]
    if day and day not in dates:
        return {"status": MISSING, "date": day, "sections": [], "source": None}

    file = folder / f"{chosen}.md"
    if not file.is_file() or not is_readable(file, paths):
        return {"status": UNAVAILABLE, "date": chosen, "sections": [], "source": None}

    try:
        content = file.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return {"status": UNAVAILABLE, "date": chosen, "sections": [], "source": None}

    meta, body = parse_frontmatter(content)
    raw_sections = _parse_sections(body)

    ordered = []
    seen = set()

    for key, title in SECTION_TITLES.items():
        if key in raw_sections:
            ordered.append({"key": key, "title": title, "items": raw_sections[key]})
            seen.add(key)

    for key, items in raw_sections.items():
        if key in seen:
            continue
        ordered.append({"key": key, "title": key.capitalize(), "items": items})

    return {
        "status": READY,
        "date": str(meta.get("date") or chosen),
        "status_note": str(meta.get("status") or ""),
        "dates": dates,
        "sections": ordered,
        "source": f"80_FAMILY/council/{file.name}",
    }


def tomorrow_iso(today: date | None = None) -> str:
    base = today or date.today()
    return date.fromordinal(base.toordinal() + 1).isoformat()
