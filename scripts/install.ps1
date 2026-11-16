# Instalador de PenguScript para Windows.
#
# Uso (PowerShell):
#   .\scripts\install.ps1                       instala la ultima version publicada
#   .\scripts\install.ps1 -FromSource .         compila desde este checkout
#   .\scripts\install.ps1 -Prefix D:\pengu      elige el prefijo
#   .\scripts\install.ps1 -Uninstall            desinstala
#
# Parametros:
#   -Version    version a instalar (por defecto, la ultima publicada)
#   -Prefix     prefijo de instalacion (por defecto $env:PENGU_HOME o %USERPROFILE%\.pengu)
#   -FromSource compila desde el directorio indicado
#   -NoPath     no modifica el PATH del usuario
#   -Uninstall  quita el binario, los extras y la entrada del PATH
#   -Force      reinstala aunque ya este
#   -Yes        no pregunta nada
#
# Este archivo evita acentos a proposito: Windows PowerShell 5.1 lee los .ps1
# sin BOM como ANSI y los caracteres no ASCII se corrompen.

[CmdletBinding()]
param(
    [string]$Version = $env:PENGU_VERSION,
    [string]$Prefix = "",
    [string]$FromSource = "",
    [switch]$NoPath,
    [switch]$Uninstall,
    [switch]$Force,
    [switch]$Yes,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

if ($Help) {
    Get-Content $PSCommandPath | Select-Object -First 24 | ForEach-Object { $_ -replace "^# ?", "" }
    exit 0
}

if (-not $Prefix) {
    $Prefix = if ($env:PENGU_HOME) { $env:PENGU_HOME } else { Join-Path $env:USERPROFILE ".pengu" }
}
$Repo = if ($env:PENGU_REPO) { $env:PENGU_REPO } else { "https://github.com/TuGatito/PenguScript-Rust" }
$BinDir = Join-Path $Prefix "bin"
$ShareDir = Join-Path $Prefix "share"
$ManDir = Join-Path $ShareDir "man\man1"
$CompletionDir = Join-Path $ShareDir "completions"
$Exe = Join-Path $BinDir "pengu.exe"

function Say([string]$Message) { Write-Host $Message }
function Note([string]$Message) { Write-Host "  $Message" }
function Fail([string]$Message) { Write-Error "error: $Message"; exit 1 }

function Get-Target {
    $arch = $env:PROCESSOR_ARCHITECTURE
    if ($arch -eq "ARM64") { return "aarch64-pc-windows-msvc" }
    return "x86_64-pc-windows-msvc"
}

function Get-UserPath {
    $value = [Environment]::GetEnvironmentVariable("Path", "User")
    if (-not $value) { return "" }
    return $value
}

function Set-UserPath([string]$Value) {
    [Environment]::SetEnvironmentVariable("Path", $Value, "User")
}

function Add-ToPath {
    if ($NoPath) { return }
    $current = Get-UserPath
    $entries = @($current -split ";" | Where-Object { $_ -ne "" })
    if ($entries -contains $BinDir) {
        Note "PATH ya contiene $BinDir"
        return
    }
    $updated = if ($entries.Count -gt 0) { "$BinDir;$current" } else { $BinDir }
    Set-UserPath $updated
    $env:Path = "$BinDir;$env:Path"
    Note "PATH de usuario actualizado con $BinDir"
}

function Remove-FromPath {
    $current = Get-UserPath
    if (-not $current) { return }
    $entries = @($current -split ";" | Where-Object { $_ -ne "" -and $_ -ne $BinDir })
    Set-UserPath ($entries -join ";")
    Note "PATH de usuario limpio"
}

function Install-Extras {
    New-Item -ItemType Directory -Force -Path $CompletionDir | Out-Null
    New-Item -ItemType Directory -Force -Path $ManDir | Out-Null
    & $Exe completions bash | Set-Content -Encoding UTF8 (Join-Path $CompletionDir "pengu.bash")
    & $Exe completions zsh | Set-Content -Encoding UTF8 (Join-Path $CompletionDir "_pengu")
    & $Exe completions fish | Set-Content -Encoding UTF8 (Join-Path $CompletionDir "pengu.fish")
    & $Exe man | Set-Content -Encoding UTF8 (Join-Path $ManDir "pengu.1")
    Note "completions en $CompletionDir"
    Note "man en $ManDir\pengu.1"
}

function Install-FromSource([string]$Directory) {
    $dir = $Directory
    if (-not $dir -or $dir -eq ".") { $dir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path }
    if (-not (Test-Path (Join-Path $dir "Cargo.toml"))) {
        Fail "no hay Cargo.toml en $dir"
    }
    if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
        Fail "hace falta cargo para compilar desde fuente (instala Rust desde https://rustup.rs)"
    }
    Say "Compilando PenguScript desde $dir (puede tardar unos minutos)"
    Push-Location $dir
    try {
        & cargo build --release --locked -p pengu-cli
        if ($LASTEXITCODE -ne 0) { Fail "cargo build fallo" }
    } finally {
        Pop-Location
    }
    Copy-Item (Join-Path $dir "target\release\pengu.exe") $Exe -Force
    return $true
}

function Install-FromRelease([string]$TargetName, [string]$Tag) {
    $archive = "pengu-$Tag-$TargetName.zip"
    $url = "$Repo/releases/download/v$Tag/$archive"
    $temp = Join-Path ([System.IO.Path]::GetTempPath()) ("pengu-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path $temp | Out-Null
    try {
        Say "Descargando $url"
        Invoke-WebRequest -Uri $url -OutFile (Join-Path $temp $archive) -UseBasicParsing
        $sumsPath = Join-Path $temp "SHA256SUMS"
        try {
            Invoke-WebRequest -Uri "$Repo/releases/download/v$Tag/SHA256SUMS" -OutFile $sumsPath -UseBasicParsing
            $line = Select-String -Path $sumsPath -Pattern ([regex]::Escape($archive)) | Select-Object -First 1
            if (-not $line) { Fail "SHA256SUMS no contiene $archive" }
            $expected = ($line.Line -split "\s+")[0]
            $actual = (Get-FileHash -Algorithm SHA256 (Join-Path $temp $archive)).Hash.ToLower()
            if ($expected.ToLower() -ne $actual) { Fail "checksum incorrecto para $archive" }
            Note "checksum verificado"
        } catch {
            Note "aviso: no se pudo descargar SHA256SUMS; continuo sin verificar"
        }
        Expand-Archive -Path (Join-Path $temp $archive) -DestinationPath $temp -Force
        $binary = Get-ChildItem -Path $temp -Filter "pengu.exe" -Recurse | Select-Object -First 1
        if (-not $binary) { Fail "el archivo no contiene pengu.exe" }
        Copy-Item $binary.FullName $Exe -Force
    } finally {
        Remove-Item -Recurse -Force $temp -ErrorAction SilentlyContinue
    }
}

function Uninstall {
    Say "Desinstalando PenguScript de $Prefix"
    Remove-FromPath
    if (Test-Path $Prefix) {
        Remove-Item -Recurse -Force $Prefix
        Note "eliminado $Prefix"
    } else {
        Note "no habia nada en $Prefix"
    }
    Say "Hecho. Abre una terminal nueva para que el PATH cambie."
    exit 0
}

if ($Uninstall) { Uninstall }

New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

if ((Test-Path $Exe) -and (-not $Force) -and (-not $FromSource)) {
    $installed = (& $Exe version | ForEach-Object { ($_ -split " ")[1] })
    if ($Version -and $installed -eq $Version) {
        Say "PenguScript $installed ya esta instalado en $BinDir"
        Say "Usa -Force para reinstalar o -Version para cambiar."
        Add-ToPath
        exit 0
    }
}

if ($FromSource) {
    Install-FromSource $FromSource
} else {
    $targetName = Get-Target
    if (-not $Version) {
        try {
            $latest = (Invoke-WebRequest -Uri "$Repo/releases/latest/download/VERSION" -UseBasicParsing).Content
            $Version = ($latest -replace "[^0-9.]", "").Trim()
        } catch {
            $Version = ""
        }
    }
    if (-not $Version) {
        Say "No se pudo averiguar la ultima version publicada."
        Say "Compilo desde el repositorio actual como respaldo."
        Install-FromSource "."
    } else {
        Install-FromRelease $targetName $Version
    }
}

if (-not (Test-Path $Exe)) { Fail "no se instalo el binario en $Exe" }
$Version = (& $Exe version | ForEach-Object { ($_ -split " ")[1] })
Install-Extras
Add-ToPath

Say ""
Say "PenguScript $Version instalado en $Exe"
if ($NoPath) {
    Say "Anade $BinDir al PATH (se omitio por -NoPath)."
} else {
    Say "Abre una terminal nueva para usar pengu."
}
Say ""
Say "Comprobando la instalacion:"
$env:Path = "$BinDir;$env:Path"
& $Exe doctor
exit $LASTEXITCODE
