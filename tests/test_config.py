# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Mikkel Schubert
from __future__ import annotations

import logging
import re
from pathlib import Path

import pytest

from agent_container._config import Config
from agent_container._parser import ParseError


@pytest.fixture
def empty_file(tmp_path: Path) -> Path:
    empty_file = tmp_path / "empty-file"
    empty_file.touch()

    return empty_file


def test_config_from_empty_file(empty_file: Path) -> None:
    config = Config.load(empty_file)
    assert config == Config(
        allowed_workspaces=None,
        disallowed_workspaces=[],
        container=None,
        includes=[],
    )


def test_config_converts_allowed_workspaces_to_regex(tmp_path: Path) -> None:
    filename = tmp_path / "config.toml"
    filename.write_text('allowed_workspaces = ["/"]')

    config = Config.load(filename)
    assert config == Config(allowed_workspaces=[re.compile("/")])


def test_config_converts_disallowed_workspaces_to_regex(tmp_path: Path) -> None:
    filename = tmp_path / "config.toml"
    filename.write_text('disallowed_workspaces = ["/"]')

    config = Config.load(filename)
    assert config == Config(disallowed_workspaces=[re.compile("/")])


def test_config_converts_container_to_path(tmp_path: Path) -> None:
    filename = tmp_path / "config.toml"
    filename.write_text('container = "/path/to/container.sif"')

    config = Config.load(filename)
    assert config == Config(container=Path("/path/to/container.sif"))


def test_config_converts_includes_to_path(tmp_path: Path) -> None:
    filename = tmp_path / "config.toml"
    filename.write_text('includes = ["/path/to/include"]')

    config = Config.load(filename)
    assert config == Config(includes=[Path("/path/to/include")])


def test_config_example_is_a_valid_config_file() -> None:
    filename = Path(__file__).parent.parent / "agent-container.toml"
    config = Config.load(filename)
    assert config == Config(
        allowed_workspaces=[],
        container=Path("/path/to/container.sif"),
    )


@pytest.mark.parametrize("has_global_config", [True, False])
def test_config_uses_last_container(*, has_global_config: bool, tmp_path: Path) -> None:
    filename1 = tmp_path / "config1.toml"
    if has_global_config:
        filename1.write_text('container = "/path/to/default/container.sif"')

    filename2 = tmp_path / "config2.toml"
    filename2.write_text('container = "/path/to/user/container.sif"')

    config = Config.load(filename1, filename2)
    assert config == Config(container=Path("/path/to/user/container.sif"))


def test_config_uses_first_allowlist_if_non_empty(
    caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    filename1 = tmp_path / "config1.toml"
    filename1.write_text('allowed_workspaces = ["/path/to/allow"]')
    filename2 = tmp_path / "config2.toml"
    filename2.write_text('allowed_workspaces = ["/some/other/path"]')

    with caplog.at_level(logging.WARNING):
        config = Config.load(filename1, filename2)
    assert config == Config(allowed_workspaces=[re.compile("/path/to/allow")])
    assert f"skipping `allowed_workspaces` in '{filename2}'" in caplog.text


def test_config_uses_first_allowlist_even_if_empty(tmp_path: Path) -> None:
    filename1 = tmp_path / "config1.toml"
    filename1.write_text("allowed_workspaces = []")
    filename2 = tmp_path / "config2.toml"
    filename2.write_text('allowed_workspaces = ["/some/other/path"]')

    config = Config.load(filename1, filename2)
    assert config == Config(allowed_workspaces=[])


def test_config_uses_second_allowlist_if_first_is_unspecified(tmp_path: Path) -> None:
    filename1 = tmp_path / "config1.toml"
    filename1.touch()
    filename2 = tmp_path / "config2.toml"
    filename2.write_text('allowed_workspaces = ["/some/other/path"]')

    config = Config.load(filename1, filename2)
    assert config == Config(allowed_workspaces=[re.compile("/some/other/path")])


def test_config_uses_second_allowlist_if_first_is_unspecified_even_if_empty(
    tmp_path: Path,
) -> None:
    filename1 = tmp_path / "config1.toml"
    filename1.touch()
    filename2 = tmp_path / "config2.toml"
    filename2.write_text("allowed_workspaces = []")

    config = Config.load(filename1, filename2)
    assert config == Config(allowed_workspaces=[])


def test_config_merges_disallow_list(*, tmp_path: Path) -> None:
    filename1 = tmp_path / "config1.toml"
    filename1.write_text('disallowed_workspaces = ["/path/to/allow"]')
    filename2 = tmp_path / "config2.toml"
    filename2.write_text('disallowed_workspaces = ["/some/other/path"]')

    config = Config.load(filename1, filename2)
    assert config == Config(
        disallowed_workspaces=[
            re.compile("/path/to/allow"),
            re.compile("/some/other/path"),
        ]
    )


def test_config_merges_includes(*, tmp_path: Path) -> None:
    filename1 = tmp_path / "config1.toml"
    filename1.write_text('includes = ["/path/to/allow"]')
    filename2 = tmp_path / "config2.toml"
    filename2.write_text('includes = ["/some/other/path"]')

    config = Config.load(filename1, filename2)
    assert config == Config(
        includes=[
            Path("/path/to/allow"),
            Path("/some/other/path"),
        ]
    )


def test_config_with_relative_container_path_raises_parse_error(tmp_path: Path) -> None:
    filename = tmp_path / "config.toml"
    filename.write_text('container = "path/to/container"')

    with pytest.raises(
        ParseError,
        match=f"relative container path in '{filename}': 'path/to/container'",
    ):
        Config.load(filename)


def test_config_with_relative_include_path_raises_parse_error(tmp_path: Path) -> None:
    filename = tmp_path / "config.toml"
    filename.write_text('includes = ["path/to/include"]')

    with pytest.raises(
        ParseError,
        match=f"relative include path in '{filename}': 'path/to/include'",
    ):
        Config.load(filename)


def test_config_with_invalid_container_path_raises_parse_error(tmp_path: Path) -> None:
    filename = tmp_path / "config.toml"
    filename.write_text('container = ""')

    with pytest.raises(ParseError, match="could not coerce to Path"):
        Config.load(filename)


def test_config_with_invalid_include_path_raises_parse_error(tmp_path: Path) -> None:
    filename = tmp_path / "config.toml"
    filename.write_text('includes = [""]')

    with pytest.raises(ParseError, match="could not coerce to Path"):
        Config.load(filename)


def test_config_with_invalid_allow_regex_raises_parse_error(tmp_path: Path) -> None:
    filename = tmp_path / "config.toml"
    filename.write_text('allowed_workspaces = ["(unclosed"]')

    with pytest.raises(ParseError, match="could not coerce to Pattern"):
        Config.load(filename)


def test_config_with_invalid_disallow_regex_raises_parse_error(tmp_path: Path) -> None:
    filename = tmp_path / "config.toml"
    filename.write_text('disallowed_workspaces = ["(unclosed"]')

    with pytest.raises(ParseError, match="could not coerce to Pattern"):
        Config.load(filename)


def test_config_file_prohibits_unknown_keys(tmp_path: Path) -> None:
    filename = tmp_path / "config.toml"
    filename.write_text('allowed_workspaces = ["/"]\nfoo = 1')

    with pytest.raises(ParseError, match="__unknown_keys__"):
        Config.load(filename)


def test_config_rethrows_oserrors(tmp_path: Path) -> None:
    filename = tmp_path / "config.toml"
    filename.touch(mode=0o000)

    try:
        with pytest.raises(PermissionError, match="Permission denied"):
            Config.load(filename)
    finally:
        # allow cleanup by pytest
        filename.chmod(mode=0o700)
