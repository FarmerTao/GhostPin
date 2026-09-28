#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
SKILL_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
PYTHON="${PYTHON_BIN:-python3}"
"$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3,12) else "Python 3.12+ required; set PYTHON_BIN to an existing interpreter path.")'
"$PYTHON" -m venv "$SKILL_DIR/.venv"
"$SKILL_DIR/.venv/bin/python" -m pip install --disable-pip-version-check --no-cache-dir -r "$SCRIPT_DIR/requirements.txt"
"$SKILL_DIR/.venv/bin/python" -m pip check
printf '\nInstallation complete. Next:\n"%s" "%s" devices\n' "$SKILL_DIR/.venv/bin/python" "$SCRIPT_DIR/location.py"
