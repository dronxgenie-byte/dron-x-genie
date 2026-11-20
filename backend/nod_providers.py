"""
NOD — база данных провайдеров, моделей, ключей, почтовых ящиков и биллинга AMD.

Хранит:
- Провайдеры (имя, тип, базовый URL, документация, как получить бесплатный API)
- Модели (имя провайдера, имя модели, лимиты, стоимость, контекстное окно, приоритет стоимости)
- Условия подключения (нужен ли ключ, как получить, лимиты free-tier)
- API ключи (ссылка на зашифрованные значения в vault)
- Здоровье ключей (история проверок)
- Лог открытий (ночной поиск)
- Mailbox (меж агентная почта: Dron ↔ NOD ↔ Kil)
- AMD billing (отслеживание бесплатных баллов AMD AI Developer Program)

Все данные хранятся в SQLite: backend/data/nod_providers.db
Режим WAL для безопасной параллельной записи от нескольких агентов.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent / "data" / "nod_providers.db"


# ---------------------------------------------------------------
# Инициализация БД
# ---------------------------------------------------------------

def get_connection() -> sqlite3.Connection:
    """Создать соединение с SQLite в режиме WAL для параллельной записи."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # WAL режим позволяет нескольким агентам писать одновременно без блокировок
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    )
    return cur.fetchone() is not None


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def migrate_db(conn: sqlite3.Connection) -> None:
    """Применить миграции к существующей БД без потери данных."""
    cur = conn.cursor()

    # Добавить cost_priority в models, если колонки нет
    if _table_exists(conn, "models") and not _column_exists(conn, "models", "cost_priority"):
        cur.execute("ALTER TABLE models ADD COLUMN cost_priority INTEGER DEFAULT 2")
        conn.commit()

    conn.commit()


def init_db() -> None:
    """Создать таблицы, если их нет, и применить миграции."""
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS providers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                display_name TEXT,
                provider_type TEXT NOT NULL,           -- 'openai', 'anthropic', 'local', 'cloud', 'aggregator', 'amd'
                base_url TEXT NOT NULL,
                auth_type TEXT DEFAULT 'none',         -- 'none', 'api_key', 'bearer', 'no_auth'
                auth_header_name TEXT DEFAULT 'Authorization',
                auth_header_prefix TEXT DEFAULT 'Bearer',
                docs_url TEXT,
                free_tier_url TEXT,                    -- куда регистрироваться за бесплатный ключ
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_id INTEGER NOT NULL,
                model_id TEXT NOT NULL,
                display_name TEXT,
                context_window INTEGER,
                max_output_tokens INTEGER,
                price_per_1k_input REAL DEFAULT 0,     -- в рублях/долларах, 0 = бесплатно
                price_per_1k_output REAL DEFAULT 0,
                is_free INTEGER DEFAULT 0,
                cost_priority INTEGER DEFAULT 2,       -- 1 = AMD бесплатные баллы, 2 = free-tier, 3 = платные
                rate_limit_rpm INTEGER DEFAULT 0,      -- запросов в минуту (0 = неизвестно)
                rate_limit_tpm INTEGER DEFAULT 0,      -- токенов в минуту
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (provider_id) REFERENCES providers(id),
                UNIQUE(provider_id, model_id)
            );

            CREATE TABLE IF NOT EXISTS provider_conditions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_id INTEGER NOT NULL,
                condition_type TEXT NOT NULL,          -- 'signup_required', 'credit_required', 'phone_required', 'no_auth'
                description TEXT,
                is_required INTEGER DEFAULT 1,
                how_to_get TEXT,                       -- инструкция как получить бесплатно
                created_at TEXT NOT NULL,
                FOREIGN KEY (provider_id) REFERENCES providers(id)
            );

            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_id INTEGER NOT NULL,
                key_name TEXT NOT NULL,                -- пользовательское имя ключа
                encrypted_key TEXT NOT NULL,           -- зашифрованный ключ (ссылка на vault)
                is_active INTEGER DEFAULT 1,
                added_at TEXT NOT NULL,
                last_checked_at TEXT,
                last_working_at TEXT,
                check_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0,
                last_error TEXT,
                notes TEXT,
                FOREIGN KEY (provider_id) REFERENCES providers(id)
            );

            CREATE TABLE IF NOT EXISTS key_health_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_id INTEGER NOT NULL,
                checked_at TEXT NOT NULL,
                is_working INTEGER NOT NULL,
                response_time_ms INTEGER,
                error_message TEXT,
                FOREIGN KEY (key_id) REFERENCES api_keys(id)
            );

            CREATE TABLE IF NOT EXISTS discovery_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_name TEXT NOT NULL,
                model_id TEXT,
                found_at TEXT NOT NULL,
                source_url TEXT,
                notes TEXT,
                added_to_db INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS mailbox (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_agent TEXT NOT NULL,              -- 'dron', 'nod', 'kil', 'traycer'
                to_agent TEXT NOT NULL,                -- целевой агент или 'broadcast'
                message_type TEXT NOT NULL,            -- 'task', 'ask', 'reply', 'status', 'heartbeat'
                subject TEXT,
                payload TEXT,                          -- JSON с телом сообщения
                correlation_id TEXT,                   -- для склейки ask→reply
                status TEXT DEFAULT 'pending',         -- pending, delivered, read, failed
                created_at TEXT NOT NULL,
                delivered_at TEXT,
                read_at TEXT
            );

            CREATE TABLE IF NOT EXISTS amd_billing (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                checked_at TEXT NOT NULL,
                remaining_tokens INTEGER,
                rps_used INTEGER,
                rps_limit INTEGER DEFAULT 20,
                daily_limit INTEGER,
                daily_used INTEGER,
                notes TEXT
            );
        """)
        # Применить миграции для существующих БД
        migrate_db(conn)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------
# Провайдеры
# ---------------------------------------------------------------

def add_provider(
    name: str,
    provider_type: str,
    base_url: str,
    *,
    display_name: str | None = None,
    auth_type: str = "none",
    auth_header_name: str = "Authorization",
    auth_header_prefix: str = "Bearer",
    docs_url: str | None = None,
    free_tier_url: str | None = None,
    notes: str | None = None,
) -> int:
    """Добавить провайдера. Вернуть его id."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        cur.execute(
            """
            INSERT INTO providers
            (name, display_name, provider_type, base_url, auth_type,
             auth_header_name, auth_header_prefix, docs_url, free_tier_url,
             notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                display_name or name,
                provider_type,
                base_url,
                auth_type,
                auth_header_name,
                auth_header_prefix,
                docs_url,
                free_tier_url,
                notes,
                now,
                now,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_provider(name: str) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        cur = conn.execute("SELECT * FROM providers WHERE name = ?", (name,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_providers() -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.execute("SELECT * FROM providers ORDER BY name")
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ---------------------------------------------------------------
# Модели
# ---------------------------------------------------------------

def add_model(
    provider_name: str,
    model_id: str,
    *,
    display_name: str | None = None,
    context_window: int | None = None,
    max_output_tokens: int | None = None,
    price_per_1k_input: float = 0.0,
    price_per_1k_output: float = 0.0,
    is_free: bool = False,
    cost_priority: int = 2,
    rate_limit_rpm: int = 0,
    rate_limit_tpm: int = 0,
    notes: str | None = None,
) -> int:
    conn = get_connection()
    try:
        prov = get_provider(provider_name)
        if not prov:
            raise ValueError(f"Провайдер '{provider_name}' не найден")
        now = datetime.now(timezone.utc).isoformat()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO models
            (provider_id, model_id, display_name, context_window,
             max_output_tokens, price_per_1k_input, price_per_1k_output,
             is_free, cost_priority, rate_limit_rpm, rate_limit_tpm, notes,
             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                prov["id"],
                model_id,
                display_name or model_id,
                context_window,
                max_output_tokens,
                price_per_1k_input,
                price_per_1k_output,
                1 if is_free else 0,
                cost_priority,
                rate_limit_rpm,
                rate_limit_tpm,
                notes,
                now,
                now,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_models(provider_name: str | None = None) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        if provider_name:
            cur = conn.execute(
                """
                SELECT m.*, p.name AS provider_name
                FROM models m
                JOIN providers p ON m.provider_id = p.id
                WHERE p.name = ?
                ORDER BY m.cost_priority ASC, m.model_id
                """,
                (provider_name,),
            )
        else:
            cur = conn.execute(
                """
                SELECT m.*, p.name AS provider_name
                FROM models m
                JOIN providers p ON m.provider_id = p.id
                ORDER BY m.cost_priority ASC, p.name, m.model_id
                """
            )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_models_by_priority(priority: int) -> list[dict[str, Any]]:
    """Получить все модели с указанным приоритетом стоимости.

    Приоритеты:
      1 — AMD бесплатные баллы (высший приоритет)
      2 — free-tier провайдеры
      3 — платные API
    """
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT m.*, p.name AS provider_name
            FROM models m
            JOIN providers p ON m.provider_id = p.id
            WHERE m.cost_priority = ?
            ORDER BY p.name, m.model_id
            """,
            (priority,),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ---------------------------------------------------------------
# API ключи (ссылка на зашифрованные значения в vault)
# ---------------------------------------------------------------

def add_api_key(
    provider_name: str,
    key_name: str,
    encrypted_key: str,
    *,
    notes: str | None = None,
) -> int:
    """Добавить ключ (зашифрованное значение хранится в vault, здесь только id ссылки)."""
    conn = get_connection()
    try:
        prov = get_provider(provider_name)
        if not prov:
            raise ValueError(f"Провайдер '{provider_name}' не найден")
        now = datetime.now(timezone.utc).isoformat()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO api_keys
            (provider_id, key_name, encrypted_key, added_at)
            VALUES (?, ?, ?, ?)
            """,
            (prov["id"], key_name, encrypted_key, now),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_keys(provider_name: str | None = None) -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        if provider_name:
            cur = conn.execute(
                """
                SELECT k.*, p.name AS provider_name
                FROM api_keys k
                JOIN providers p ON k.provider_id = p.id
                WHERE p.name = ?
                ORDER BY k.added_at DESC
                """,
                (provider_name,),
            )
        else:
            cur = conn.execute(
                """
                SELECT k.*, p.name AS provider_name
                FROM api_keys k
                JOIN providers p ON k.provider_id = p.id
                ORDER BY k.added_at DESC
                """
            )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ---------------------------------------------------------------
# Здоровье ключей
# ---------------------------------------------------------------

def record_key_health(
    key_id: int,
    *,
    is_working: bool,
    response_time_ms: int | None = None,
    error_message: str | None = None,
) -> None:
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO key_health_log
            (key_id, checked_at, is_working, response_time_ms, error_message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (key_id, now, 1 if is_working else 0, response_time_ms, error_message),
        )
        # Обновить сводку в api_keys
        if is_working:
            cur.execute(
                """
                UPDATE api_keys
                SET last_checked_at = ?, last_working_at = ?,
                    check_count = check_count + 1, success_count = success_count + 1,
                    last_error = NULL
                WHERE id = ?
                """,
                (now, now, key_id),
            )
        else:
            cur.execute(
                """
                UPDATE api_keys
                SET last_checked_at = ?,
                    check_count = check_count + 1, fail_count = fail_count + 1,
                    last_error = ?
                WHERE id = ?
                """,
                (now, error_message, key_id),
            )
        conn.commit()
    finally:
        conn.close()


def get_key_health(key_id: int) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT k.*, p.name AS provider_name
            FROM api_keys k
            JOIN providers p ON k.provider_id = p.id
            WHERE k.id = ?
            """,
            (key_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_working_keys(provider_name: str | None = None) -> list[dict[str, Any]]:
    """Вернуть ключи, у которых success_count > fail_count (или нет неудач)."""
    conn = get_connection()
    try:
        if provider_name:
            cur = conn.execute(
                """
                SELECT k.*, p.name AS provider_name
                FROM api_keys k
                JOIN providers p ON k.provider_id = p.id
                WHERE k.is_active = 1
                  AND (p.name = ?)
                  AND (k.success_count > 0 OR k.check_count = 0)
                ORDER BY k.success_count DESC, k.fail_count ASC
                """,
                (provider_name,),
            )
        else:
            cur = conn.execute(
                """
                SELECT k.*, p.name AS provider_name
                FROM api_keys k
                JOIN providers p ON k.provider_id = p.id
                WHERE k.is_active = 1
                  AND (k.success_count > 0 OR k.check_count = 0)
                ORDER BY k.success_count DESC, k.fail_count ASC
                """
            )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ---------------------------------------------------------------
# Лог открытий (ночной поиск)
# ---------------------------------------------------------------

def add_discovery(
    provider_name: str,
    *,
    model_id: str | None = None,
    source_url: str | None = None,
    notes: str | None = None,
    added_to_db: bool = False,
) -> int:
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO discovery_log
            (provider_name, model_id, found_at, source_url, notes, added_to_db)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (provider_name, model_id, now, source_url, notes, 1 if added_to_db else 0),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


# ---------------------------------------------------------------
# Mailbox — межагентная почта
# ---------------------------------------------------------------

def send_mail(
    from_agent: str,
    to_agent: str,
    message_type: str,
    *,
    subject: str | None = None,
    payload: str | None = None,
    correlation_id: str | None = None,
) -> int:
    """Отправить сообщение в mailbox. Вернуть id сообщения."""
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO mailbox
            (from_agent, to_agent, message_type, subject, payload,
             correlation_id, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                from_agent,
                to_agent,
                message_type,
                subject,
                payload,
                correlation_id,
                "pending",
                now,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_mail(
    agent: str,
    *,
    message_type: str | None = None,
    status: str = "pending",
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Получить непрочитанные сообщения для агента."""
    conn = get_connection()
    try:
        if message_type:
            cur = conn.execute(
                """
                SELECT * FROM mailbox
                WHERE to_agent = ? AND status = ?
                  AND (? IS NULL OR message_type = ?)
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (agent, status, message_type, message_type, limit),
            )
        else:
            cur = conn.execute(
                """
                SELECT * FROM mailbox
                WHERE to_agent = ? AND status = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (agent, status, limit),
            )
        rows = cur.fetchall()
        # Пометить как доставленные
        for row in rows:
            conn.execute(
                "UPDATE mailbox SET status = 'delivered', delivered_at = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), row["id"]),
            )
        conn.commit()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def reply(
    original_id: int,
    from_agent: str,
    to_agent: str,
    *,
    subject: str | None = None,
    payload: str | None = None,
) -> int:
    """Ответить на сообщение, создав новое с correlation_id = original_id."""
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO mailbox
            (from_agent, to_agent, message_type, subject, payload,
             correlation_id, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                from_agent,
                to_agent,
                "reply",
                subject,
                payload,
                str(original_id),
                "pending",
                now,
            ),
        )
        # Пометить оригинал как прочитанный
        cur.execute(
            "UPDATE mailbox SET status = 'read', read_at = ? WHERE id = ?",
            (now, original_id),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def mark_mail_read(mail_id: int) -> None:
    """Пометить сообщение как прочитанное."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE mailbox SET status = 'read', read_at = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), mail_id),
        )
        conn.commit()
    finally:
        conn.close()


def list_mailbox(
    agent: str | None = None,
    *,
    status: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Список сообщений mailbox (для администрирования)."""
    conn = get_connection()
    try:
        query = "SELECT * FROM mailbox WHERE 1=1"
        params: list[Any] = []
        if agent:
            query += " AND (from_agent = ? OR to_agent = ?)"
            params.extend([agent, agent])
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        cur = conn.execute(query, params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ---------------------------------------------------------------
# AMD Billing — отслеживание бесплатных баллов AMD
# ---------------------------------------------------------------

def record_amd_billing(
    *,
    remaining_tokens: int | None = None,
    rps_used: int | None = None,
    rps_limit: int = 20,
    daily_limit: int | None = None,
    daily_used: int | None = None,
    notes: str | None = None,
) -> int:
    """Записать текущее состояние AMD биллинга."""
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO amd_billing
            (checked_at, remaining_tokens, rps_used, rps_limit,
             daily_limit, daily_used, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now,
                remaining_tokens,
                rps_used,
                rps_limit,
                daily_limit,
                daily_used,
                notes,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_latest_amd_billing() -> dict[str, Any] | None:
    """Получить последнюю запись AMD биллинга."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT * FROM amd_billing
            ORDER BY checked_at DESC
            LIMIT 1
            """
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_amd_billing(limit: int = 50) -> list[dict[str, Any]]:
    """История записей AMD биллинга."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT * FROM amd_billing
            ORDER BY checked_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ---------------------------------------------------------------
# Инициализация при импорте
# ---------------------------------------------------------------
init_db()
