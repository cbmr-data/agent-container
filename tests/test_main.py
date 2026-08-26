# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Mikkel Schubert
from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import pytest

from agent_container._filters import PathFilters
from agent_container._main import prepare_binds
from agent_container._singularity import BindDir

DEFAULT_FILTER = PathFilters(allow=[re.compile(".*")])


def test_prepare_binds_with_no_binds_and_no_filters() -> None:
    assert prepare_binds(DEFAULT_FILTER, []) == []


def test_prepare_binds_checks_that_paths_are_not_relative(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    assert prepare_binds(DEFAULT_FILTER, [Path("foo")]) is None
    assert "BUG: unresolved including directory 'foo'" in caplog.text


def test_prepare_binds_checks_that_paths_are_normalized(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    assert prepare_binds(DEFAULT_FILTER, [tmp_path / "foo" / ".." / "bar"]) is None
    assert f"BUG: unresolved including directory '{tmp_path}/foo/../bar'" in caplog.text


def test_prepare_binds_resolves_symlinks(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    (tmp_path / "bar").symlink_to(tmp_path / "foo")
    assert prepare_binds(DEFAULT_FILTER, [tmp_path / "bar"]) is None
    assert f"BUG: unresolved including directory '{tmp_path}/bar'" in caplog.text


def test_prepare_binds_accepts_resolved_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert prepare_binds(DEFAULT_FILTER, [tmp_path / "foo"]) == [
        BindDir(tmp_path / "foo", tmp_path / "foo", None)
    ]


def test_prepare_binds_filters_paths(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    filters = PathFilters(allow=[re.compile(".*/foo/")])

    assert prepare_binds(filters, [tmp_path / "foo"]) == [
        BindDir(tmp_path / "foo", tmp_path / "foo", None)
    ]
    assert f"include directory is invalid: '{tmp_path / 'foo'}'" not in caplog.text

    assert prepare_binds(filters, [tmp_path / "bar"]) is None
    assert f"include directory is invalid: '{tmp_path / 'bar'}'" in caplog.text


@pytest.mark.parametrize(
    ("filename", "mode"),
    [
        ("foo", None),
        ("foo/", None),
        ("foo:ro", "ro"),
        ("foo/:ro", "ro"),
        ("foo:rw", "rw"),
        ("foo/:rw", "rw"),
    ],
)
def test_prepare_binds_ro_and_rw_indicates_write_permissions(
    *,
    filename: str,
    mode: Literal["ro", "rw"] | None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    assert prepare_binds(DEFAULT_FILTER, [tmp_path / filename]) == [
        BindDir(tmp_path / "foo", tmp_path / "foo", mode=mode)
    ]


@pytest.mark.parametrize("filename", ["foo:RO", "foo:RW", "foo:foo", "foo:"])
def test_prepare_binds_only_ro_and_rw_indicates_write_permissions(
    *,
    filename: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    filepath = tmp_path / filename

    assert prepare_binds(DEFAULT_FILTER, [filepath]) == [
        BindDir(filepath, filepath, mode=None)
    ]


def test_prepare_binds_only_the_last_flag_is_used(
    *,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    assert prepare_binds(DEFAULT_FILTER, [tmp_path / "name:foo:rw"]) == [
        BindDir(tmp_path / "name:foo", tmp_path / "name:foo", mode="rw")
    ]
    assert prepare_binds(DEFAULT_FILTER, [tmp_path / "name:rw:ro"]) == [
        BindDir(tmp_path / "name:rw", tmp_path / "name:rw", mode="ro")
    ]
    assert prepare_binds(DEFAULT_FILTER, [tmp_path / "name:ro:ro"]) == [
        BindDir(tmp_path / "name:ro", tmp_path / "name:ro", mode="ro")
    ]


def test_prepare_binds_returns_none_if_any_paths_fail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    path_1 = tmp_path / "1"
    path_2 = tmp_path / "2"
    path_3 = tmp_path / "../3"

    assert prepare_binds(DEFAULT_FILTER, [path_1]) is not None
    assert prepare_binds(DEFAULT_FILTER, [path_2]) is not None
    assert prepare_binds(DEFAULT_FILTER, [path_1, path_2]) is not None

    assert prepare_binds(DEFAULT_FILTER, [path_3]) is None
    assert prepare_binds(DEFAULT_FILTER, [path_1, path_3]) is None
    assert prepare_binds(DEFAULT_FILTER, [path_3, path_1]) is None
    assert prepare_binds(DEFAULT_FILTER, [path_2, path_3]) is None
    assert prepare_binds(DEFAULT_FILTER, [path_3, path_2]) is None
    assert prepare_binds(DEFAULT_FILTER, [path_1, path_2, path_3]) is None
    assert prepare_binds(DEFAULT_FILTER, [path_1, path_3, path_2]) is None
    assert prepare_binds(DEFAULT_FILTER, [path_3, path_1, path_2]) is None


def test_prepare_binds_ignores_exact_duplicate_entries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    path_1 = tmp_path / "1"
    path_2 = tmp_path / "2:ro"
    path_3 = tmp_path / "3:rw"
    arguments = [path_1, path_2, path_1, path_3, path_2, path_3]

    assert prepare_binds(DEFAULT_FILTER, arguments) == [
        BindDir(tmp_path / "1", tmp_path / "1", mode=None),
        BindDir(tmp_path / "2", tmp_path / "2", mode="ro"),
        BindDir(tmp_path / "3", tmp_path / "3", mode="rw"),
    ]


def test_prepare_binds_rejects_conflicting_flags(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    path_1 = tmp_path / "1"
    path_2 = tmp_path / "1:ro"
    path_3 = tmp_path / "1:rw"

    assert prepare_binds(DEFAULT_FILTER, [path_1, path_1]) is not None

    assert prepare_binds(DEFAULT_FILTER, [path_1, path_2]) is None
    assert f"include with conflicting :ro/:rw flags: '{tmp_path / '1'}" in caplog.text

    caplog.clear()
    assert prepare_binds(DEFAULT_FILTER, [path_1, path_2]) is None
    assert f"include with conflicting :ro/:rw flags: '{tmp_path / '1'}" in caplog.text

    caplog.clear()
    assert prepare_binds(DEFAULT_FILTER, [path_2, path_3]) is None
    assert f"include with conflicting :ro/:rw flags: '{tmp_path / '1'}" in caplog.text
