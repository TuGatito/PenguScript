$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Psc = if ($env:PSC) { $env:PSC } else { Join-Path $Root "build\psc.exe" }
Set-Location $Root
$fail = 0
$count = 0
$files = @(Get-ChildItem tests\pengu\*.pengu -File -ErrorAction SilentlyContinue)
$files += @(Get-ChildItem tests\conformance -Recurse -Filter *.pengu -File -ErrorAction SilentlyContinue)
foreach ($f in $files) {
    $text = Get-Content -Raw $f.FullName
    if ($text -notmatch 'weave main') { continue }
    if ($f.Name -match '^(bench_|fuzz_)') { continue }
    $count++
    & $Psc run $f.FullName --no-cache
    if ($LASTEXITCODE -ne 0) { Write-Host "FAIL $($f.FullName)"; $fail++ }
}
if ($fail -ne 0) { Write-Host "$fail of $count failed"; exit 1 }
Write-Host "OK $count PSC test file(s)"
