#!/usr/bin/env bash
# Build the whole PenguScript toolchain in-tree and register its environment.
#
# Layout (all of it lives inside this checkout):
#
#   build/psc                 compiler
#   build/pengu-bind          optional libclang helper
#   build/lib/*.a             native runtime + std_c satellites
#   build/include/*.h         headers used by generated bundles
#   build/wasm/...            optional wasm runtime
#   build/env/pengu.env.*     generated shell environment
#
# The environment makes `psc` available from any directory without the user
# defining PENGU_INCLUDE_DIR/PENGU_LIB_DIR/PENGU_STD_DIR by hand. It is written
# for bash/zsh (POSIX sh), fish and PowerShell, and a small idempotent block is
# appended to the matching shell rc files unless --no-register is used.
#
# Usage:
#   ./tools/build.sh [--debug] [--no-bind] [--no-wasm] [--no-register]
#                    [--shells auto|bash,zsh,fish] [--jobs N] [--cc CMD]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PROFILE="release"
BUILD_BIND=1
BUILD_WASM=1
REGISTER=1
SHELLS="auto"
JOBS="${JOBS:-}"
CC_OVERRIDE=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --debug) PROFILE="debug" ;;
    --no-bind) BUILD_BIND=0 ;;
    --no-wasm) BUILD_WASM=0 ;;
    --no-register) REGISTER=0 ;;
    --shells)
      shift
      [ "$#" -gt 0 ] || { echo "build: missing value for --shells" >&2; exit 2; }
      SHELLS="$1"
      ;;
    --shells=*) SHELLS="${1#--shells=}" ;;
    --jobs)
      shift
      [ "$#" -gt 0 ] || { echo "build: missing value for --jobs" >&2; exit 2; }
      JOBS="$1"
      ;;
    --jobs=*) JOBS="${1#--jobs=}" ;;
    --cc)
      shift
      [ "$#" -gt 0 ] || { echo "build: missing value for --cc" >&2; exit 2; }
      CC_OVERRIDE="$1"
      ;;
    --cc=*) CC_OVERRIDE="${1#--cc=}" ;;
    -h|--help)
      awk 'NR > 1 { if ($0 ~ /^set -euo/) exit; if ($0 ~ /^#/) { sub(/^# ?/, ""); print } }' "$0"
      exit 0
      ;;
    *)
      echo "build: unknown option: $1" >&2
      exit 2
      ;;
  esac
  shift
done

if [ -n "$CC_OVERRIDE" ]; then
  export CC="$CC_OVERRIDE"
fi
if [ -n "$JOBS" ]; then
  export JOBS
fi

log() { printf '[build] %s\n' "$*"; }
warn() { printf '[build] warning: %s\n' "$*" >&2; }

# ---------------------------------------------------------------------------
# 1. Runtime + bootstrap compiler
# ---------------------------------------------------------------------------
log "building the native runtime and bootstrap compiler"
if ! "$ROOT/tools/build_bootstrap.sh"; then
  if [ -x "$ROOT/build/psc" ]; then
    warn "stage0 bootstrap failed; reusing the existing build/psc as bootstrap"
  else
    echo "build: cannot bootstrap psc (no stage0 bundle and no build/psc)" >&2
    exit 1
  fi
fi

BOOTSTRAP="$ROOT/build/psc-stage0"
if [ ! -x "$BOOTSTRAP" ]; then
  BOOTSTRAP="$ROOT/build/psc"
fi
if [ ! -x "$BOOTSTRAP" ]; then
  echo "build: no bootstrap compiler available" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# 2. Compiler
# ---------------------------------------------------------------------------
log "building psc ($PROFILE)"
"$BOOTSTRAP" build . --profile "$PROFILE" --no-cache
"$ROOT/build/psc" version

# ---------------------------------------------------------------------------
# 3. Optional helper: pengu-bind
# ---------------------------------------------------------------------------
if [ "$BUILD_BIND" = "1" ]; then
  if command -v llvm-config >/dev/null 2>&1 || command -v llvm-config-23 >/dev/null 2>&1 || [ -d /usr/include/clang-c ]; then
    if "$ROOT/tools/build_bind.sh" >/tmp/pengu-bind-build.log 2>&1; then
      log "built build/pengu-bind"
    else
      warn "pengu-bind was not built (optional); see /tmp/pengu-bind-build.log"
    fi
  else
    warn "libclang not found; skipping the optional pengu-bind helper"
  fi
fi

# ---------------------------------------------------------------------------
# 4. Optional wasm runtime
# ---------------------------------------------------------------------------
if [ "$BUILD_WASM" = "1" ] && command -v emcc >/dev/null 2>&1; then
  log "building the WebAssembly runtime"
  if ! "$ROOT/tools/build_runtime_wasm.sh"; then
    warn "wasm runtime build failed; native builds still work"
  fi
elif [ "$BUILD_WASM" = "1" ]; then
  log "emcc not found; skipping the optional wasm runtime"
fi

# ---------------------------------------------------------------------------
# 5. Generated environment files (inside the checkout)
# ---------------------------------------------------------------------------
ENV_DIR="$ROOT/build/env"
mkdir -p "$ENV_DIR"

sh_quote() { printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\\\''/g")"; }
json_escape() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }

PSC_PATH="$ROOT/build/psc"
BIND_PATH="$ROOT/build/pengu-bind"
WASM_DIR="$ROOT/build/wasm"
QROOT="$(sh_quote "$ROOT")"
QENV="$(sh_quote "$ENV_DIR")"
QPSC="$(sh_quote "$PSC_PATH")"
QBIND="$(sh_quote "$BIND_PATH")"
QROOT_BUILD="$(sh_quote "$ROOT/build")"
QWASM="$(sh_quote "$WASM_DIR")"

cat > "$ENV_DIR/pengu.env.sh" <<EOF
# Generated by tools/build.sh -- do not edit by hand.
# Source this from bash/zsh:  . "$ENV_DIR/pengu.env.sh"
export PENGU_HOME=$QROOT
export PENGU_LIB_DIR="\$PENGU_HOME/build/lib"
export PENGU_INCLUDE_DIR="\$PENGU_HOME/build/include"
export PENGU_STD_DIR="\$PENGU_HOME/std"
export PENGU_PSC=$QPSC
EOF
if [ -x "$BIND_PATH" ]; then
  printf 'export PENGU_BIND=%s\n' "$QBIND" >> "$ENV_DIR/pengu.env.sh"
fi
if [ -d "$WASM_DIR" ]; then
  printf 'export PENGU_RUNTIME_CROSS=%s\n' "$QWASM" >> "$ENV_DIR/pengu.env.sh"
fi
cat >> "$ENV_DIR/pengu.env.sh" <<EOF
case ":\$PATH:" in
  *":$ROOT/build:"*) ;;
  *) export PATH="$ROOT/build:\$PATH" ;;
esac
EOF

cat > "$ENV_DIR/pengu.env.fish" <<EOF
# Generated by tools/build.sh -- do not edit by hand.
# Source this from fish:  source $ENV_DIR/pengu.env.fish
set -gx PENGU_HOME $QROOT
set -gx PENGU_LIB_DIR "\$PENGU_HOME/build/lib"
set -gx PENGU_INCLUDE_DIR "\$PENGU_HOME/build/include"
set -gx PENGU_STD_DIR "\$PENGU_HOME/std"
set -gx PENGU_PSC $QPSC
EOF
if [ -x "$BIND_PATH" ]; then
  printf 'set -gx PENGU_BIND %s\n' "$QBIND" >> "$ENV_DIR/pengu.env.fish"
fi
if [ -d "$WASM_DIR" ]; then
  printf 'set -gx PENGU_RUNTIME_CROSS %s\n' "$QWASM" >> "$ENV_DIR/pengu.env.fish"
fi
cat >> "$ENV_DIR/pengu.env.fish" <<EOF
if not contains $QROOT_BUILD \$PATH
    set -gx PATH $QROOT_BUILD \$PATH
end
EOF

cat > "$ENV_DIR/pengu.env.ps1" <<EOF
# Generated by tools/build.sh -- do not edit by hand.
# Dot-source this from PowerShell:  . "$ENV_DIR/pengu.env.ps1"
\$env:PENGU_HOME = '$ROOT'
\$env:PENGU_LIB_DIR = Join-Path \$env:PENGU_HOME 'build\\lib'
\$env:PENGU_INCLUDE_DIR = Join-Path \$env:PENGU_HOME 'build\\include'
\$env:PENGU_STD_DIR = Join-Path \$env:PENGU_HOME 'std'
\$env:PENGU_PSC = Join-Path \$env:PENGU_HOME 'build\\psc.exe'
EOF
if [ -x "$BIND_PATH" ]; then
  printf "\$env:PENGU_BIND = Join-Path \$env:PENGU_HOME 'build\\\\pengu-bind.exe'\n" >> "$ENV_DIR/pengu.env.ps1"
fi
if [ -d "$WASM_DIR" ]; then
  printf "\$env:PENGU_RUNTIME_CROSS = Join-Path \$env:PENGU_HOME 'build\\\\wasm'\n" >> "$ENV_DIR/pengu.env.ps1"
fi
cat >> "$ENV_DIR/pengu.env.ps1" <<EOF
\$penguBin = Join-Path \$env:PENGU_HOME 'build'
if ((\$env:PATH -split ';') -notcontains \$penguBin) {
    \$env:PATH = \$penguBin + ';' + \$env:PATH
}
EOF

# Machine-readable description for editors/LSPs that do not source shell rc files.
version="$(cat "$ROOT/VERSION" 2>/dev/null || printf '0.0.0')"
bind_value=""
if [ -x "$BIND_PATH" ]; then bind_value="$(json_escape "$BIND_PATH")"; fi
wasm_value=""
if [ -d "$WASM_DIR" ]; then wasm_value="$(json_escape "$WASM_DIR")"; fi
cat > "$ENV_DIR/pengu.env.json" <<JSON
{
  "schema": 1,
  "version": "$(json_escape "$version")",
  "home": "$(json_escape "$ROOT")",
  "psc": "$(json_escape "$PSC_PATH")",
  "std": "$(json_escape "$ROOT/std")",
  "include": "$(json_escape "$ROOT/build/include")",
  "lib": "$(json_escape "$ROOT/build/lib")",
  "bind": "$bind_value",
  "wasm": "$wasm_value",
  "path": ["$(json_escape "$ROOT/build")"]
}
JSON

log "environment written to build/env/"

# ---------------------------------------------------------------------------
# 6. Register the environment in the user's shells
# ---------------------------------------------------------------------------
register=0
if [ "$REGISTER" = "1" ]; then
  CORE_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/pengu"
  mkdir -p "$CORE_DIR"
  cp "$ENV_DIR/pengu.env.sh" "$CORE_DIR/env.sh"
  cp "$ENV_DIR/pengu.env.fish" "$CORE_DIR/env.fish"
  cp "$ENV_DIR/pengu.env.ps1" "$CORE_DIR/env.ps1"
  cp "$ENV_DIR/pengu.env.json" "$CORE_DIR/env.json"
  QSH="$(sh_quote "$CORE_DIR/env.sh")"
  QFISH="$(sh_quote "$CORE_DIR/env.fish")"
  QPS="$(sh_quote "$CORE_DIR/env.ps1")"

  begin_marker="# >>> PenguScript toolchain >>>"
  end_marker="# <<< PenguScript toolchain <<<"

  ensure_block() {
    local file="$1" snippet="$2"
    mkdir -p "$(dirname "$file")"
    [ -e "$file" ] || : > "$file"
    local tmp
    tmp="$(mktemp "${TMPDIR:-/tmp}/pengu-rc.XXXXXX")"
    awk -v s="$begin_marker" -v e="$end_marker" '
      $0 == s { skip = 1; next }
      $0 == e { skip = 0; next }
      !skip { print }
    ' "$file" > "$tmp"
    printf '%s\n' "$snippet" >> "$tmp"
    mv "$tmp" "$file"
  }

  posix_snippet="$begin_marker
if [ -f $QSH ]; then . $QSH; fi
$end_marker"
  fish_snippet="$begin_marker
test -f $QFISH; and source $QFISH
$end_marker"
  ps_snippet="$begin_marker
if (Test-Path $QPS) { . $QPS }
$end_marker"

  want_shell() {
    case ",$SHELLS," in
      *,auto,*) command -v "$1" >/dev/null 2>&1 ;;
      *,"$1",*) return 0 ;;
      *) return 1 ;;
    esac
  }

  if want_shell bash; then
    [ -f "$HOME/.bashrc" ] || : > "$HOME/.bashrc"
    ensure_block "$HOME/.bashrc" "$posix_snippet"
    [ -f "$HOME/.bash_profile" ] || : > "$HOME/.bash_profile"
    ensure_block "$HOME/.bash_profile" "$posix_snippet"
    register=1
  fi
  if want_shell zsh; then
    [ -f "$HOME/.zshrc" ] || : > "$HOME/.zshrc"
    ensure_block "$HOME/.zshrc" "$posix_snippet"
    register=1
  fi
  if want_shell fish; then
    ensure_block "${XDG_CONFIG_HOME:-$HOME/.config}/fish/config.fish" "$fish_snippet"
    register=1
  fi

  # PowerShell profile (Windows, and pwsh on Unix when available).
  if command -v pwsh >/dev/null 2>&1 || [ -n "${WINDIR:-}" ]; then
    profile=""
    if command -v pwsh >/dev/null 2>&1; then
      profile="$(pwsh -NoProfile -NonInteractive -Command '$PROFILE.CurrentUserCurrentHost' 2>/dev/null | tr -d '\r')"
    elif [ -n "${USERPROFILE:-}" ]; then
      profile="$USERPROFILE/Documents/PowerShell/Microsoft.PowerShell_profile.ps1"
    fi
    if [ -n "$profile" ]; then
      ensure_block "$profile" "$ps_snippet"
      register=1
    fi
  fi

  if [ "$register" = "1" ]; then
    log "registered the toolchain environment in the shell startup files"
  else
    warn "no supported shell detected; the generated files are in build/env/"
  fi
fi

# ---------------------------------------------------------------------------
# 7. Summary
# ---------------------------------------------------------------------------
"$ROOT/build/psc" version
log "compiler:  $ROOT/build/psc"
log "runtime:   $ROOT/build/lib/libpengu_runtime.a"
log "headers:   $ROOT/build/include"
log "std:       $ROOT/std"
if [ -x "$ROOT/build/pengu-bind" ]; then
  log "bind:      $ROOT/build/pengu-bind"
fi
if [ "$REGISTER" = "1" ] && [ "$register" = "1" ]; then
  echo
  echo "Open a new terminal (or reload your shell) and run:"
  echo "  psc version"
  echo "  psc build /path/to/project"
  echo
  echo "Current shell:"
  echo "  bash/zsh: . \"${XDG_CONFIG_HOME:-$HOME/.config}/pengu/env.sh\""
  echo "  fish:     source \"${XDG_CONFIG_HOME:-$HOME/.config}/pengu/env.fish\""
else
  echo
  echo "Source the generated environment before using psc:"
  echo "  bash/zsh: . \"$ENV_DIR/pengu.env.sh\""
  echo "  fish:     source \"$ENV_DIR/pengu.env.fish\""
fi
