#!/usr/bin/env bash
# Update the installed SkillManager from this project folder — no GitHub download.
#
# Usage (one line, run from the project root):
#   bash scripts/update-local.sh
#
# What it does:
#   1. Builds the .deb from local source (uv run skill-manager-build linux --deb)
#   2. Installs it with dpkg (replaces the /usr/bin/skill-manager system package)
#   3. Removes a stale ~/.local/bin/skill-manager that would shadow the new install
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> Building app bundle from local source (PyInstaller)..."
uv run python -m PyInstaller --noconfirm packaging/skill_manager.spec

echo "==> Packaging .deb from local bundle..."
uv run skill-manager-build linux --deb

DEB=$(ls -t dist/skill-manager_*_amd64.deb 2>/dev/null | head -n 1)
if [ -z "${DEB}" ]; then
    echo "ERROR: no .deb found in dist/ after build." >&2
    exit 1
fi

echo "==> Installing ${DEB}..."
sudo dpkg -i "${DEB}"

USER_BIN="${HOME}/.local/bin/skill-manager"
if [ -e "${USER_BIN}" ] || [ -L "${USER_BIN}" ]; then
    echo "==> Removing shadowing user-level binary: ${USER_BIN}"
    rm -f "${USER_BIN}"
fi

echo "==> Done. Installed version:"
skill-manager --version 2>/dev/null || /usr/bin/skill-manager --version 2>/dev/null || echo "(version check flag unavailable — launch the app to confirm)"
