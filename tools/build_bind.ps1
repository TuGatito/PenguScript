# Build the libclang-based pengu-bind helper on Windows.
param([string]$Output = "")
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Out = if ($Output) { $Output } else { Join-Path $Root "build\pengu-bind.exe" }
$CC = if ($env:CC) { $env:CC } else { "gcc" }

$cflags = @()
$libs = @()
$llvmConfig = Get-Command "llvm-config" -ErrorAction SilentlyContinue
if ($llvmConfig) {
    $cflags = @(& $llvmConfig.Source --cflags)
    $libs = @(& $llvmConfig.Source --ldflags) + @("-lclang")
} else {
    $libs = @("-lclang")
}

$outDir = Split-Path -Parent $Out
if ($outDir) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }

$ccArgs = @("-std=c11", "-O2", "-Wall", "-Wextra") + $cflags +
    @((Join-Path $Root "tools\pengu-bind-clang.c")) + $libs + @("-o", $Out)
& $CC @ccArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "[bind] built $Out"
