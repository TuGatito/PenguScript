# Instala el ejecutable de PenguScript (pengu.exe) y lo añade al PATH del usuario.
#
# No modifica perfiles de PowerShell, cmd ni de ningún otro shell: usa la
# variable de entorno Path de usuario de Windows, que todos los shells heredan.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File scripts\install.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\install.ps1 -Prefix C:\ruta
#   powershell -ExecutionPolicy Bypass -File scripts\install.ps1 -SkipBuild
param(
    [string]$Prefix = "$env:LOCALAPPDATA\Programs\pengu",
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

function Write-Info([string]$Message) { Write-Host "-> $Message" }
function Write-Fail([string]$Message) { Write-Host "error: $Message" -ForegroundColor Red; exit 1 }

$Root = Split-Path -Parent $PSScriptRoot

if (-not (Get-Command bun -ErrorAction SilentlyContinue)) {
    Write-Fail "no se encontró 'bun' en PATH (se necesita Bun >= 1.4)"
}

if (-not $SkipBuild) {
    Write-Info "Compilando pengu con Bun..."
    Push-Location $Root
    try {
        bun run build
        if ($LASTEXITCODE -ne 0) { Write-Fail "la compilación falló (código $LASTEXITCODE)" }
    }
    finally {
        Pop-Location
    }
}

$Candidates = @(
    (Join-Path $Root "dist\pengu.exe"),
    (Join-Path $Root "dist\pengu")
)
$Binary = $Candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Binary) {
    Write-Fail "no existe dist\pengu.exe; ejecuta de nuevo sin -SkipBuild"
}

New-Item -ItemType Directory -Force -Path $Prefix | Out-Null
$Target = Join-Path $Prefix "pengu.exe"
Copy-Item -Force $Binary $Target
Write-Info "instalado en $Target"

# Path de usuario (HKLM no necesita permisos y lo heredan todos los shells).
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
$Parts = @()
if ($UserPath) { $Parts = $UserPath -split ';' | Where-Object { $_ } }
if ($Parts -notcontains $Prefix) {
    $NewPath = (@($Parts) + $Prefix) -join ';'
    [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
    Write-Info "añadido '$Prefix' al PATH del usuario"
}
else {
    Write-Info "'$Prefix' ya estaba en el PATH del usuario"
}

# También en la sesión actual, para poder probarlo sin abrir otra consola.
if (($env:Path -split ';') -notcontains $Prefix) {
    $env:Path = "$env:Path;$Prefix"
}

& $Target --version
