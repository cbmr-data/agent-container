#!/bin/bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Mikkel Schubert
set -euo pipefail

mkdir -p "$HOME/.local/bin"

# Prevent claude from complaining about the global install on first run
if [ $# -ge 1 ] && [ "${1}" = "claude" ]; then
    if [ ! -e "$HOME/.local/bin/claude" ]; then
        echo "Performing first-time setup"
        /usr/local/bin/claude-installer install
    elif [ "$HOME/.local/bin/claude" -ot "/timestamp" ]; then
        echo "Upgrading claude"
        claude upgrade
    fi
fi

exec "${@}"
