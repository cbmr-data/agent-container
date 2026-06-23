# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Mikkel Schubert
from __future__ import annotations

import dataclasses
import re
from pathlib import Path

import pytest

from agent_container._parser import ParseError, parse, parse_toml


@dataclasses.dataclass
class SimpleDC:
    regex: re.Pattern[str] | None = None
    path: Path | None = None


def test_parse_dataclass_with_defaults() -> None:
    assert parse(SimpleDC, {}) == SimpleDC(
        regex=None,
        path=None,
    )


def test_parse_dataclass() -> None:
    data = {"regex": re.compile("foo"), "path": Path("/some/path")}

    assert parse(SimpleDC, data) == SimpleDC(
        regex=re.compile("foo"),
        path=Path("/some/path"),
    )


def test_parse_dataclass_with_coercion() -> None:
    data = {"regex": "foo", "path": "/some/path"}

    assert parse(SimpleDC, data) == SimpleDC(
        regex=re.compile("foo"),
        path=Path("/some/path"),
    )


def test_parse_with_invalid_path_raises_parse_error() -> None:
    data = {"path": ""}

    with pytest.raises(ParseError, match="invalid configuration"):
        parse(SimpleDC, data)


def test_parse_with_path_type_error_raises_parse_error() -> None:
    data = {"path": 1}

    with pytest.raises(ParseError, match="invalid configuration"):
        parse(SimpleDC, data)


def test_parse_with_invalid_regex_raises_parse_error() -> None:
    data = {"regex": "(unclosed"}

    with pytest.raises(ParseError, match="invalid configuration"):
        parse(SimpleDC, data)


def test_parse_with_regex_type_error_raises_parse_error() -> None:
    data = {"regex": 1}

    with pytest.raises(ParseError, match="invalid configuration"):
        parse(SimpleDC, data)


def test_parse_with_bytes_regex_raises_parse_error() -> None:
    data = {"regex": re.compile(b"foo")}

    with pytest.raises(ParseError, match="invalid configuration"):
        parse(SimpleDC, data)


def test_parse_prohibits_unknown_keys() -> None:
    data = {"path": "/foo/bar", "foo": 1}

    with pytest.raises(ParseError, match="invalid configuration"):
        parse(SimpleDC, data)


def test_parse_toml_with_invalid_toml_raises_parse_error(tmp_path: Path) -> None:
    filename = tmp_path / "config.toml"
    filename.write_text('path = "unclosed')

    with pytest.raises(ParseError, match="error reading TOML file"):
        parse_toml(SimpleDC, filename)


def test_parse_toml_with_invalid_regex_raises_parse_error(tmp_path: Path) -> None:
    filename = tmp_path / "config.toml"
    filename.write_text('regex = "(unclosed"')

    with pytest.raises(ParseError, match="failed to parse TOML file"):
        parse_toml(SimpleDC, filename)


def test_parse_toml_prohibits_unknown_keys(tmp_path: Path) -> None:
    filename = tmp_path / "config.toml"
    filename.write_text('path = "/foo/bar"\nfoo = 1')

    with pytest.raises(ParseError, match="failed to parse TOML file"):
        parse_toml(SimpleDC, filename)
