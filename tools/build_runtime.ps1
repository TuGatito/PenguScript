$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$CC = if ($env:CC) { $env:CC } else { "cc" }
$AR = if ($env:AR) { $env:AR } else { "ar" }
$Out = Join-Path $Root "build"
$Inc = Join-Path $Out "include"
$Lib = Join-Path $Out "lib"
$Obj = Join-Path $Out "obj_runtime"
$SObj = Join-Path $Out "obj_std_c"
New-Item -ItemType Directory -Force -Path $Inc,$Lib,$Obj,$SObj | Out-Null
Copy-Item (Join-Path $Root "pengu_runtime.h") (Join-Path $Inc "pengu_runtime.h") -Force
Copy-Item (Join-Path $Root "std_c/sds/sds.h") (Join-Path $Inc "sds.h") -Force
$flags = @("-O2", "-I$Root", "-I$Inc", "-I$Root/std_c/sds", "-ffunction-sections", "-fdata-sections")
foreach ($pair in @(@("pengu_runtime.o","0"), @("pengu_runtime_filum.o","1"))) {
  & $CC @flags "-DPENGU_ENABLE_THREADS=$($pair[1])" "-DPENGU_RUNTIME_SUBSYSTEM_ONLY=$($pair[1])" `
    -c (Join-Path $Root "runtime/pengu_runtime.c") -o (Join-Path $Obj $pair[0])
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
# SDS is compiled into libpengu_runtime.a so existing projects keep linking
# only -lpengu_runtime.
& $CC -O2 -std=c99 -Wall -Wextra -Werror "-I$Root/std_c/sds" `
  -ffunction-sections -fdata-sections `
  -c (Join-Path $Root "std_c/sds/sds.c") -o (Join-Path $SObj "sds.o")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$runtime = Join-Path $Lib "libpengu_runtime.a"
Remove-Item $runtime -ErrorAction SilentlyContinue
& $AR rcs $runtime (Join-Path $Obj "pengu_runtime.o") (Join-Path $Obj "pengu_runtime_filum.o") (Join-Path $SObj "sds.o")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Get-ChildItem (Join-Path $Root "std_c") -Filter *.h | Copy-Item -Destination $Inc -Force
Get-ChildItem (Join-Path $Root "std_c") -Filter *.c | ForEach-Object {
  $name = $_.BaseName
  if ($name -eq "petitio") { return }
  $extra = @()
  if ($name -eq "miniz") { $extra = @("-DMINIZ_NO_ZLIB_COMPATIBLE_NAMES","-DMINIZ_NO_ARCHIVE_APIS","-DMINIZ_NO_STDIO","-DMINIZ_NO_TIME","-Wno-type-limits") }
  & $CC -O2 -std=c99 -Wall -Wextra -Werror "-I$Root/std_c" "-I$Root" "-I$Inc" "-I$Root/std_c/sds" -ffunction-sections -fdata-sections @extra -c $_.FullName -o (Join-Path $SObj "$name.o")
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  $lib = Join-Path $Lib "lib$name.a"
  Remove-Item $lib -ErrorAction SilentlyContinue
  & $AR rcs $lib (Join-Path $SObj "$name.o")
}
Write-Host "[runtime] built $Lib"
