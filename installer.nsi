; Zhorik-Setup-0.1.0.nsi
; NSIS installer for DRON X GENIE (Zhorik)
; Version: 0.1.0

!define APP_NAME "Zhorik"
!define APP_VERSION "0.1.0"
!define APP_PUBLISHER "DRON X GENIE Team"
!define APP_WEBSITE "https://dronxgenie.com"
!define INSTALLER_NAME "Zhorik-Setup-0.1.0.exe"

!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"

; --- General ---
Name "${APP_NAME} ${APP_VERSION}"
OutFile "dist\\${INSTALLER_NAME}"
InstallDir "$LOCALAPPDATA\\Zhorik"
InstallDirRegKey HKCU "Software\\${APP_NAME}" "InstallDir"
RequestExecutionLevel user
ShowInstDetails show

; --- Modern UI ---
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"
!define MUI_LICENSEPAGE_TEXT_LICENSELICENSETEXTTOP "Постановление об использовании DRON X GENIE (Zhorik)"
!define MUI_LICENSEPAGE_TEXT_LICENSELICENSETEXTBOTTOM "Нажимая Далее, вы принимаете условия."

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "docs\LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "Russian"

; --- Variables ---
Var StartMenuFolder
Var PreviousInstallDir

; ============================================================================
; .onInit
; ============================================================================
Function .onInit
    ; Check for previous installation
    ReadRegStr $PreviousInstallDir HKCU "Software\\${APP_NAME}" "InstallDir"
    ${If} $PreviousInstallDir != ""
        MessageBox MB_YESNO|MB_ICONQUESTION \
            "Обнаружена предыдущая установка в:$\n$PreviousInstallDir$\n$\nУдалить её и установить заново?" \
            IDYES NoRemovePrevious
        ; Remove previous installation silently
        ClearErrors
        Delete "$PreviousInstallDir\*"
        RMDir /r "$PreviousInstallDir"
        DeleteRegKey HKCU "Software\\${APP_NAME}"
    NoRemovePrevious:
    ${EndIf}
FunctionEnd

; ============================================================================
; Install
; ============================================================================
Section "MainSection" SEC_MAIN
    SetOutPath "$INSTDIR"
    SetOutPath "$INSTDIR\backend"
    File /r "backend\*.py"
    SetOutPath "$INSTDIR\backend\agent"
    File /r "backend\agent\*.py"
    SetOutPath "$INSTDIR\frontend\dist"
    File /r "frontend\dist\*.*"
    SetOutPath "$INSTDIR\frontend\dron_ui"
    File /r "frontend\dron_ui\*.*"
    SetOutPath "$INSTDIR\scripts"
    File /r "scripts\*.ps1"
    File /r "scripts\*.py"
    SetOutPath "$INSTDIR\prompts"
    File /r "prompts\*.md"
    SetOutPath "$INSTDIR\configs"
    File /r "configs\*.json"
    SetOutPath "$INSTDIR\css"
    File /r "css\*.css"
    SetOutPath "$INSTDIR\js"
    File /r "js\*.js"
    SetOutPath "$INSTDIR\data\genie_memory"
    File /r "data\genie_memory\*"
    SetOutPath "$INSTDIR\data\logs"
    File /r "data\logs\*"
    SetOutPath "$INSTDIR"
    File /r "requirements.txt"
    File /r "requirements-core.txt"
    SetOutPath "$INSTDIR\docs"
    File /r "docs\*.md"
    File /r "docs\LICENSE.txt"

    ; Create data directories
    CreateDirectory "$INSTDIR\data\genie_memory"
    CreateDirectory "$INSTDIR\data\logs"
    CreateDirectory "$INSTDIR\data\sync"

    ; Write uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"

    ; Registry
    WriteRegStr HKCU "Software\\${APP_NAME}" "InstallDir" "$INSTDIR"
    WriteRegStr HKCU "Software\\${APP_NAME}" "Version" "${APP_VERSION}"
    
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayName" "${APP_NAME} ${APP_VERSION}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "UninstallString" '"$INSTDIR\uninstall.exe"'
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayVersion" "${APP_VERSION}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "Publisher" "${APP_PUBLISHER}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "URLInfoAbout" "${APP_WEBSITE}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "InstallLocation" "$INSTDIR"

    ; Start Menu
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\scripts\launcher.py"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" "$INSTDIR\uninstall.exe"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\Open Folder.lnk" "$INSTDIR"

    ${GetParameters} $R0
    ${If} $R0 == "/NOICONS"
        ; User doesn't want icons
    ${Else}
        CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\scripts\launcher.py"
    ${EndIf}
SectionEnd

; ============================================================================
; Uninstall
; ============================================================================
Section "Uninstall"
    ; Remove files
    RMDir /r "$INSTDIR"

    ; Remove Start Menu
    Delete "$SMPROGRAMS\${APP_NAME}\*.*"
    RMDir "$SMPROGRAMS\${APP_NAME}"

    ; Remove Desktop shortcut
    Delete "$DESKTOP\${APP_NAME}.lnk"

    ; Remove Registry
    DeleteRegKey HKCU "Software\${APP_NAME}"
    DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
SectionEnd

; ============================================================================
; Finish - no interactive dialog (silent install)
; ============================================================================
Function .onInstSuccess
    ShowWindow $HWNDPARENT ${SW_SHOW}
FunctionEnd