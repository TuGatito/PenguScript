# Build a native `psc` bootstrap on Windows from the checked-in stage0 bundle.
#
# The bundle only needs a C compiler (MinGW-w64 gcc/clang) and `ar`, so CI and
# users can bootstrap without Python or a previous release.
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$OutDir = Join-Path $Root "build"
$Out = Join-Path $OutDir "psc-stage0.exe"

function Get-Tool([string]$Name, [string]$Fallback) {
    $value = [Environment]::GetEnvironmentVariable($Name)
    if ($value) { return $value }
    $cmd = Get-Command $Fallback -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $Fallback
}

$CC = Get-Tool "CC" "gcc"
$AR = Get-Tool "AR" "ar"
if (-not (Get-Command $CC -ErrorAction SilentlyContinue)) {
    $alt = Get-Command "cc" -ErrorAction SilentlyContinue
    if ($alt) { $CC = $alt.Source }
}
if (-not (Get-Command $CC -ErrorAction SilentlyContinue)) {
    throw "build_bootstrap: no C compiler found (set CC)"
}

$arch = $env:PROCESSOR_ARCHITECTURE
if (-not $arch) { $arch = "AMD64" }
switch ($arch.ToUpperInvariant()) {
    "AMD64" { $hostArch = "x64" }
    "ARM64" { $hostArch = "arm64" }
    default { $hostArch = $arch.ToLowerInvariant() }
}

$stage0 = Join-Path $Root "bootstrap\psc_stage0_windows_x64.c"
if ($hostArch -ne "x64" -or -not (Test-Path $stage0)) {
    if (Test-Path (Join-Path $OutDir "psc.exe")) {
        Write-Host "[bootstrap] no Windows stage0 bundle; reusing build\psc.exe"
        exit 0
    }
    throw "build_bootstrap: no stage0 bundle for windows-$hostArch (expected bootstrap\psc_stage0_windows_x64.c)"
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

Write-Host "[bootstrap] building the native runtime"
$env:PENGU_NO_WERROR = "1"
& (Join-Path $PSScriptRoot "build_runtime.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$libs = @("-lm", "-lws2_32", "-lwinpthread")
$ccArgs = @(
    "-std=c11", "-O2",
    "-I$Root", "-I$(Join-Path $Root 'build\include')",
    "-I$(Join-Path $Root 'std_c')", "-I$(Join-Path $Root 'std_c\sds')",
    $stage0,
    (Join-Path $Root "build\lib\libpengu_runtime.a"),
    (Join-Path $Root "build\lib\libminiz.a"),
    (Join-Path $Root "build\lib\libre.a")
) + $libs + @("-o", $Out)

& $CC @ccArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $Out version
