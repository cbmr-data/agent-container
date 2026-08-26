# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Mikkel Schubert
from __future__ import annotations

import logging
import os
from collections.abc import Iterable
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Literal

from agent_container._common import SequenceNotStr

__all__ = [
    "BindDir",
    "SingularityError",
    "run_singularity",
]

LOG = logging.getLogger(__name__)
SINGULARITY_HOME = Path("/home/singularity")


class SingularityError(RuntimeError):
    pass


@dataclass(frozen=True)
class BindDir:
    src: Path
    dst: Path
    mode: Literal["ro", "rw"] | None = None

    def format(self, *, read_only: bool) -> str:
        """Format bind-dirs to be used as --bind arguments"""
        escaped_path: list[str] = [
            BindDir._escape_path(self.src),
            ":",
            BindDir._escape_path(self.dst),
        ]

        mode = self.mode
        if mode is None and read_only:
            mode = "ro"

        if mode is not None:
            escaped_path.append(f":{mode}")

        return "".join(escaped_path)

    @staticmethod
    def _escape_path(path: Path) -> str:
        escaped_path: list[str] = []
        for char in str(path):
            if char in ",:\\":
                escaped_path.append("\\")
            escaped_path.append(char)

        return "".join(escaped_path)


def run_singularity(
    *,
    exe: str,
    image: Path,
    home: Path,
    cwd: Path,
    binds: Iterable[BindDir] = (),
    argv: SequenceNotStr[str] = (),
    read_only: bool = False,
) -> None:
    command: list[str] = [
        exe,
        "run",
        "--containall",
        "--writable-tmpfs",
        "--home",
        BindDir(home, SINGULARITY_HOME).format(read_only=False),
        "--pwd",
        str(cwd),
        "--bind",
        _format_binds([*binds, BindDir(cwd, cwd)], read_only=read_only),
        str(image),
    ]

    LOG.debug("running os.execv(%r, %r ...)", exe, command)
    try:
        os.execv(exe, [*command, *argv])  # noqa: S606
    except OSError as error:
        raise SingularityError(f"failed to run singularity: {error}") from error


def _format_binds(binds: Iterable[BindDir], *, read_only: bool) -> str:
    # Duplicates are ignored, as includes and cwd may overlap. Sorting is required both
    # for conflict checks and for nested binds (e.g. /foo *and* then /foo/bar)
    binds = sorted(set(binds), key=lambda it: it.dst)
    for bind_a, bind_b in pairwise(binds):
        if bind_a.dst == bind_b.dst:
            raise SingularityError(
                f"conflicting bindings at destination '{bind_a.dst}'"
            )

    for bind in binds:
        if bind.dst == SINGULARITY_HOME:
            raise SingularityError(
                f"cannot bind '{SINGULARITY_HOME}': path is reserved"
            )

    return ",".join(bind.format(read_only=read_only) for bind in binds)
