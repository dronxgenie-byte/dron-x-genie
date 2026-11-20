"""HTTP-маршруты ANANISIM OS."""

from __future__ import annotations

import base64
import json
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse

from . import comms, council, dron, finance, genie, genie_memory, stt, vault, voice, pi_dron, providers_registry
from .config import load_cloud, load_local_model, load_paths, load_settings, save_settings
from .models import ChatRequest, GenieChatRequest, SettingsPatch, SpeakRequest, SttRequest
from agent_x import AgentX
from .pi_dron import get_pidron, PIDronError, get_execution_mode, load_prompt

router = APIRouter(prefix="/api")

PHRASES_FILE = Path(__file__).resolve().parents[2] / "prompts" / "phrases.json"

READY = "ready"
UNAVAILABLE = "unavailable"
UNCONFIGURED = "unconfigured"
UNKNOWN = "unknown"
NOT_IMPLEMENTED = "not_implemented"


def fail(status: int, code: str, message: str, retryable: bool = False) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "retryable": retryable}},
    )


def _db_status(paths) -> str:
    if paths.db is None:
        return UNCONFIGURED
    return READY if paths.db.is_file() else UNAVAILABLE


def _dashboard_payload(request: Request) -> dict:
    paths = load_paths()
    settings = load_settings(paths)

    tasks, tasks_status = vault.read_tasks(paths)
    events, schedule_status = vault.read_events(paths)

    open_tasks = [t for t in tasks if not t.done]

    return {
        "timezone": settings.get("timezone", "Europe/Moscow"),
        "generated_at": vault.now_iso(),
        "events": [
            {
                "id": e.id,
                "title": e.title,
                "date": e.date,
                "time": e.time,
                "duration_minutes": e.duration_minutes,
                "participants": e.participants,
                "body": e.body,
                "source": e.source,
            }
            for e in events
        ],
        "tasks": [
            {"id": t.id, "text": t.text, "source": t.source} for t in open_tasks
        ],
        "reminders": [],
        "reminders_status": UNCONFIGURED,
        "vanya": None,
        "vanya_status": UNCONFIGURED,
        "sources": {
            "schedule": schedule_status,
            "tasks": tasks_status,
            "database": _db_status(paths),
            "reminders": UNCONFIGURED,
        },
    }


@router.get("/health")
async def health() -> dict:
    paths = load_paths()
    settings = load_settings(paths)
    model = load_local_model()
    cloud = load_cloud()

    components = {
        "database": _db_status(paths),
        "vault": vault.vault_status(paths),
        "dron": await dron.status(model),
        "genie": READY if cloud.configured else UNCONFIGURED,
        "voice": voice.status(paths)["status"],
        "stt": stt.status()["status"],
    }

    # База пока не создаётся намеренно (решение Андрея): её отсутствие —
    # это не деградация системы, а незаполненный источник данных.
    optional = {"database"}
    degraded = any(
        state != READY and name not in optional for name, state in components.items()
    )

    return {
        "status": "degraded" if degraded else "ready",
        "components": components,
        "checked_at": vault.now_iso(),
        "agent_model": model.model,
        "voice_model": settings.get("voice_model"),
        "genie_model": cloud.realtime_model,
        "genie_prompt_id": cloud.prompt_id,
        "default_agent": settings.get("default_agent"),
    }


@router.get("/dashboard")
async def dashboard(request: Request) -> dict:
    return _dashboard_payload(request)


@router.get("/finance")
async def finance_summary(period: str | None = Query(default=None, max_length=7)) -> dict:
    paths = load_paths()
    return finance.month_summary(paths, period)


@router.get("/council")
async def council_view(day: str | None = Query(default=None, max_length=10)) -> dict:
    """Семейный совет: повестка вечера, финансы, задачи на завтра, валюта."""
    paths = load_paths()
    settings = load_settings(paths)
    today = date.today()
    tomorrow = (today + timedelta(days=1)).isoformat()

    tasks, tasks_status = vault.read_tasks(paths)
    events, schedule_status = vault.read_events(paths)

    open_tasks = [t for t in tasks if not t.done]
    done_tasks = [t for t in tasks if t.done]

    tomorrow_events = [e for e in events if e.date == tomorrow]

    note = council.read_council(paths, day)
    money = finance.month_summary(paths)

    return {
        "date": today.isoformat(),
        "tomorrow": tomorrow,
        "timezone": settings.get("timezone", "Europe/Moscow"),
        "generated_at": vault.now_iso(),
        "council": note,
        "finance": money,
        "tasks_tomorrow": [
            {"id": t.id, "text": t.text, "source": t.source} for t in open_tasks
        ],
        "schedule_tomorrow": [
            {
                "id": e.id,
                "title": e.title,
                "time": e.time,
                "duration_minutes": e.duration_minutes,
                "participants": e.participants,
            }
            for e in tomorrow_events
        ],
        "done_today": [
            {"id": t.id, "text": t.text, "source": t.source} for t in done_tasks
        ],
        "sources": {
            "council": note.get("status"),
            "tasks": tasks_status,
            "schedule": schedule_status,
            "finance": money.get("status"),
        },
        "anis": {
            "status": UNCONFIGURED,
            "symbol": "₳",
            "rate_to_rub": 1,
            "reason": "Журнал операций ₳ появится на этапе F. Балансы пока не ведутся.",
            "balances": [],
        },
        "voting": {
            "rule": "Решающий голос — у того, у кого больше ₳.",
            "available": False,
            "reason": "Голос не подсчитан: балансы ₳ не ведутся. Появится вместе с журналом на этапе F.",
            "deciding_participant": None,
        },
    }


@router.get("/ivan")
async def ivan_app() -> dict:
    """I.VAN — учебное приложение Вани: уроки, расписание, задачи, заметки."""
    paths = load_paths()
    settings = load_settings(paths)

    tasks, tasks_status = vault.read_tasks(paths)
    events, schedule_status = vault.read_events(paths)
    notes, notes_status = vault.list_notes(paths, paths.vanya)

    vanya_events = [
        {
            "id": e.id,
            "title": e.title,
            "date": e.date,
            "time": e.time,
            "duration_minutes": e.duration_minutes,
        }
        for e in events
        if "vanya" in [p.lower() for p in e.participants]
    ]

    return {
        "timezone": settings.get("timezone", "Europe/Moscow"),
        "generated_at": vault.now_iso(),
        "lessons": [],
        "lessons_status": UNCONFIGURED,
        "homework": [
            {"id": t.id, "text": t.text, "source": t.source} for t in tasks if not t.done
        ],
        "homework_status": tasks_status,
        "schedule": vanya_events,
        "schedule_status": schedule_status,
        "notes": notes,
        "notes_status": notes_status,
        "anis": {
            "status": UNCONFIGURED,
            "symbol": "₳",
            "reason": "Баланс Вани появится вместе с журналом ₳ на этапе F.",
        },
        "sources": {
            "lessons": UNCONFIGURED,
            "homework": tasks_status,
            "schedule": schedule_status,
            "notes": notes_status,
        },
    }


@router.get("/settings")
async def get_settings() -> dict:
    paths = load_paths()
    return load_settings(paths)


@router.patch("/settings")
async def patch_settings(patch: SettingsPatch) -> dict:
    paths = load_paths()
    settings = load_settings(paths)

    updates = patch.model_dump(exclude_none=True)
    if not updates:
        return settings

    settings.update(updates)
    save_settings(paths, settings)
    return load_settings(paths)


def _dron_kwargs(paths) -> dict:
    settings = load_settings(paths)
    return {
        "temperature": float(settings.get("dron_temperature", 0.35)),
        "max_tokens": int(settings.get("dron_max_tokens", 220)),
    }


@router.post("/dron/chat")
async def dron_chat(body: ChatRequest, background: BackgroundTasks):
    model = load_local_model()
    paths = load_paths()
    history = [turn.model_dump() for turn in body.history]

    # Команды связи Дрон выполняет сам, без модели: звонок и отправка сообщения.
    command = comms.parse_command(body.message)
    if command:
        result = await comms.run_command(command)
        if result.get("ok"):
            action = "Звоню" if command.get("action") == "call" else "Отправил"
            target = result.get("to") or ""
            suffix = " (черновик: COMMS_DRY_RUN=1)" if result.get("dry_run") else ""
            return {
                "reply": f"{action}, Босс: {target}{suffix}.",
                "agent": "dron",
                "model": "comms",
                "action": result,
            }
        return {
            "reply": f"Не вышло, чёрт побери: {result.get('error')}",
            "agent": "dron",
            "model": "comms",
            "action": result,
        }

    try:
        mode = get_execution_mode()
        system_prompt = load_prompt(f"system_{mode.lower()}.md")
        answer = await dron.chat(
            model, body.message, history,
            system_prompt=system_prompt, **_dron_kwargs(paths),
        )
        try:
            genie_memory.append_turn("user", body.message, agent="dron")
            genie_memory.append_turn(
                "assistant", answer.get("reply") or "", agent="dron"
            )
            background.add_task(genie_memory.maybe_compact, model)
        except Exception:  # noqa: BLE001 — память не критична
            pass
        return answer
    except ValueError as exc:
        return fail(422, "INVALID_MESSAGE", str(exc))
    except RuntimeError as exc:
        return fail(503, "DRON_UNAVAILABLE", str(exc), retryable=True)
    except Exception as exc:  # сетевые сбои httpx и прочее
        return fail(503, "DRON_UNAVAILABLE", f"Локальная модель недоступна: {exc}", retryable=True)




async def _ask_dron_for_genie(item: dict) -> str | None:
    """Подпольный канал: Джинни спрашивает Дрона через function_call."""
    try:
        arguments = json.loads(item.get("arguments") or "{}")
    except json.JSONDecodeError:
        arguments = {}
    if not isinstance(arguments, dict):
        arguments = {}
    question = str(
        arguments.get("question") or arguments.get("query") or arguments.get("text") or ""
    ).strip()
    if not question:
        return None
    model = load_local_model()
    paths = load_paths()
    mode = get_execution_mode()
    system_prompt = load_prompt(f"system_{mode.lower()}.md")
    answer = await dron.chat(model, question, None, system_prompt=system_prompt, **_dron_kwargs(paths))
    return (answer.get("reply") or "").strip() or None


def _memory_context() -> str | None:
    try:
        block = genie_memory.context_item()
    except Exception:  # noqa: BLE001 — память не должна ломать чат
        return None
    return block or None


@router.post("/genie/chat")
async def genie_chat(body: GenieChatRequest, background: BackgroundTasks):
    """Текстовый ход к облачной Джинни: память, голос и подпольный канал к Дрону."""
    cloud = load_cloud()
    history = [turn.model_dump() for turn in body.history]
    try:
        result = await genie.chat(
            cloud,
            body.message,
            history,
            with_audio=body.with_audio,
            memory=_memory_context(),
            tool_handler=_ask_dron_for_genie,
        )
    except ValueError as exc:
        return fail(422, "INVALID_MESSAGE", str(exc))
    except genie.GenieError as exc:
        return fail(503, "GENIE_UNAVAILABLE", str(exc), retryable=True)
    except Exception as exc:  # сетевые сбои aiohttp и прочее
        return fail(503, "GENIE_UNAVAILABLE", f"Облачный Джинн недоступен: {exc}", retryable=True)

    try:
        genie_memory.append_turn("user", body.message)
        genie_memory.append_turn("assistant", result.reply, agent="genie")
        background.add_task(genie_memory.maybe_compact, load_local_model())
    except Exception:  # noqa: BLE001 — память не критична
        pass

    return {
        "reply": result.reply,
        "agent": "genie",
        "model": result.model,
        "session_id": result.session_id,
        "usage": result.usage,
        "audio_wav": (
            base64.b64encode(result.audio_wav).decode("ascii") if result.audio_wav else None
        ),
    }


@router.get("/genie/status")
async def genie_status(probe: bool = Query(default=False)):
    """Состояние Джинни. probe=1 — живая проверка сессии (тратит запрос)."""
    cloud = load_cloud()
    state = genie.status(cloud)
    if probe and state == READY:
        state = await genie.probe(cloud)

    return {
        "status": state,
        "api_key_set": cloud.api_key_set,
        "folder_id": cloud.folder_id,
        "prompt_id": cloud.prompt_id,
        "realtime_model": cloud.realtime_model,
        "text_model": cloud.text_model,
        "voice_channel": "/ws/genie",
        "audio_format": {"type": "pcm16", "rate": 44100, "channels": 1},
    }


@router.post("/duet")
async def duet_chat(body: ChatRequest, background: BackgroundTasks):
    """Дуэт: Джинни отвечает первой, Дрон комментирует её ответ.

    Оба хода попадают в память Джинни; когда переписка разрастается,
    Дрон сам сжимает её в сводку.
    """
    paths = load_paths()
    model = load_local_model()
    cloud = load_cloud()
    history = [turn.model_dump() for turn in body.history]

    # Команда связи — работа Дрона: звонит он, Джинни не перехватывает.
    command = comms.parse_command(body.message)
    if command:
        result = await comms.run_command(command)
        skipped = {
            "agent": "genie",
            "status": "skipped",
            "reply": None,
            "reason": "команда связи — выполняет Дрон",
        }
        if result.get("ok"):
            action = "Звоню" if command.get("action") == "call" else "Отправил"
            target = result.get("to") or command.get("contact") or ""
            mark = " (черновик: COMMS_DRY_RUN=1)" if result.get("dry_run") else ""
            return {
                "genie": skipped,
                "dron": {
                    "reply": f"{action}, Босс: {target}{mark}.",
                    "agent": "dron",
                    "model": "comms",
                    "action": result,
                },
            }
        return {
            "genie": skipped,
            "dron": {
                "reply": f"Не вышло, чёрт побери: {result.get('error')}",
                "agent": "dron",
                "model": "comms",
                "action": result,
            },
        }

    genie_state = {
        "agent": "genie",
        "status": READY if cloud.configured else UNCONFIGURED,
        "reply": None,
        "reason": None,
    }

    if not cloud.configured:
        genie_state["reason"] = (
            "Облачный Джин не настроен: нет рабочего ключа Yandex. "
            "Ритуал и голос — после подключения ключа."
        )
    else:
        try:
            result = await genie.chat(
                cloud,
                body.message,
                history,
                memory=_memory_context(),
                tool_handler=_ask_dron_for_genie,
            )
            genie_state["status"] = READY
            genie_state["reply"] = result.reply
            genie_state["model"] = result.model
        except genie.GenieError as exc:
            genie_state["status"] = UNAVAILABLE
            genie_state["reason"] = str(exc)
        except Exception as exc:  # noqa: BLE001
            genie_state["status"] = UNAVAILABLE
            genie_state["reason"] = f"Облачный Джинн недоступен: {exc}"

    context = genie_state.get("reply") if genie_state["status"] == READY else None

    try:
        answer = await dron.chat(
            model,
            body.message,
            history,
            context=context,
            system_prompt=load_prompt(f"system_{get_execution_mode().lower()}.md"),
            **_dron_kwargs(paths),
        )
        try:
            genie_memory.append_turn("user", body.message)
            if genie_state.get("reply"):
                genie_memory.append_turn("assistant", genie_state["reply"], agent="genie")
            genie_memory.append_turn("assistant", answer.get("reply") or "", agent="dron")
            background.add_task(genie_memory.maybe_compact, model)
        except Exception:  # noqa: BLE001
            pass
        return {"genie": genie_state, "dron": answer}
    except ValueError as exc:
        return fail(422, "INVALID_MESSAGE", str(exc))
    except Exception as exc:
        return {
            "genie": genie_state,
            "dron": {"agent": "dron", "reply": None, "error": str(exc)},
        }


@router.post("/dron/speak")
async def dron_speak(body: SpeakRequest):
    paths = load_paths()
    settings = load_settings(paths)

    text = body.text.strip()
    if not text:
        return fail(422, "EMPTY_TEXT", "Нечего озвучивать.")

    try:
        audio = voice.synthesize(
            paths,
            text=text,
            model_name=str(settings.get("voice_model") or "ru_RU-ruslan-medium"),
            length_scale=float(settings.get("voice_length_scale") or 1.0),
            pitch_factor=float(settings.get("voice_pitch_factor") or 1.0),
            bass_gain=int(settings.get("voice_bass_gain") or 0),
        )
    except FileNotFoundError as exc:
        return fail(503, "VOICE_MODEL_MISSING", str(exc), retryable=False)
    except ValueError as exc:
        return fail(422, "INVALID_TEXT", str(exc))
    except Exception as exc:
        return fail(503, "VOICE_UNAVAILABLE", f"Синтез не удался: {exc}", retryable=True)

    return Response(
        content=audio,
        media_type="audio/wav",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/voice")
async def voice_info() -> dict:
    paths = load_paths()
    settings = load_settings(paths)
    info = voice.status(paths)
    info["active_model"] = settings.get("voice_model")
    info["autoplay"] = settings.get("voice_autoplay", True)
    return info


@router.get("/stt")
async def stt_info() -> dict:
    return stt.status()


@router.post("/stt")
async def stt_transcribe(body: SttRequest):
    """Распознать речь из аудио, присланного браузером."""
    try:
        return stt.transcribe(body.audio, body.format)
    except ValueError as exc:
        return fail(422, "INVALID_AUDIO", str(exc))
    except Exception as exc:
        return fail(503, "STT_UNAVAILABLE", f"Распознавание не удалось: {exc}", retryable=True)


@router.get("/phrases")
async def phrases() -> dict:
    try:
        return json.loads(PHRASES_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return fail(404, "PHRASES_MISSING", "Фразы не найдены.")
    except ValueError as exc:
        return fail(500, "PHRASES_INVALID", f"Файл фраз повреждён: {exc}")


@router.get("/note")
async def note(path: str = Query(min_length=1, max_length=300)) -> dict:
    paths = load_paths()
    try:
        return vault.read_note(paths, path)
    except vault.VaultError as exc:
        return fail(403, "PATH_FORBIDDEN", str(exc))


@router.post("/client-log")
async def client_log(body: dict) -> dict:
    """Журнал ошибок клиента: помогает ловить сбои интерфейса без консоли."""
    log_dir = Path(__file__).resolve().parents[2] / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "stage": str(body.get("stage", ""))[:80],
        "message": str(body.get("message", ""))[:2000],
        "stack": str(body.get("stack", ""))[:4000],
    }
    with (log_dir / "client.log").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return {"ok": True}


@router.get("/contacts")
async def contacts_list() -> dict:
    """Телефонная книжка Дрона: имя → номер или chat_id."""
    contacts = comms.load_contacts()
    return {"contacts": contacts, "total": len(contacts)}


@router.post("/contacts")
async def contacts_add(body: dict) -> dict:
    """Добавить контакт: {"name": "мама", "value": "+7916...", "channel": "phone"}"""
    return comms.save_contact(
        str(body.get("name") or ""),
        str(body.get("value") or ""),
        str(body.get("channel") or "phone"),
    )


@router.delete("/contacts/{name}")
async def contacts_delete(name: str) -> dict:
    return comms.delete_contact(name)


@router.get("/comms/status")
async def comms_status() -> dict:
    """Готовность каналов связи: телефон, Telegram, MAX, WhatsApp."""
    return comms.status()


@router.get("/comms/log")
async def comms_log(limit: int = Query(default=20, ge=1, le=200)) -> dict:
    """Журнал попыток связи — что звонили и что отправляли."""
    return {"entries": comms.log_tail(limit)}


@router.post("/comms/send")
async def comms_send(body: dict) -> dict:
    """Отправить сообщение в выбранный канал."""
    return await comms.send(
        str(body.get("channel") or ""),
        str(body.get("to") or ""),
        str(body.get("text") or ""),
    )


@router.post("/comms/call")
async def comms_call(body: dict) -> dict:
    """Позвонить с сопряжённого телефона."""
    number = str(body.get("number") or body.get("to") or "").strip()
    if not number:
        return fail(422, "EMPTY_NUMBER", "Нужен номер телефона.")
    return await comms.call(number, reason=body.get("reason"))


@router.get("/memory")
async def memory_status() -> dict:
    """Состояние долговременной памяти Джинни."""
    return genie_memory.stats()


@router.get("/memory/summary")
async def memory_summary() -> dict:
    """Сводка памяти и последние реплики."""
    return {
        "summary": genie_memory.read_summary(),
        "facts": genie_memory.read_facts(),
        "recent": genie_memory.recent_turns(10),
        "stats": genie_memory.stats(),
    }


@router.post("/memory/compact")
async def memory_compact() -> dict:
    """Сжать переписку в сводку силами Дрона — вручную, не дожидаясь порога."""
    try:
        return await genie_memory.compact(load_local_model())
    except Exception as exc:  # noqa: BLE001
        return fail(503, "MEMORY_COMPACT_FAILED", str(exc), retryable=True)


@router.post("/memory/fact")
async def memory_add_fact(body: dict) -> dict:
    """Добавить устойчивый факт в память Джинни."""
    genie_memory.add_fact(str(body.get("text") or ""))
    return genie_memory.stats()


@router.post("/bridge/ask-dron")
async def bridge_ask_dron(body: dict) -> dict:
    """Подпольный канал Джинни → Дрон: спросить локального хранителя."""
    question = str(body.get("question") or "").strip()
    if not question:
        return fail(422, "EMPTY_QUESTION", "Пустой вопрос.")
    try:
        model = load_local_model()
        answer = await dron.chat(model, question, None, **_dron_kwargs(load_paths()))
    except Exception as exc:  # noqa: BLE001
        return fail(503, "DRON_UNAVAILABLE", str(exc), retryable=True)
    genie_memory.append_turn("user", question, agent="genie", source="bridge")
    genie_memory.append_turn(
        "assistant", answer.get("reply") or "", agent="dron", source="bridge"
    )
    return {
        "from": "genie",
        "to": "dron",
        "question": question,
        "answer": answer.get("reply"),
        "model": answer.get("model"),
    }


@router.post("/bridge/ask-genie")
async def bridge_ask_genie(body: dict) -> dict:
    """Подпольный канал Дрон → Джинни: локальный агент спрашивает облачную."""
    question = str(body.get("question") or "").strip()
    if not question:
        return fail(422, "EMPTY_QUESTION", "Пустой вопрос.")
    cloud = load_cloud()
    try:
        result = await genie.chat(
            cloud,
            question,
            None,
            memory=_memory_context(),
            tool_handler=_ask_dron_for_genie,
        )
    except genie.GenieError as exc:
        return fail(503, "GENIE_UNAVAILABLE", str(exc), retryable=True)
    genie_memory.append_turn("user", question, agent="dron", source="bridge")
    genie_memory.append_turn("assistant", result.reply, agent="genie", source="bridge")
    return {
        "from": "dron",
        "to": "genie",
        "question": question,
        "answer": result.reply,
        "model": result.model,
    }


@router.post("/notes")
async def create_note(body: dict):
    """Создание заметки. Реализуется на этапе C — сейчас честный отказ."""
    return fail(
        501,
        "NOT_IMPLEMENTED",
        "Создание заметок появится на этапе C. Пока функция не работает.",
    )


@router.post("/chat")
async def x_chat(body: dict) -> dict:
    """Маршрут для агента X — лёгкий роутер через NOD."""
    query = str(body.get("query") or "").strip()
    agent = str(body.get("agent") or "").strip()
    if agent != "x":
        return fail(
            400,
            "WRONG_AGENT",
            f"Маршрут /chat обслуживает только агента 'x', получен: {agent or '<пусто>'}",
        )
    agent_x = AgentX()
    return agent_x.handle_request(query)


# ===== РЕЕСТР ПРОВАЙДЕРОВ (таблица моделей, подписок и проверок) =====

@router.get("/providers/registry")
async def providers_registry_view() -> dict:
    """Таблица провайдеров и моделей: план, лимиты, доступность в РФ, статус."""
    return providers_registry.registry_view()


@router.post("/providers/refresh")
async def providers_refresh() -> dict:
    """Проверить всех провайдеров реальными запросами и обновить каталог из сети."""
    return await providers_registry.refresh()


@router.patch("/providers/active")
async def providers_active(body: dict) -> dict:
    """Выбрать активного провайдера для X."""
    provider_id = (body or {}).get("provider") or ""
    return providers_registry.set_active(str(provider_id))


# ===== PI ДРОН (Синхронизация и координация) =====

@router.get("/pidron/status")
async def pidron_status() -> dict:
    """Статус PI Дрона и системы синхронизации."""
    pidron = get_pidron()
    status_data = await pidron.status()
    
    return {
        "status": status_data["status"],
        "vault": status_data["vault"],
        "project": status_data["project"],
        "n8n": status_data["n8n"],
        "last_sync": status_data["last_sync"],
        "components": status_data["components"],
    }


@router.post("/pidron/sync")
async def pidron_sync(direction: str = Query(default="bidirectional")) -> dict:
    """Запустить синхронизацию между компонентами системы.
    
    direction: "vault_to_project", "project_to_vault", "n8n", "bidirectional"
    """
    pidron = get_pidron()
    
    try:
        result = await pidron.sync_all(direction=direction)
        
        return {
            "success": len(result["errors"]) == 0,
            "total_synced": result["total"],
            "errors": result["errors"],
            "details": {
                "vault_to_project": result["vault_to_project"],
                "project_to_vault": result["project_to_vault"],
                "n8n_sync": result["n8n_sync"],
            },
        }
    except PIDronError as exc:
        return fail(503, "PIDRON_ERROR", str(exc), retryable=False)
    except Exception as exc:
        return fail(500, "SYNC_FAILED", f"Ошибка синхронизации: {exc}", retryable=True)


@router.get("/pidron/log")
async def pidron_log(limit: int = Query(default=50, ge=1, le=200)) -> dict:
    """Последние записи лога синхронизации."""
    pidron = get_pidron()
    log_file = pidron.vault_path / "data" / "sync_log.json"
    
    if not log_file.exists():
        return {"log": [], "count": 0}
    
    try:
        data = json.loads(log_file.read_text(encoding="utf-8"))
        recent_log = data.get("log", [])[-limit:]
        
        return {
            "log": recent_log,
            "count": len(recent_log),
            "last_sync": data.get("last_sync"),
        }
    except Exception as e:
        return {"log": [], "count": 0, "error": str(e)}


@router.post("/pidron/verify")
async def pidron_verify() -> dict:
    """Проверить целостность данных и структуру системы."""
    pidron = get_pidron()
    
    issues = []
    
    # Проверка компонентов
    components = await pidron._check_components()
    
    if not components["vault_exists"]:
        issues.append({"component": "vault", "issue": "Vault не найден"})
    
    if not components["project_exists"]:
        issues.append({"component": "project", "issue": "Проект не найден"})
    
    if not components["backend_exists"]:
        issues.append({"component": "backend", "issue": "Backend не найден в проекте"})
    
    if not components["frontend_exists"]:
        issues.append({"component": "frontend", "issue": "Frontend не найден в проекте"})
    
    # Проверка ключевых файлов Vault
    key_files = [
        "README.md",
        "API_DOCUMENTATION.md",
        "ARCHITECTURE.md",
        "00_SYSTEM/",
        "01_INBOX/",
        "60_FINANCE/",
        "80_FAMILY/",
    ]
    
    for file in key_files:
        if not (pidron.vault_path / file).exists():
            issues.append({"component": "vault", "file": file, "issue": "Файл/папка отсутствует"})
    
    return {
        "status": "ok" if len(issues) == 0 else "degraded",
        "issues": issues,
        "components": components,
    }


@router.get("/dashboard/overview")
async def dashboard_overview() -> dict:
    """Только чтение: краткая сводка семейной БД и верхнего уровня архива."""
    paths = load_paths()
    db_path = Path(__file__).resolve().parents[1] / "anis_bank.db"

    result = {
        "database_status": "missing",
        "members": [],
        "treasury": [],
        "transactions": [],
        "archive_status": "missing",
        "archive_entries": [],
    }

    if db_path.is_file():
        try:
            with sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True) as con:
                con.row_factory = sqlite3.Row
                result["members"] = [
                    dict(row) for row in con.execute(
                        "SELECT id, name, role, balance "
                        "FROM family_members ORDER BY id"
                    )
                ]
                result["treasury"] = [
                    dict(row) for row in con.execute(
                        "SELECT id, total_balance FROM ship_treasury ORDER BY id"
                    )
                ]
                result["transactions"] = [
                    dict(row) for row in con.execute(
                        "SELECT id, amount, type, description, category, created_at "
                        "FROM transactions ORDER BY id DESC LIMIT 10"
                    )
                ]
            result["database_status"] = "ready"
        except (sqlite3.Error, OSError):
            result["database_status"] = "unavailable"

    archive = paths.vault / "90_ARCHIVE"
    if archive.is_dir():
        try:
            entries = sorted(
                archive.iterdir(),
                key=lambda item: item.stat().st_mtime,
                reverse=True,
            )[:30]
            result["archive_entries"] = [
                {
                    "name": item.name,
                    "kind": "Папка" if item.is_dir() else "Файл",
                }
                for item in entries
            ]
            result["archive_status"] = "ready"
        except OSError:
            result["archive_status"] = "unavailable"

    return result

