@echo off
rem Instalador de PenguScript para Windows.
rem
rem Uso:
rem   scripts\install.bat                          instala la ultima version
rem   scripts\install.bat --from-source .          compila desde este checkout
rem   scripts\install.bat --prefix D:\pengu        elige el prefijo
rem   scripts\install.bat --uninstall              desinstala
rem   scripts\install.bat --help                   muestra la ayuda
rem
rem Traduce las opciones al estilo de install.ps1 (-Version, -Prefix,
rem -FromSource, -NoPath, -Uninstall, -Force, -Yes) y delega en PowerShell.

setlocal EnableDelayedExpansion
set "SCRIPT=%~dp0install.ps1"
if not exist "%SCRIPT%" (
    echo error: no se encuentra "%SCRIPT%" 1>&2
    exit /b 1
)

where powershell >nul 2>nul
if errorlevel 1 (
    echo error: hace falta Windows PowerShell ^(powershell.exe^) 1>&2
    echo        viene preinstalado en Windows 7 y posteriores.
    exit /b 1
)

set "ARGS="
:parse
if "%~1"=="" goto run
set "ARG=%~1"
set "MAPPED="
if /i "!ARG!"=="--version"     set "MAPPED=-Version"
if /i "!ARG!"=="--prefix"      set "MAPPED=-Prefix"
if /i "!ARG!"=="--from-source" set "MAPPED=-FromSource"
if /i "!ARG!"=="--no-path"     set "MAPPED=-NoPath"
if /i "!ARG!"=="--uninstall"   set "MAPPED=-Uninstall"
if /i "!ARG!"=="--force"       set "MAPPED=-Force"
if /i "!ARG!"=="--yes"         set "MAPPED=-Yes"
if /i "!ARG!"=="-y"            set "MAPPED=-Yes"
if /i "!ARG!"=="--help"        set "MAPPED=-Help"
if /i "!ARG!"=="-h"            set "MAPPED=-Help"
if defined MAPPED set "ARG=!MAPPED!"
set "ARGS=!ARGS! "!ARG!""
shift
goto parse

:run
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%" %ARGS%
set "CODE=%ERRORLEVEL%"
endlocal & exit /b %CODE%
