$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Psc = if ($env:PSC) { $env:PSC } else { Join-Path $Root "build\psc.exe" }
Set-Location $Root
$fail = 0
$count = 0
$files = @(Get-ChildItem tests\pengu\*.pengu -File -ErrorAction SilentlyContinue)
$files += @(Get-ChildItem tests\conformance -Recurse -Filter *.pengu -File -ErrorAction SilentlyContinue)
$wasmSmoke = Join-Path $Root "tests\wasm\std_web_smoke.pengu"
if (Test-Path $wasmSmoke) { $files += Get-Item $wasmSmoke }
$jsSmoke = Join-Path $Root "tests\wasm\js_smoke.pengu"
if (Test-Path $jsSmoke) { $files += Get-Item $jsSmoke }
foreach ($f in $files) {
    $text = Get-Content -Raw $f.FullName
    if ($text -notmatch 'weave main') { continue }
    if ($f.Name -match '^(bench_|fuzz_)') { continue }
    if ($env:PSC_SKIP_PETITIO -eq '1' -and $f.Name -match '^petitio_') { continue }
    $count++
    & $Psc run $f.FullName --no-cache
    if ($LASTEXITCODE -ne 0) { Write-Host "FAIL $($f.FullName)"; $fail++ }
}
if ($fail -ne 0) { Write-Host "$fail of $count failed"; exit 1 }
Write-Host "OK $count PSC test file(s)"
