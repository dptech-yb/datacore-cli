#!/bin/sh
set -eu

INSTALL_ROOT="${DATACORE_INSTALL_ROOT:-$HOME/.local/share/datacore-cli}"
BIN_DIR="${DATACORE_BIN_DIR:-$HOME/.local/bin}"
SKILLS_DIR="${DATACORE_SKILLS_DIR:-$HOME/.agents/skills}"
PURGE_BACKUPS=0
KEEP_AUTHORIZATION=0

usage() {
  printf '%s\n' "Usage: uninstall.sh [--purge-backups] [--keep-authorization]"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --purge-backups) PURGE_BACKUPS=1; shift ;;
    --keep-authorization) KEEP_AUTHORIZATION=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown option: %s\n' "$1" >&2; usage; exit 2 ;;
  esac
done

HOME_REAL="$(cd "$HOME" 2>/dev/null && pwd -P)" || {
  printf '%s\n' "Unable to resolve the current home directory." >&2
  exit 1
}

INSTALL_REAL=""
if [ -e "$INSTALL_ROOT" ]; then
  INSTALL_REAL="$(cd "$INSTALL_ROOT" 2>/dev/null && pwd -P)" || {
    printf '%s\n' "Refusing uninstall: install root is not a directory." >&2
    exit 1
  }
  case "$INSTALL_REAL" in
    /|"$HOME_REAL")
      printf 'Refusing uninstall from unsafe path: %s\n' "$INSTALL_REAL" >&2
      exit 1
      ;;
  esac
  if [ ! -f "$INSTALL_REAL/.datacore-cli-install" ] && [ ! -x "$INSTALL_REAL/venv/bin/datacore" ]; then
    printf 'Refusing uninstall: %s is not a DataCore CLI installation.\n' "$INSTALL_REAL" >&2
    exit 1
  fi
fi

CLI=""
CLI_PYTHON=""
if [ -n "$INSTALL_REAL" ] && [ -x "$INSTALL_REAL/venv/bin/datacore" ]; then
  CLI="$INSTALL_REAL/venv/bin/datacore"
  [ ! -x "$INSTALL_REAL/venv/bin/python" ] || CLI_PYTHON="$INSTALL_REAL/venv/bin/python"
fi

REMOTE_REVOCATION_WARNING=0
if [ -n "$CLI" ]; then
  if [ "$KEEP_AUTHORIZATION" -eq 0 ]; then
    HAS_AUTHORIZATION=0
    if [ -n "$CLI_PYTHON" ] && "$CLI_PYTHON" -c '
from datacore_cli.credentials import load_token
from datacore_cli.main import DEFAULT_BASE_URL
raise SystemExit(0 if load_token(DEFAULT_BASE_URL) else 1)
' >/dev/null 2>&1; then
      HAS_AUTHORIZATION=1
    fi
    if [ "$HAS_AUTHORIZATION" -eq 1 ]; then
      "$CLI" auth logout >/dev/null 2>&1 || REMOTE_REVOCATION_WARNING=1
    fi
    "$CLI" uninstall --yes >/dev/null 2>&1 || {
      printf '%s\n' "Warning: local credential or DataCore Skills could not be removed automatically." >&2
    }
  else
    "$CLI" skills uninstall --yes >/dev/null 2>&1 || {
      printf '%s\n' "Warning: DataCore Skills could not be removed automatically." >&2
    }
  fi
else
  printf '%s\n' "Warning: no DataCore CLI was available to clean authorization and Skills." >&2
fi

if [ "$KEEP_AUTHORIZATION" -eq 0 ] && [ -n "$CLI_PYTHON" ]; then
  CREDENTIAL_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/datacore/credentials.json"
  "$CLI_PYTHON" - "$CREDENTIAL_FILE" <<'PY' || true
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    value = json.loads(path.read_text(encoding="utf-8"))
except (FileNotFoundError, OSError, ValueError):
    raise SystemExit(0)
if isinstance(value, dict) and not value:
    path.unlink(missing_ok=True)
    try:
        path.parent.rmdir()
    except OSError:
        pass
PY
fi

PROFILE_MARKER=""
if [ -n "$INSTALL_REAL" ] && [ -f "$INSTALL_REAL/.datacore-cli-profile" ]; then
  PROFILE_MARKER="$(sed -n '1p' "$INSTALL_REAL/.datacore-cli-profile")"
fi

LAUNCHER="$BIN_DIR/datacore"
if [ -L "$LAUNCHER" ]; then
  LINK_TARGET="$(readlink "$LAUNCHER")"
  case "$LINK_TARGET" in
    "$INSTALL_ROOT/venv/bin/datacore"|"$INSTALL_REAL/venv/bin/datacore")
      rm -f "$LAUNCHER"
      ;;
    *)
      printf 'Warning: kept unrelated launcher %s -> %s.\n' "$LAUNCHER" "$LINK_TARGET" >&2
      ;;
  esac
elif [ -e "$LAUNCHER" ]; then
  printf 'Warning: kept non-symlink launcher %s.\n' "$LAUNCHER" >&2
fi

if [ -n "$INSTALL_REAL" ]; then
  rm -rf "$INSTALL_REAL"
fi

# shellcheck disable=SC2016 # Match the literal line written by install.sh.
PROFILE_LINE='export PATH="$HOME/.local/bin:$PATH"'
if [ -n "$PROFILE_MARKER" ]; then
  case "$PROFILE_MARKER" in
    "$HOME_REAL"/.profile|"$HOME_REAL"/.zprofile)
      if [ -f "$PROFILE_MARKER" ]; then
        PROFILE_TEMP="$PROFILE_MARKER.datacore-uninstall.$$"
        trap 'rm -f "$PROFILE_TEMP"' EXIT HUP INT TERM
        awk -v line="$PROFILE_LINE" '$0 != line { print }' "$PROFILE_MARKER" > "$PROFILE_TEMP"
        cat "$PROFILE_TEMP" > "$PROFILE_MARKER"
        rm -f "$PROFILE_TEMP"
        trap - EXIT HUP INT TERM
      fi
      ;;
    *)
      printf 'Warning: ignored unsafe profile record %s.\n' "$PROFILE_MARKER" >&2
      ;;
  esac
fi

if [ "$PURGE_BACKUPS" -eq 1 ]; then
  SKILLS_PARENT="$(dirname "$SKILLS_DIR")"
  BACKUP_ROOT="$SKILLS_PARENT/datacore-skill-backups"
  if [ -e "$BACKUP_ROOT" ]; then
    BACKUP_REAL="$(cd "$BACKUP_ROOT" 2>/dev/null && pwd -P)" || {
      printf 'Warning: could not resolve backup directory %s.\n' "$BACKUP_ROOT" >&2
      BACKUP_REAL=""
    }
    if [ -n "$BACKUP_REAL" ]; then
      case "$BACKUP_REAL" in
        "$HOME_REAL"/*) rm -rf "$BACKUP_REAL" ;;
        *) printf 'Warning: refused to purge backups outside the home directory: %s.\n' "$BACKUP_REAL" >&2 ;;
      esac
    fi
  fi
fi

rmdir "$SKILLS_DIR" 2>/dev/null || true
rmdir "$(dirname "$SKILLS_DIR")" 2>/dev/null || true
rmdir "$BIN_DIR" 2>/dev/null || true

if [ "$KEEP_AUTHORIZATION" -eq 1 ]; then
  printf '%s\n' "DataCore CLI and managed Skills were removed; device authorization was kept."
elif [ "$PURGE_BACKUPS" -eq 1 ]; then
  printf '%s\n' "DataCore CLI, managed Skills, backups, and the local device credential were removed."
else
  printf '%s\n' "DataCore CLI, managed Skills, and the local device credential were removed."
  printf '%s\n' "Safety backups of user-modified Skills, if any, were kept."
fi
if [ "$REMOTE_REVOCATION_WARNING" -eq 1 ]; then
  printf '%s\n' "Remote session revocation could not be confirmed; revoke this device in DataCore Personal Center if needed." >&2
fi
if [ "$KEEP_AUTHORIZATION" -eq 0 ] && [ -n "${DATACORE_TOKEN:-}" ]; then
  printf '%s\n' "DATACORE_TOKEN is still set in the environment; remove it from the environment or secret manager separately." >&2
fi
