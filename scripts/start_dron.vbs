' DRON X GENIE — запуск через setup_env.ps1 (создаёт .venv, ставит зависимости, запускает бэкенд)
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "powershell -ExecutionPolicy Bypass -File ""%~dp0setup_env.ps1""", 1, True
