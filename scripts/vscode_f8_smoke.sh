#!/usr/bin/env bash
# Smoke real de VS Code para F8. Requiere una sesión gráfica (Wayland/X11).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC_BIN:-$ROOT/psc/build/psc}"
WORK="$(mktemp -d /tmp/psc-f8-vscode.XXXXXX)"
FILE="$WORK/main.pengu"
UD="$WORK/user"
EXT="$WORK/ext"
mkdir -p "$WORK" "$UD" "$EXT"

cat > "$FILE" <<'PENGU'
weave main into int:
    var x as int is
PENGU

cleanup() {
  pkill -f "user-data-dir=$UD" 2>/dev/null || true
  rm -rf "$WORK"
}
trap cleanup EXIT

PSC_BIN="$PSC" PENGU_SMOKE_FILE="$FILE" \
  timeout 60 code --user-data-dir="$UD" --extensions-dir="$EXT" \
  --disable-gpu --no-sandbox --new-window \
  --extensionDevelopmentPath="$ROOT/vscode-extension" \
  --extensionTestsPath="$ROOT/vscode-extension/test/f8_smoke.js" \
  >/dev/null 2>&1 || true

LOG=""
for _ in $(seq 1 60); do
  LOG="$(find "$UD/logs" -name renderer.log -print 2>/dev/null | sort | tail -1)"
  if [ -n "$LOG" ] && grep -q 'F8_VSCODE_DIAGS=' "$LOG"; then
    break
  fi
  sleep 0.5
done
if [ -z "$LOG" ] || ! grep -q 'F8_VSCODE_DIAGS=' "$LOG"; then
  echo "vscode smoke: no diagnostics captured" >&2
  exit 1
fi
grep 'F8_VSCODE_DIAGS=' "$LOG" | tail -1
