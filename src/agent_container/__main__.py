# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Mikkel Schubert
from __future__ import annotations

import sys
from typing import NoReturn

from agent_container import _main


def entrypoint() -> NoReturn:
    sys.exit(_main.main())


if __name__ == "__main__":
    entrypoint()
