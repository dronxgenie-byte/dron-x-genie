"""Долговременная память Джинни и связь с Дроном.

Идея (договорённость с Боссом):
- У Джинни одна своя папка `data/genie_memory/`, а не весь Obsidian.
- В ней лежит переписка чата (`chat.jsonl`), сжатая сводка (`summary.md`)
  и устойчивые факты (`facts.md`).
- Сводку делает Дрон: он локальный, бесплатный и уже знает семейный контекст.
- Когда сводка устаревает, старые реплики сжимаются, а полный лог уезжает
  в `archive/` — память не растёт бесконечно.
- Если в памяти чего-то нет, Джинни спрашивает Дрона через инструмент
  `ask_dron` — это и есть подпольная связь между агентами.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from . import dron
from .config import LocalModel

ROOT = Path(__file__).resolve().parents[2]
MEMORY_DIR = ROOT / "data" / "genie_memory"
CHAT_LOG = MEMORY_DIR / "chat.jsonl"
SUMMARY = MEMORY_DIR / "summary.md"
FACTS = MEMORY_DIR / "facts.md"
ARCHIVE_DIR = MEMORY_DIR / "archive"

# Порог: когда реплик больше, Дрон сжимает старые в сводку.
KEEP_TURNS = 24
COMPACT_KEEP = 12
MAX_BLOCK_CHARS = 3500

SUMMARY_HEADER = """# Память Джинни — сводка

Обновлено: {ts}
Реплик сжато: {count}

"""

COMPACT_PROMPT = """Ты — Дрон, хранитель памяти семейной системы ANANISIM OS.
Сожми переписку в короткую сводку для Джинни (голосового помощника семьи).

Требования:
- 8–14 пунктов, каждый — факт, а не пересказ реплик.
- Сохраняй имена (Босс/Андрей, Ваня, Тамара Ивановна), даты, договорённости,
  привычки, планы, незакрытые вопросы.
- Ничего не выдумывай: только то, что есть в переписке.
- Без вступлений и обращений, сразу список с «- ».
- Пиши по-русски, коротко.

ПРЕЖНЯЯ СВОДКА:
{previous}

НОВАЯ ПЕРЕПИСКА:
{transcript}
"""


def _ensure_dirs() -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _atomic_write(path: Path, text: str) -> None:
    _ensure_dirs()
    handle, temp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def append_turn(role: str, text: str, *, agent: str = "genie", source: str = "chat") -> None:
    """Записать реплику в память. Ничего не роняет: память не критична."""
    value = (text or "").strip()
    if not value:
        return
    _ensure_dirs()
    entry = {
        "ts": _now(),
        "role": role,
        "agent": agent,
        "source": source,
        "text": value[:4000],
    }
    with CHAT_LOG.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_turns() -> list[dict]:
    if not CHAT_LOG.is_file():
        return []
    turns: list[dict] = []
    with CHAT_LOG.open("r", encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict) and item.get("text"):
                turns.append(item)
    return turns


def recent_turns(limit: int = COMPACT_KEEP) -> list[dict]:
    return read_turns()[-limit:]


def read_summary() -> str:
    if not SUMMARY.is_file():
        return ""
    return SUMMARY.read_text(encoding="utf-8").strip()


def read_facts() -> str:
    if not FACTS.is_file():
        return ""
    return FACTS.read_text(encoding="utf-8").strip()


def add_fact(text: str) -> None:
    value = (text or "").strip()
    if not value:
        return
    existing = read_facts()
    line = f"- {value}"
    if line in existing:
        return
    _atomic_write(FACTS, (existing + "\n" + line).strip() + "\n")


def needs_compaction() -> bool:
    return len(read_turns()) > KEEP_TURNS


def memory_block(limit: int = MAX_BLOCK_CHARS) -> str:
    """Текст памяти для Джинни: сводка + факты + последние реплики."""
    parts: list[str] = []
    summary = read_summary()
    if summary:
        parts.append(summary)
    facts = read_facts()
    if facts:
        parts.append("## Устойчивые факты\n" + facts)
    turns = recent_turns()
    if turns:
        lines = []
        for turn in turns:
            who = "user" if turn.get("role") == "user" else turn.get("agent", "genie")
            name = {"user": "Босс", "dron": "Дрон", "genie": "Джинни"}.get(who, "Джинни")
            lines.append(f"{name}: {turn.get('text', '')[:400]}")
        parts.append("## Последние реплики\n" + "\n".join(lines))
    block = "\n\n".join(parts).strip()
    if len(block) > limit:
        block = block[:limit] + "\n…(обрезано)"
    return block


def context_item() -> str:
    """Готовая реплика-контекст, которую Джинни видит перед ответом."""
    block = memory_block()
    if not block:
        return ""
    return (
        "ПАМЯТЬ СЕМЬИ (это не вопрос, а контекст; не пересказывай его, "
        "просто учитывай). Если нужных сведений здесь нет — вызови инструмент "
        "ask_dron и спроси Дрона, он локальный хранитель этих данных.\n\n" + block
    )


def stats() -> dict:
    turns = read_turns()
    summary = read_summary()
    return {
        "folder": str(MEMORY_DIR),
        "turns": len(turns),
        "summary_chars": len(summary),
        "facts_chars": len(read_facts()),
        "needs_compaction": len(turns) > KEEP_TURNS,
        "summary_updated": _summary_timestamp(summary),
    }


def _summary_timestamp(summary: str) -> str | None:
    for line in summary.splitlines()[:3]:
        if line.lower().startswith("обновлено:"):
            return line.split(":", 1)[1].strip()
    return None


def _transcript(turns: list[dict]) -> str:
    lines = []
    for turn in turns:
        who = "user" if turn.get("role") == "user" else turn.get("agent", "genie")
        name = {"user": "Босс", "dron": "Дрон", "genie": "Джинни"}.get(who, "Джинни")
        lines.append(f"{name}: {turn.get('text', '')}")
    return "\n".join(lines)


def _archive(turns: list[dict]) -> None:
    if not turns:
        return
    _ensure_dirs()
    stamp = datetime.now().strftime("%Y%m")
    target = ARCHIVE_DIR / f"chat-{stamp}.jsonl"
    with target.open("a", encoding="utf-8") as stream:
        for turn in turns:
            stream.write(json.dumps(turn, ensure_ascii=False) + "\n")


async def compact(model: LocalModel, *, keep: int = COMPACT_KEEP) -> dict:
    """Сжать переписку силами Дрона. Возвращает новую сводку и статистику."""
    turns = read_turns()
    if len(turns) <= keep:
        return {"ok": False, "reason": "нечего сжимать", "turns": len(turns)}

    old = turns[:-keep]
    fresh = turns[-keep:]

    prompt = COMPACT_PROMPT.format(
        previous=read_summary() or "(сводки пока нет)",
        transcript=_transcript(old)[-8000:],
    )
    try:
        answer = await dron.chat(
            model,
            "Сожми переписку в сводку по инструкции.",
            temperature=0.2,
            max_tokens=700,
            context=None,
            system_prompt=prompt,
        )
        summary_text = (answer.get("reply") or "").strip()
    except Exception as exc:  # noqa: BLE001 — память не должна ломать чат
        return {"ok": False, "reason": f"Дрон не смог сжать: {exc}", "turns": len(turns)}

    if not summary_text:
        return {"ok": False, "reason": "Дрон вернул пустую сводку", "turns": len(turns)}

    header = SUMMARY_HEADER.format(ts=_now(), count=len(old))
    _atomic_write(SUMMARY, header + summary_text.strip() + "\n")
    _archive(old)
    _atomic_write(
        CHAT_LOG,
        "".join(json.dumps(turn, ensure_ascii=False) + "\n" for turn in fresh),
    )
    return {
        "ok": True,
        "compressed": len(old),
        "kept": len(fresh),
        "summary_chars": len(summary_text),
        "summary": summary_text,
    }


async def maybe_compact(model: LocalModel) -> dict | None:
    """Сжать, только если переписка переросла порог."""
    if not needs_compaction():
        return None
    return await compact(model)
