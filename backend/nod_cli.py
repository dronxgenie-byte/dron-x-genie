"""
NOD CLI — управление провайдерами, моделями и ключами API.

Использование:
    python backend/nod_cli.py provider add <name> <type> <base_url> [--free-tier-url <url>] [--docs-url <url>]
    python backend/nod_cli.py provider list
    python backend/nod_cli.py model add <provider> <model_id> [--free] [--context <n>] [--priority <1|2|3>]
    python backend/nod_cli.py model list [provider]
    python backend/nod_cli.py key add <provider> <key_name> <key_value>
    python backend/nod_cli.py key list [provider]
    python backend/nod_cli.py key health-check [provider]
    python backend/nod_cli.py discovery run
    python backend/nod_cli.py discovery report
    python backend/nod_cli.py router status
    python backend/nod_cli.py router route <запрос>
    python backend/nod_cli.py router test-routing <запрос>
    python backend/nod_cli.py amd status
    python backend/nod_cli.py dashboard
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

try:
    from rich.console import Console
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Добавить корень проекта в sys.path, чтобы импорты backend.* работали
# при запуске скрипта напрямую: python backend/nod_cli.py ...
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.nod_providers import (
    add_model,
    add_provider,
    add_discovery,
    get_models_by_priority,
    get_provider,
    get_latest_amd_billing,
    list_models,
    list_providers,
    record_key_health,
)
from backend.nod_discovery import run_discovery as discovery_run, get_discovery_report, clear_discovery_report
from backend.nod_vault import store_key, get_key, delete_key, list_key_ids
from backend.nod_monitor import (
    check_all_keys,
    get_health_summary,
    get_amd_status,
    record_amd_usage,
    AMD_RPS_LIMIT,
)
from backend.nod_router import NODRouter


def cmd_provider_add(args: list[str]) -> None:
    if len(args) < 3:
        print("Использование: provider add <name> <type> <base_url> [--free-tier-url <url>] [--docs-url <url>]")
        return
    name = args[0]
    ptype = args[1]
    base_url = args[2]
    free_tier_url = ""
    docs_url = ""
    i = 3
    while i < len(args):
        if args[i] == "--free-tier-url" and i + 1 < len(args):
            free_tier_url = args[i + 1]
            i += 2
        elif args[i] == "--docs-url" and i + 1 < len(args):
            docs_url = args[i + 1]
            i += 2
        else:
            i += 1
    pid = add_provider(
        name=name,
        provider_type=ptype,
        base_url=base_url,
        free_tier_url=free_tier_url or None,
        docs_url=docs_url or None,
    )
    print(f"Провайдер '{name}' добавлен (id={pid})")


def cmd_provider_list(args: list[str]) -> None:
    providers = list_providers()
    if not providers:
        print("Провайдеры не найдены.")
        return
    print("\nПровайдеры:")
    for p in providers:
        print(f"  [{p['id']}] {p['name']} ({p['provider_type']}) — {p['base_url']}")
        if p.get("free_tier_url"):
            print(f"      Бесплатный доступ: {p['free_tier_url']}")


def cmd_model_add(args: list[str]) -> None:
    if len(args) < 2:
        print("Использование: model add <provider> <model_id> [--free] [--context <n>] [--priority <1|2|3>]")
        return
    provider_name = args[0]
    model_id = args[1]
    is_free = False
    context_window = None
    cost_priority = 2
    i = 2
    while i < len(args):
        if args[i] == "--free":
            is_free = True
            i += 1
        elif args[i] == "--context" and i + 1 < len(args):
            context_window = int(args[i + 1])
            i += 2
        elif args[i] == "--priority" and i + 1 < len(args):
            cost_priority = int(args[i + 1])
            i += 2
        else:
            i += 1
    add_model(
        provider_name=provider_name,
        model_id=model_id,
        is_free=is_free,
        context_window=context_window,
        cost_priority=cost_priority,
    )
    print(f"Модель '{model_id}' добавлена для провайдера '{provider_name}' (приоритет {cost_priority})")


def cmd_model_list(args: list[str]) -> None:
    provider_name = args[0] if args else None
    models = list_models(provider_name)
    if not models:
        print("Модели не найдены.")
        return
    print("\nМодели:")
    for m in models:
        free_mark = " [БЕСПЛАТНО]" if m.get("is_free") else ""
        priority_mark = f" [приоритет {m.get('cost_priority', 2)}]"
        print(f"  {m['provider_name']}:{m['model_id']}{free_mark}{priority_mark}")


def cmd_key_add(args: list[str]) -> None:
    if len(args) < 3:
        print("Использование: key add <provider> <key_name> <key_value>")
        return
    provider_name = args[0]
    key_name = args[1]
    key_value = args[2]
    key_id = f"{provider_name}:{key_name}"
    store_key(key_id, key_value)
    from backend.nod_providers import add_api_key
    add_api_key(provider_name, key_name, key_id)
    print(f"Ключ '{key_name}' для провайдера '{provider_name}' сохранён в сейфе")


def cmd_key_list(args: list[str]) -> None:
    provider_name = args[0] if args else None
    from backend.nod_providers import list_keys as _list_keys
    keys = _list_keys(provider_name)
    if not keys:
        print("Ключи не найдены.")
        return
    print("\nКлючи:")
    for k in keys:
        print(f"  [{k['id']}] {k['key_name']} — {k['provider_name']} (успехов: {k.get('success_count', 0)}, неудач: {k.get('fail_count', 0)})")


def cmd_key_health(args: list[str]) -> None:
    import asyncio
    provider_name = args[0] if args else None
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(check_all_keys())
    finally:
        loop.close()
    print(f"\nПроверка ключей: {result['working_keys']}/{result['total_keys']} работают")
    for r in result.get("results", []):
        status = "✓" if r.get("is_working") else "✗"
        err = f" ({r.get('error')})" if r.get("error") else ""
        print(f"  {status} {r.get('provider')}{err}")


def cmd_discovery_run(args: list[str]) -> None:
    report = discovery_run()
    print(f"\nНочной поиск завершён ({report['timestamp']}):")
    print(f"  Новых провайдеров: {len(report['added_providers'])} — {report['added_providers']}")
    print(f"  Новых моделей: {len(report['added_models'])}")
    print(f"  Пропущено (уже есть): {len(report['skipped_existing'])}")


def cmd_discovery_report(args: list[str]) -> None:
    report = get_discovery_report()
    if not report:
        print("Отчёта о поиске нет. Запустите: discovery run")
        return
    print(f"\nОтчёт ночного поиска ({report['timestamp']}):")
    print(f"  Провайдеры: {report['added_providers']}")
    print(f"  Модели: {report['added_models']}")
    print(f"  Пропущено: {report['skipped_existing']}")
    clear_discovery_report()


def cmd_router_status(args: list[str]) -> None:
    router = NODRouter()
    status = router.get_status()
    print(f"\nСтатус NOD роутера:")
    print(f"  Провайдеров: {status['providers_count']}")
    print(f"  Ключей: {status['keys_count']} (работают: {status['working_keys_count']})")
    print(f"  Моделей: {status['models_count']} (бесплатно: {status['free_models_count']})")
    print(f"  Список провайдеров: {', '.join(status['providers_list']) or 'пусто'}")
    if status.get("amd_billing"):
        ab = status["amd_billing"]
        print(f"  AMD баланс: {ab.get('remaining_tokens', 'N/A')} токенов")
        print(f"  AMD RPS: {ab.get('rps_used', 0)}/{ab.get('rps_limit', 20)}")


def cmd_router_route(args: list[str]) -> None:
    if not args:
        print("Использование: router route <запрос>")
        return
    query = " ".join(args)
    import asyncio
    router = NODRouter()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(router.route_request(query))
    finally:
        loop.close()
    print(f"\nОтвет роутера:")
    print(f"  Статус: {result.get('status')}")
    if result.get("status") == "ok":
        print(f"  Провайдер: {result.get('provider')}")
        print(f"  Модель: {result.get('model')}")
        print(f"  Приоритет: {result.get('cost_priority')}")
        print(f"  Время: {result.get('response_time_ms')} мс")
        print(f"  Ответ: {result.get('response')}")
    else:
        print(f"  Ошибка: {result.get('message')}")
        if result.get("suggestion"):
            print(f"  Подсказка: {result.get('suggestion')}")


def cmd_router_test_routing(args: list[str]) -> None:
    """Показать, какой провайдер будет выбран для запроса, без фактической отправки."""
    if not args:
        print("Использование: router test-routing <запрос>")
        return
    query = " ".join(args)
    router = NODRouter()

    # Показываем что будет выбрано для каждого приоритета
    print(f"\nТест маршрутизации для запроса: '{query}'")
    print("-" * 60)

    for priority in (1, 2, 3):
        selected = router.select_best_provider(
            require_priority=priority,
            model_preference=None,
        )
        if selected:
            print(f"  Приоритет {priority} ({'AMD бесплатные' if priority == 1 else 'Бесплатный tier' if priority == 2 else 'Платные API'}):")
            print(f"    Провайдер: {selected['provider_name']}")
            print(f"    Модель: {selected['model_id']}")
            print(f"    Ключ: {selected['key_name']} (id={selected['key_id']})")
        else:
            print(f"  Приоритет {priority}: нет доступных провайдеров с ключами")

    # Показываем итоговый выбор
    print("-" * 60)
    result = router.select_best_provider(require_free=True)
    if result:
        print(f"✓ Выбранный провайдер: {result['provider_name']}")
        print(f"  Модель: {result['model_id']}")
        print(f"  Приоритет: {result['cost_priority']} ({'AMD бесплатные баллы' if result['cost_priority'] == 1 else 'Бесплатный tier' if result['cost_priority'] == 2 else 'Платные API'})")
        print(f"  Ключ: {result['key_name']}")
    else:
        print("✗ Нет доступных провайдеров с ключами!")


def cmd_amd_status(args: list[str]) -> None:
    """Показать текущий статус AMD биллинга."""
    status = get_amd_status()
    current = status.get("current", {})
    db_record = status.get("last_db_record")

    print("\nСтатус AMD AI Developer Program:")
    print("-" * 50)
    print(f"  RPS лимит: {status['rps_limit']}")
    print(f"  Порог предупреждения: {status['warning_threshold']}")
    print()
    print(f"  Текущее RPS: {current.get('rps_used', 0)}")
    print(f"  Остаток токенов: {current.get('remaining_tokens', 'N/A')}")
    print(f"  Дневной лимит: {current.get('daily_limit', 'N/A')}")
    print(f"  Дневное использование: {current.get('daily_used', 0)}")
    print(f"  Последнее обновление: {current.get('last_updated', 'N/A')}")
    print()
    if status["is_limit_reached"]:
        print("  ⚠️  LIMITE RPS ИСЧЕРПАН — AMD недоступен!")
    elif status["is_near_limit"]:
        print(f"  ⚠️  ВНИМАНИЕ: RPS близко к лимиту ({current.get('rps_used', 0)}/{AMD_RPS_LIMIT})")
    else:
        print("  ✓ AMD доступен в обычном режиме")
    print()
    if db_record:
        print(f"  Последняя запись в БД: {db_record.get('checked_at', 'N/A')}")
        print(f"  Заметка: {db_record.get('notes', 'N/A')}")


def cmd_dashboard(args: list[str]) -> None:
    """Интерактивная таблица состояния NOD в терминале."""
    if not RICH_AVAILABLE:
        print("Ошибка: библиотека rich не установлена. Установите: pip install rich")
        return

    from backend.nod_router import NODRouter
    from backend.nod_providers import list_providers, list_models, list_keys
    from backend.nod_monitor import get_amd_status, AMD_RPS_LIMIT

    console = Console()

    try:
        while True:
            console.clear()
            console.print("[bold cyan]NOD Dashboard — mo니торинг системы[/bold cyan]")
            console.print(f"[dim]Обновление каждые 5 сек. Ctrl+C для выхода.[/dim]\n")

            router = NODRouter()
            status = router.get_status()
            amd_status = get_amd_status()

            # Таблица провайдеров
            table = Table(title="Провайдеры и модели")
            table.add_column("Провайдер", style="cyan")
            table.add_column("Тип", style="magenta")
            table.add_column("Базовый URL", style="green")
            table.add_column("Ключей", style="yellow")
            table.add_column("Работающих", style="green")

            from backend.nod_providers import list_keys as _list_keys
            all_keys = _list_keys()
            keys_by_provider = {}
            for k in all_keys:
                pname = k["provider_name"]
                if pname not in keys_by_provider:
                    keys_by_provider[pname] = {"total": 0, "working": 0}
                keys_by_provider[pname]["total"] += 1
                if k.get("success_count", 0) > k.get("fail_count", 0):
                    keys_by_provider[pname]["working"] += 1

            for p in status.get("providers", []):
                pname = p["name"]
                keys_info = keys_by_provider.get(pname, {"total": 0, "working": 0})
                table.add_row(
                    pname,
                    p.get("type", "unknown"),
                    p.get("base_url", "N/A"),
                    str(keys_info["total"]),
                    str(keys_info["working"]),
                )

            console.print(table)
            console.print()

            # Таблица моделей по приоритетам
            models_table = Table(title="Модели по приоритетам стоимости")
            models_table.add_column("Приоритет", style="cyan")
            models_table.add_column("Количество", style="magenta")
            models_table.add_column("Модели", style="green")

            for p in (1, 2, 3):
                models = get_models_by_priority(p)
                priority_label = {
                    1: "1 — AMD бесплатные",
                    2: "2 — Бесплатный tier",
                    3: "3 — Платные API",
                }[p]
                models_list = ", ".join(m["model_id"] for m in models[:5])
                if len(models) > 5:
                    models_list += f" … (+{len(models) - 5})"
                models_table.add_row(priority_label, str(len(models)), models_list)

            console.print(models_table)
            console.print()

            # AMD статус
            amd_table = Table(title="AMD AI Developer Program")
            amd_table.add_column("Параметр", style="cyan")
            amd_table.add_column("Значение", style="magenta")

            current = amd_status.get("current", {})
            amd_table.add_row("RPS лимит", str(amd_status["rps_limit"]))
            amd_table.add_row("Текущее RPS", str(current.get("rps_used", 0)))
            amd_table.add_row("Порог предупреждения", str(amd_status["warning_threshold"]))
            amd_table.add_row("Остаток токенов", str(current.get("remaining_tokens", "N/A")))
            amd_table.add_row("Дневное использование", str(current.get("daily_used", 0)))
            amd_table.add_row(
                "Статус",
                "🔴 ЛИМИТ ИСЧЕРПАН" if amd_status["is_limit_reached"]
                else "🟡 БЛИЗКО К ЛИМИТУ" if amd_status["is_near_limit"]
                else "🟢 НОРМА",
            )
            amd_table.add_row("Последнее обновление", current.get("last_updated", "N/A"))

            console.print(amd_table)
            console.print()

            console.print("[dim]Нажмите Ctrl+C для выхода…[/dim]")
            time.sleep(5)
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Dashboard остановлен.[/bold yellow]")


COMMANDS = {
    "provider": {
        "add": cmd_provider_add,
        "list": cmd_provider_list,
    },
    "model": {
        "add": cmd_model_add,
        "list": cmd_model_list,
    },
    "key": {
        "add": cmd_key_add,
        "list": cmd_key_list,
        "health-check": cmd_key_health,
    },
    "discovery": {
        "run": cmd_discovery_run,
        "report": cmd_discovery_report,
    },
    "router": {
        "status": cmd_router_status,
        "route": cmd_router_route,
        "test-routing": cmd_router_test_routing,
    },
    "amd": {
        "status": cmd_amd_status,
    },
    "dashboard": {
        "": cmd_dashboard,
    },
}


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return
    group = sys.argv[1]
    action = sys.argv[2] if len(sys.argv) > 2 else ""
    rest = sys.argv[3:]

    if group in COMMANDS and action in COMMANDS[group]:
        COMMANDS[group][action](rest)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
