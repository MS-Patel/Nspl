#!/usr/bin/env bash
set -euo pipefail

# Relationship exports contain PAN data. New files should be owner-readable only.
umask 077

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

if [[ -x "$PROJECT_DIR/env/bin/python" ]]; then
    PYTHON_EXECUTABLE="$PROJECT_DIR/env/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_EXECUTABLE="python3"
else
    echo "Python 3 was not found." >&2
    exit 1
fi

exec "$PYTHON_EXECUTABLE" manage.py export_bbf_relationships "$@"
