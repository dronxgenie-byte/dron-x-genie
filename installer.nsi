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