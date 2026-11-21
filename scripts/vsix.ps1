# Empaqueta la extensión de VS Code (editors\vscode) como .vsix y la instala.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File scripts\vsix.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\vsix.ps1 -PackageOnly
#   powershell -ExecutionPolicy Bypass -File scripts\vsix.ps1 -SkipDeps -Out C:\ruta
param(
    [switch]$PackageOnly,
    [switch]$SkipDeps,
    [string]$Out = "$PSScriptRoot\..\dist"
)

$ErrorActionPreference = "Stop"

function Write-Info([string]$Message) { Write-Host "-> $Message" }
function Write-Warn([string]$Message) { Write-Host "aviso: $Message" -ForegroundColor Yellow }
function Write-Fail([string]$Message) { Write-Host "error: $Message" -ForegroundColor Red; exit 1 }

$Root = Split-Path -Parent $PSScriptRoot
$ExtDir = Join-Path $Root "editors\vscode"

if (-not (Get-Command node -ErrorAction SilentlyContinue)) { Write-Fail "no se encontró 'node' en PATH" }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { Write-Fail "no se encontró 'npm' en PATH" }
if (-not (Test-Path (Join-Path $ExtDir "package.json"))) { Write-Fail "no existe $ExtDir\package.json" }

if (-not $SkipDeps -and -not (Test-Path (Join-Path $ExtDir "node_modules"))) {
    Write-Info "Instalando dependencias de la extensión..."
    Push-Location $ExtDir
    try {
        npm install --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) { Write-Fail "npm install falló (código $LASTEXITCODE)" }
    }
    finally {
        Pop-Location
    }
}

$Manifest = Get-Content (Join-Path $ExtDir "package.json") -Raw | ConvertFrom-Json
$Version = $Manifest.version
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$Vsix = Join-Path $Out "penguscript-$Version.vsix"

Write-Info "Empaquetando la extensión $Version..."
Push-Location $ExtDir
try {
    npx --yes @vscode/vsce package --allow-missing-repository --out $Vsix
    if ($LASTEXITCODE -ne 0) { Write-Fail "vsce package falló (código $LASTEXITCODE)" }
}
finally {
    Pop-Location
}

if (-not (Test-Path $Vsix)) { Write-Fail "no se generó el .vsix" }
Write-Info "generado $Vsix"

if ($PackageOnly) { exit 0 }

$CodeCli = $null
foreach ($candidate in @("code", "code-insiders", "codium")) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        $CodeCli = $candidate
        break
    }
}

if (-not $CodeCli) {
    Write-Warn "no se encontró el CLI de VS Code (code/code-insiders/codium)."
    Write-Host ""
    Write-Host "Instálala manualmente desde VS Code:"
    Write-Host "  Extensiones -> '...' -> Instalar desde VSIX... -> $Vsix"
    exit 0
}

Write-Info "Instalando en VS Code con '$CodeCli'..."
& $CodeCli --install-extension $Vsix --force
if ($LASTEXITCODE -ne 0) { Write-Fail "la instalación falló (código $LASTEXITCODE)" }
Write-Info "extensión instalada. Recarga VS Code para activarla."
