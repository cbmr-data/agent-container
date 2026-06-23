# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Mikkel Schubert
from __future__ import annotations

from pathlib import Path

import pytest

from agent_container._args import (
    AGENT_COMMANDS,
    LOG_LEVELS,
    OTHER_COMMANDS,
    SHELL_COMMANDS,
    Args,
    parse_args,
)

COMMANDS = (*AGENT_COMMANDS, *OTHER_COMMANDS, *SHELL_COMMANDS)


def test_parse_args_with_no_arguments(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):  # noqa: PT011
        parse_args([])
    result = capsys.readouterr()
    assert result.err.startswith("usage: agent-container [-h]")


def test_parse_args_with_minimal_arguments() -> None:
    assert parse_args(["shell"]) == Args(
        log_level="INFO",
        read_only=False,
        include=[],
        command="shell",
        arguments=[],
    )


def test_parse_args_with_read_only() -> None:
    assert parse_args(["--read-only", "shell"]) == Args(
        log_level="INFO",
        read_only=True,
        include=[],
        command="shell",
        arguments=[],
    )


def test_parse_args_with_includes() -> None:
    assert parse_args(["--include", "/foo", "shell"]) == Args(
        log_level="INFO",
        read_only=False,
        include=[Path("/foo")],
        command="shell",
        arguments=[],
    )

    assert parse_args(["--include", "/foo", "--include", "/bar", "shell"]) == Args(
        log_level="INFO",
        read_only=False,
        include=[Path("/foo"), Path("/bar")],
        command="shell",
        arguments=[],
    )


def test_parse_args_with_include_rejects_empty_paths(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit):  # noqa: PT011
        parse_args(["--include", "", "shell"])
    result = capsys.readouterr()
    assert "error: argument --include: non-empty path required" in result.err


@pytest.mark.parametrize("level", LOG_LEVELS)
def test_parse_args_with_log_level(level: str) -> None:
    assert parse_args(["--log-level", level, "shell"]).log_level == level
    assert parse_args(["--log-level", level.title(), "shell"]).log_level == level
    assert parse_args(["--log-level", level.lower(), "shell"]).log_level == level
    assert parse_args(["--log-level", level.upper(), "shell"]).log_level == level


def test_parse_args_with_invalid_log_level(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):  # noqa: PT011
        parse_args(["--log-level", "URGENT", "shell"])
    result = capsys.readouterr()
    assert "invalid choice: 'URGENT'" in result.err


def test_parse_args_with_passed_args() -> None:
    expected = ["--foo", "--bar", "zed"]

    assert parse_args(["shell", "--foo", "--bar", "zed"]).arguments == expected
    assert parse_args(["shell", "--", "--foo", "--bar", "zed"]).arguments == expected


def test_parse_args_with_passed_args_matching_known_arguments_1() -> None:
    args = parse_args(["shell", "--log-level", "ERROR"])
    assert args.log_level == "INFO"
    assert args.arguments == ["--log-level", "ERROR"]

    args = parse_args(["shell", "--", "--log-level", "ERROR"])
    assert args.log_level == "INFO"
    assert args.arguments == ["--log-level", "ERROR"]


def test_parse_args_with_passed_args_matching_known_arguments_2() -> None:
    assert parse_args(["shell", "--help"]).arguments == ["--help"]
    assert parse_args(["shell", "--", "--help"]).arguments == ["--help"]


def test_parse_args_with_similar_args_and_passed_args() -> None:
    args = parse_args(["--log-level", "WARNING", "shell", "--log-level", "ERROR"])
    assert args.log_level == "WARNING"
    assert args.arguments == ["--log-level", "ERROR"]


@pytest.mark.parametrize("command", COMMANDS)
def test_parse_args_command_is_case_insensitive(command: str) -> None:
    assert parse_args([command]).command == command
    assert parse_args([command.title()]).command == command
    assert parse_args([command.lower()]).command == command
    assert parse_args([command.upper()]).command == command


def test_parse_args_with_invalid_command(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):  # noqa: PT011
        parse_args(["not-a-command"])
    result = capsys.readouterr()
    assert "invalid choice: 'not-a-command'" in result.err
