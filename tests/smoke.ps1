$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Psc = if ($env:PSC) { $env:PSC } else { Join-Path $Root "build\psc.exe" }
Set-Location $Root
$files = @(
  "tests\pengu\lexer_unit.pengu",
  "tests\pengu\parser_unit.pengu",
  "tests\pengu\lexer_corpus.pengu",
  "tests\pengu\parser_corpus.pengu",
  "tests\pengu\flag.pengu"
)
foreach ($f in $files) {
  if (Test-Path $f) { & $Psc run $f --no-cache; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
}
Write-Host "OK compiler smoke"
