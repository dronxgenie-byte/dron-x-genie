; --- Определения ---
!define APP_NAME "Zhorik"
!define APP_VERSION "0.1.0"
!define APP_PUBLISHER "DronX Genie"
!define APP_URL "https://github.com/dronxgenie-byte/dron-x-genie"

Name "${APP_NAME}"
OutFile "dist\Zhorik-Setup-${APP_VERSION}.exe"
InstallDir "$LOCALAPPDATA\Zhorik"
RequestExecutionLevel user
SetCompressor /SOLID lzma

; --- Современный интерфейс ---
!include "MUI2.nsh"
!define MUI_ABORTWARNING
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Russian"

; --- Секция установки ---
Section "Install"
    SetOutPath "$INSTDIR"
    
    ; Копируем основные файлы
    File "requirements.txt"
    
    ; КОПИРУЕМ ПАПКИ ЦЕЛИКОМ (без \*.*), чтобы сохранить структуру
    File /r "backend"
    File /r "frontend"
    File /r "scripts"
    File /r "prompts"
    File /r "configs"
    File /r "css"
    File /r "js"
    File /r "docs"
    
    ; Создаем пустые папки для данных
    CreateDirectory "$INSTDIR\data\logs"
    CreateDirectory "$INSTDIR\data\genie_memory"
    
    ; Создаем деинсталлятор
    WriteUninstaller "$INSTDIR\uninstall.exe"
    
    ; Запись в реестр (HKCU - для текущего пользователя)
    WriteRegStr HKCU "Software\${APP_NAME}" "InstallDir" "$INSTDIR"
    
    ; Запись в "Установка и удаление программ"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayName" "${APP_NAME}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "UninstallString" '"$INSTDIR\uninstall.exe"'
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayVersion" "${APP_VERSION}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "Publisher" "${APP_PUBLISHER}"
    
    ; Создание ярлыков (в Пуске и на Рабочем столе)
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\scripts\launcher.py" "" "$INSTDIR\scripts\launcher.py" 0 SW_SHOWNORMAL
    CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\scripts\launcher.py" "" "$INSTDIR\scripts\launcher.py" 0 SW_SHOWNORMAL
SectionEnd

; --- Секция удаления ---
Section "Uninstall"
    ; Убиваем процессы, если они висят
    nsExec::Exec 'taskkill /f /im python.exe'
    
    ; Удаляем папки, включая созданную venv
    RMDir /r "$INSTDIR\.venv"
    RMDir /r "$INSTDIR\backend"
    RMDir /r "$INSTDIR\frontend"
    RMDir /r "$INSTDIR\scripts"
    RMDir /r "$INSTDIR\prompts"
    RMDir /r "$INSTDIR\configs"
    RMDir /r "$INSTDIR\css"
    RMDir /r "$INSTDIR\js"
    RMDir /r "$INSTDIR\docs"
    RMDir /r "$INSTDIR\data"
    
    Delete "$INSTDIR\requirements.txt"
    Delete "$INSTDIR\uninstall.exe"
    
    ; Принудительно удаляем корневую папку
    RMDir /r "$INSTDIR"

    ; Удаляем ярлыки
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    RMDir "$SMPROGRAMS\${APP_NAME}"
    Delete "$DESKTOP\${APP_NAME}.lnk"

    ; Чистим реестр
    DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
    DeleteRegKey HKCU "Software\${APP_NAME}"
SectionEnd