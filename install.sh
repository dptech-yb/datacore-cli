#!/bin/sh
set -eu

REPO="dptech-yb/datacore-cli"
INSTALL_ROOT="${DATACORE_INSTALL_ROOT:-$HOME/.local/share/datacore-cli}"
BIN_DIR="${DATACORE_BIN_DIR:-$HOME/.local/bin}"
VERSION="${DATACORE_VERSION:-latest}"
RUN_SETUP=1
ALLOW_FILE_CREDENTIAL=0
UNINSTALL=0

usage() {
  printf '%s\n' "Usage: install.sh [--version v0.2.0] [--no-setup] [--allow-file-credential] [--uninstall]"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --version)
      [ "$#" -ge 2 ] || { usage; exit 2; }
      VERSION="$2"
      shift 2
      ;;
    --no-setup) RUN_SETUP=0; shift ;;
    --allow-file-credential) ALLOW_FILE_CREDENTIAL=1; shift ;;
    --uninstall) UNINSTALL=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown option: %s\n' "$1" >&2; usage; exit 2 ;;
  esac
done

if [ "$UNINSTALL" -eq 1 ]; then
  if [ -x "$INSTALL_ROOT/venv/bin/datacore" ]; then
    "$INSTALL_ROOT/venv/bin/datacore" auth logout >/dev/null 2>&1 || true
  fi
  rm -f "$BIN_DIR/datacore"
  rm -rf "$INSTALL_ROOT"
  rm -rf "$HOME/.codex/skills/datacore" "$HOME/.codex/skills/datacore-conductivity"
  printf '%s\n' "DataCore CLI and DataCore Skills were removed."
  exit 0
fi

need() {
  command -v "$1" >/dev/null 2>&1 || {
    printf 'Required command not found: %s\n' "$1" >&2
    exit 1
  }
}

need curl

PYTHON=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    PYTHON="$candidate"
    break
  fi
done
if [ -z "$PYTHON" ]; then
  printf '%s\n' "Python 3.10 or newer is required: https://www.python.org/downloads/" >&2
  exit 1
fi

if [ "$VERSION" = "latest" ]; then
  VERSION="$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" | sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)"
fi
case "$VERSION" in
  v*) PACKAGE_VERSION="${VERSION#v}" ;;
  *) PACKAGE_VERSION="$VERSION"; VERSION="v$VERSION" ;;
esac
[ -n "$PACKAGE_VERSION" ] || { printf '%s\n' "Unable to resolve release version." >&2; exit 1; }

WHEEL="datacore_cli-${PACKAGE_VERSION}-py3-none-any.whl"
BASE="${DATACORE_RELEASE_BASE:-https://github.com/$REPO/releases/download/$VERSION}"
TMP="$(mktemp -d 2>/dev/null || mktemp -d -t datacore-cli)"
trap 'rm -rf "$TMP"' EXIT HUP INT TERM

printf 'Downloading DataCore CLI %s...\n' "$VERSION"
curl -fL --retry 3 --retry-connrefused --retry-delay 1 -o "$TMP/$WHEEL" "$BASE/$WHEEL"
curl -fL --retry 3 --retry-connrefused --retry-delay 1 -o "$TMP/SHA256SUMS" "$BASE/SHA256SUMS"

EXPECTED="$(awk -v file="$WHEEL" '$2 == file || $2 == "*" file {print $1}' "$TMP/SHA256SUMS" | head -n 1)"
[ -n "$EXPECTED" ] || { printf '%s\n' "Release checksum entry is missing." >&2; exit 1; }
if command -v sha256sum >/dev/null 2>&1; then
  ACTUAL="$(sha256sum "$TMP/$WHEEL" | awk '{print $1}')"
else
  need shasum
  ACTUAL="$(shasum -a 256 "$TMP/$WHEEL" | awk '{print $1}')"
fi
[ "$ACTUAL" = "$EXPECTED" ] || { printf '%s\n' "SHA256 verification failed; refusing installation." >&2; exit 1; }

mkdir -p "$INSTALL_ROOT" "$BIN_DIR"
if [ ! -x "$INSTALL_ROOT/venv/bin/python" ]; then
  "$PYTHON" -m venv "$INSTALL_ROOT/venv"
fi
"$INSTALL_ROOT/venv/bin/python" -m pip install --disable-pip-version-check --upgrade "$TMP/$WHEEL"
ln -sf "$INSTALL_ROOT/venv/bin/datacore" "$BIN_DIR/datacore"

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *)
    PROFILE="$HOME/.profile"
    [ "${SHELL:-}" = "/bin/zsh" ] && PROFILE="$HOME/.zprofile"
    LINE='export PATH="$HOME/.local/bin:$PATH"'
    if [ ! -f "$PROFILE" ] || ! grep -F "$LINE" "$PROFILE" >/dev/null 2>&1; then
      printf '\n%s\n' "$LINE" >> "$PROFILE"
    fi
    export PATH="$BIN_DIR:$PATH"
    printf 'Added %s to PATH in %s.\n' "$BIN_DIR" "$PROFILE"
    ;;
esac

"$BIN_DIR/datacore" skills install --force
printf 'Installed DataCore CLI %s.\n' "$PACKAGE_VERSION"

if [ "$RUN_SETUP" -eq 1 ]; then
  if [ "$ALLOW_FILE_CREDENTIAL" -eq 1 ]; then
    "$BIN_DIR/datacore" setup --allow-file-credential
  else
    "$BIN_DIR/datacore" setup
  fi
else
  printf '%s\n' "Run 'datacore setup' to authorize this device."
fi
