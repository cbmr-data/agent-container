# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Mikkel Schubert
from __future__ import annotations

import argparse
import dataclasses
import functools
from pathlib import Path
from typing import Literal, get_args

from agent_container._common import value_list
from agent_container._parser import parse

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LOG_LEVELS = get_args(LogLevel)

ShellCommand = Literal["bash", "shell"]
AgentCommand = Literal["claude", "codex", "copilot", "gemini", "vibe"]
OtherCommands = Literal["new", "list"]
Command = Literal[AgentCommand, OtherCommands, ShellCommand]

SHELL_COMMANDS: tuple[str, ...] = get_args(ShellCommand)
AGENT_COMMANDS: tuple[str, ...] = get_args(AgentCommand)
OTHER_COMMANDS: tuple[str, ...] = get_args(OtherCommands)
COMMANDS = get_args(Command)


@dataclasses.dataclass
class Args:
    log_level: LogLevel
    read_only: bool
    include: list[Path]
    command: Command
    arguments: list[str]


def parse_args(argv: list[str]) -> Args:
    parser = argparse.ArgumentParser(
        prog="agent-container",
        formatter_class=functools.partial(
            argparse.ArgumentDefaultsHelpFormatter,
            width=79,
        ),
        allow_abbrev=False,
    )

    parser.add_argument(
        "--log-level",
        type=str.upper,
        choices=LOG_LEVELS,
        default="INFO",
        metavar="LEVEL",
        help="Log-level for messages produced by agent-container. Possible values are "
        + value_list(LOG_LEVELS),
    )

    parser.add_argument(
        "--read-only",
        default=False,
        action="store_true",
        help="Mount the current folder and included folders as read-only. Does not "
        "affect includes explicitly flagged with `:ro` or `:rw`",
    )

    parser.add_argument(
        "--include",
        type=_non_empty_path,
        default=[],
        action="append",
        help="Make this this folder available in the agent container. By default, "
        "included folders are writable unless the `--read-only` option is used. "
        "Alternatively, the paths pay be suffixed with `:ro` or `:rw` to explicitly "
        "mark them as read-only or read/writable, in which caes `--read-only` does not "
        "affect the include",
    )

    parser.add_argument(
        "command",
        type=str.lower,
        metavar="COMMAND",
        choices=get_args(Command),
        help="The agent or shell to run in the current workspace, or a command to "
        f"manipulate workspaces. Possible values are {value_list(COMMANDS)}",
    )

    parser.add_argument(
        "arguments",
        # REMAINDER is an undocumented legacy feature. It only works if it is preceded
        # by another positional argument, and should therefore be safe in this case.
        # For more information, see https://bugs.python.org/issue17050#msg315716
        nargs=argparse.REMAINDER,
        help="Arguments to be passed to the shell or agent. All arguments after the "
        "COMMAND will be passed as-is",
    )

    args = parser.parse_args(argv)

    return parse(Args, vars(args))


def _non_empty_path(value: str) -> Path:
    if not value:
        raise argparse.ArgumentTypeError(f"non-empty path required, but got {value!r}")

    return Path(value).resolve()
