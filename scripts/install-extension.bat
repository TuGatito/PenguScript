@echo off
rem Empaqueta la extension de VS Code y la instala (atajo de vsix.mjs --install).
rem
rem Uso: scripts\install-extension.bat [--code RUTA] [--out RUTA]

setlocal
where node >nul 2>nul
if errorlevel 1 (
    echo error: hace falta Node.js ^(https://nodejs.org^) 1>&2
    exit /b 1
)
node "%~dp0vsix.mjs" --install %*
exit /b %ERRORLEVEL%
