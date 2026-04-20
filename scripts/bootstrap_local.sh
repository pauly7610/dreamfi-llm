#!/usr/bin/env bash
set -euo pipefail

here="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$here/onyx_data"

echo "Launching Onyx (first run downloads images; can take ~10 min)..."
if command -v curl >/dev/null 2>&1; then
  curl -fsSL https://onyx.app/install_onyx.sh | bash
else
  echo "curl not installed — install Onyx manually: https://onyx.app" >&2
  exit 1
fi

echo
echo "Onyx launched. Open http://localhost:3000 to create the first admin user."
