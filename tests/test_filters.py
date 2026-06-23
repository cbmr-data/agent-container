# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Mikkel Schubert
from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import patch

from agent_container._filters import PathFilters
from tests.testutils import identity

########################################################################################
# PathFilters


def test_path_filters_disallows_everything_by_default() -> None:
    flt = PathFilters()

    assert not flt(Path())
    assert not flt(Path("/"))
    assert not flt(Path("/tmp"))
    assert not flt(Path("/tmp/"))
    assert not flt(Path("/tmp/foo"))
    assert not flt(Path("/home/foo"))


def test_path_filters_root_filter_allows_all_paths() -> None:
    flt = PathFilters(allow=(re.compile("/.*"),))
    with patch("pathlib.Path.resolve", identity):
        assert flt(Path("/"))
        assert flt(Path("/tmp"))
        assert flt(Path("/tmp/"))
        assert flt(Path("/tmp/foo"))
        assert flt(Path("/home/foo"))


def test_path_filters_disallow_excludes_allowed_paths() -> None:
    flt = PathFilters(allow=(re.compile("/.*"),), disallow=(re.compile("/tmp/.*"),))

    with patch("pathlib.Path.resolve", identity):
        assert not flt(Path())  # expected to fail due to disabling resolve
        assert flt(Path("/"))
        assert not flt(Path("/tmp"))
        assert not flt(Path("/tmp/"))
        assert not flt(Path("/tmp/foo"))
        assert flt(Path("/home/foo"))


def test_path_filters_tested_paths_always_end_on_slash() -> None:
    flt = PathFilters(
        allow=(re.compile(r"/home/\w+/.*"),),
        disallow=(re.compile("/home/private/.*"),),
    )

    with patch("pathlib.Path.resolve", identity):
        assert not flt(Path())  # expected to fail due to disabling resolve
        assert not flt(Path("/"))
        assert not flt(Path("/home"))
        assert not flt(Path("/home/"))
        assert flt(Path("/home/public"))
        assert flt(Path("/home/public/"))
        assert flt(Path("/home/public/folder"))
        assert flt(Path("/home/public/folder/"))
        assert not flt(Path("/home/private"))
        assert not flt(Path("/home/private/"))
        assert not flt(Path("/home/private/folder"))
        assert not flt(Path("/home/private/folder/"))


def test_path_filters_resolves_paths(tmp_path: Path) -> None:
    tmp_path = tmp_path.resolve()
    allowed = tmp_path / "allowed"
    flt = PathFilters(allow=(re.compile(f"{allowed}/.*"),))

    assert not flt(allowed / "..")
    assert not flt(tmp_path)
    assert flt(allowed)
    assert flt(allowed / "subdir")
    assert not flt(allowed / "subdir" / ".." / "..")

    allowed.mkdir()
    link = allowed / "link"
    link.symlink_to(tmp_path)
    assert not flt(link)


def test_path_filters_allow_matches_entire_path() -> None:
    with patch("pathlib.Path.resolve", identity):
        flt = PathFilters(allow=(re.compile(r"/tmp"),))
        assert not flt(Path("/tmp"))
        assert not flt(Path("/tmpfoo"))
        assert not flt(Path("/tmp/foo"))
        assert not flt(Path("/root/tmp"))

        flt = PathFilters(allow=(re.compile(r"/tmp/"),))
        assert flt(Path("/tmp"))
        assert not flt(Path("/tmpfoo"))
        assert not flt(Path("/tmp/foo"))
        assert not flt(Path("/root/tmp"))

        flt = PathFilters(allow=(re.compile(r"/tmp/.*"),))
        assert flt(Path("/tmp"))
        assert not flt(Path("/tmpfoo"))
        assert flt(Path("/tmp/foo"))
        assert not flt(Path("/root/tmp"))


def test_path_filters_disallow_matches_beginning_of_path() -> None:
    with patch("pathlib.Path.resolve", identity):
        flt = PathFilters(allow=[re.compile(r"/.*")], disallow=[re.compile("/tmp")])
        assert not flt(Path("/tmp"))
        assert not flt(Path("/tmpfoo"))
        assert not flt(Path("/tmp/foo"))
        assert flt(Path("/root/tmp"))

        flt = PathFilters(allow=[re.compile(r"/.*")], disallow=[re.compile("/tmp/")])
        assert not flt(Path("/tmp"))
        assert flt(Path("/tmpfoo"))
        assert not flt(Path("/tmp/foo"))
        assert flt(Path("/root/tmp"))

        flt = PathFilters(allow=[re.compile(r"/.*")], disallow=[re.compile("/tmp/.*")])
        assert not flt(Path("/tmp"))
        assert flt(Path("/tmpfoo"))
        assert not flt(Path("/tmp/foo"))
        assert flt(Path("/root/tmp"))


def test_path_filters_allows_path_matching_any_allow_pattern() -> None:
    flt = PathFilters(allow=(re.compile(r"/home/\w+/.*"), re.compile(r"/data/\w+/.*")))

    with patch("pathlib.Path.resolve", identity):
        assert flt(Path("/home/foo"))
        assert flt(Path("/data/bar"))
        assert not flt(Path("/home"))
        assert not flt(Path("/etc/baz"))


def test_path_filters_disallows_path_matching_any_disallow_pattern() -> None:
    flt = PathFilters(
        allow=(re.compile(r"/.*"),),
        disallow=(re.compile(r"/etc/.*"), re.compile(r"/root/.*")),
    )

    with patch("pathlib.Path.resolve", identity):
        assert flt(Path("/home/foo"))
        assert not flt(Path("/etc/passwd"))
        assert not flt(Path("/root/secret"))
