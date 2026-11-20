!define APP_NAME "Zhorik"
!define APP_VERSION "0.1.0"
!define APP_PUBLISHER "DronX Genie"

Name "${APP_NAME}"
OutFile "dist\Zhorik-Setup-${APP_VERSION}.exe"
InstallDir "$LOCALAPPDATA\Zhorik"
RequestExecutionLevel user
SetCompressor /SOLID lzma

!include "MUI2.nsh"
!define MUI_ABORTWARNING
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Russian"

Section "Install"
    SetOutPath "$INSTDIR"
    
    File "requirements.txt"
    File "requirements-core.txt"
    
    File /r "backend"
    File /r "frontend"
    File /r "scripts"
    File /r "prompts"
    File /r "configs"
    File /r "css"
    File /r "js"
    File /r "docs"
    
    CreateDirectory "$INSTDIR\data\logs"
    CreateDirectory "$INSTDIR\data\genie_memory"
    
    WriteUninstaller "$INSTDIR\uninstall.exe"
    
    WriteRegStr HKCU "Software\${APP_NAME}" "InstallDir" "$INSTDIR"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayName" "${APP_NAME}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "UninstallString" '"$INSTDIR\uninstall.exe"'
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayVersion" "${APP_VERSION}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "Publisher" "${APP_PUBLISHER}"
    
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\scripts\launcher.py" "" "$INSTDIR\scripts\launcher.py" 0 SW_SHOWNORMAL
    CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\scripts\launcher.py" "" "$INSTDIR\scripts\launcher.py" 0 SW_SHOWNORMAL
SectionEnd

Section "Uninstall"
    nsExec::Exec 'taskkill /f /im python.exe'
    
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
    Delete "$INSTDIR\requirements-core.txt"
    Delete "$INSTDIR\uninstall.exe"
    
    RMDir /r "$INSTDIR"

    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    RMDir "$SMPROGRAMS\${APP_NAME}"
    Delete "$DESKTOP\${APP_NAME}.lnk"

    DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
    DeleteRegKey HKCU "Software\${APP_NAME}"
SectionEnd