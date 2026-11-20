"""Чтение финансов из Vault: взносы, расходы, перенос остатка.

Источник истины — Markdown в `60_FINANCE/<ГГГГ-ММ>/`.
База данных здесь не используется.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from .config import Paths
from .vault import READY, MISSING, UNAVAILABLE, is_readable, parse_frontmatter

PERIOD_RE = re.compile(r"^\d{4}-\d{2}$")
MONEY_RE = re.compile(r"^-?\d+$")


def current_period() -> str:
    today = date.today()
    return f"{today.year:04d}-{today.month:02d}"


def available_periods(paths: Paths) -> list[str]:
    if not paths.finance.is_dir():
        return []
    try:
        names = [p.name for p in paths.finance.iterdir() if p.is_dir() and PERIOD_RE.match(p.name)]
    except OSError:
        return []
    return sorted(names)


def _to_int(value) -> int | None:
    text = str(value or "").strip().replace(" ", "").replace("₽", "").replace(",", "")
    return int(text) if MONEY_RE.match(text) else None


def _table_rows(body: str) -> list[list[str]]:
    """Достать строки ПЕРВОЙ Markdown-таблицы как списки ячеек.

    Разбор останавливается на первой непустой строке вне таблицы: иначе в
    список взносов попадает таблица «Сводка месяца» и суммы задваиваются.
    """
    rows: list[list[str]] = []
    started = False

    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            if started:
                break
            continue

        started = True
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not cells:
            continue
        if all(set(c) <= {"-", ":", " "} for c in cells if c):
            continue
        rows.append(cells)

    return rows


def _clean(text: str) -> str:
    return text.replace("*", "").replace("`", "").strip()


def _read_month(paths: Paths, period: str) -> dict:
    folder = paths.finance / period
    result = {
        "period": period,
        "contributions": [],
        "contributions_total": 0,
        "expenses": [],
        "expenses_total": 0,
        "opening_balance": None,
        "demo_present": False,
        "files": [],
        "status": READY,
    }

    if not folder.is_dir():
        result["status"] = MISSING
        return result

    try:
        files = sorted(folder.glob("*.md"))
    except OSError:
        result["status"] = UNAVAILABLE
        return result

    for file in files:
        if not is_readable(file, paths):
            continue
        try:
            content = file.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            continue

        meta, body = parse_frontmatter(content)
        kind = str(meta.get("type") or "")
        total = _to_int(meta.get("total"))
        demo = str(meta.get("demo") or "").lower() == "true"

        result["files"].append(file.name)
        if demo:
            result["demo_present"] = True

        if kind == "finance_contributions":
            if total is not None:
                result["contributions_total"] += total
            for row in _table_rows(body):
                if len(row) < 2:
                    continue
                who = _clean(row[0])
                amount = _to_int(row[1])
                if not who or amount is None:
                    continue
                if who.lower().startswith(("итого", "показатель", "кто")):
                    continue
                result["contributions"].append({"who": who, "rub": amount})

        elif kind == "finance_expenses":
            category = _clean(str(meta.get("category") or file.stem))
            if total is not None:
                result["expenses_total"] += total
                result["expenses"].append(
                    {"category": category, "rub": total, "demo": demo, "file": file.name}
                )

        elif kind == "finance_opening":
            opening = _to_int(meta.get("opening_balance"))
            if opening is not None:
                result["opening_balance"] = opening

    closing = (result["opening_balance"] or 0) + result["contributions_total"] - result["expenses_total"]
    result["closing_balance"] = closing
    return result


def month_summary(paths: Paths, period: str | None = None) -> dict:
    """Сводка за месяц: взносы, расходы, остаток."""
    if not paths.finance.is_dir():
        return {
            "status": MISSING,
            "currency": "RUB",
            "periods": [],
            "month": None,
        }

    periods = available_periods(paths)
    today_period = current_period()

    # Приоритет: текущий месяц, если он есть. Иначе последний доступный.
    # Иначе совет в октябре показывал бы ноябрь — месяц, которого ещё нет.
    if period:
        chosen = period
    elif today_period in periods:
        chosen = today_period
    elif periods:
        chosen = periods[-1]
    else:
        chosen = today_period

    month = _read_month(paths, chosen)
    return {
        "status": month["status"],
        "currency": "RUB",
        "periods": periods,
        "period": chosen,
        "current_period": today_period,
        "month": month,
    }


def carry_over(paths: Paths, period: str) -> int | None:
    """Входящий остаток месяца (перенос из предыдущего)."""
    folder = paths.finance / period
    if not folder.is_dir():
        return None
    try:
        files = sorted(folder.glob("*.md"))
    except OSError:
        return None

    for file in files:
        if not is_readable(file, paths):
            continue
        try:
            content = file.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            continue
        meta, _ = parse_frontmatter(content)
        if str(meta.get("type") or "") == "finance_opening":
            return _to_int(meta.get("opening_balance"))
    return None
