# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Mikkel Schubert
from __future__ import annotations

import itertools
import logging
import re
import unittest.mock
from pathlib import Path
from unittest.mock import patch

import pytest

from agent_container._filters import PathFilters
from agent_container._workspaces import Workspace, WorkspaceError, Workspaces
from tests.testutils import identity

_with_and_without_reload = pytest.mark.parametrize("reload", [True, False])

ALLOW_EVERYTHING = PathFilters(allow=[re.compile("/.*")])


def test_workspaces_creates_storage_folder(tmp_path: Path) -> None:
    storage = tmp_path / "storage"
    assert not storage.exists()
    wss = Workspaces(storage=storage, filters=PathFilters())
    assert list(wss) == []
    assert storage.is_dir()
    assert storage.lstat().st_mode & 0o777 == 0o700


def test_workspaces_limits_permissions_on_storage_folder(tmp_path: Path) -> None:
    storage = tmp_path / "storage"
    storage.mkdir()
    storage.chmod(0o777)
    wss = Workspaces(storage=storage, filters=PathFilters())
    assert list(wss) == []
    assert storage.lstat().st_mode & 0o777 == 0o700


def test_workspaces_initializes_throws_on_error(tmp_path: Path) -> None:
    storage = tmp_path / "storage"
    with unittest.mock.patch("pathlib.Path.mkdir") as mock:
        mock.side_effect = OSError("dummy value")

        with pytest.raises(
            WorkspaceError,
            match=f"Could not create storage folder '{storage}': dummy value",
        ):
            Workspaces(storage=storage, filters=PathFilters())

    with unittest.mock.patch("pathlib.Path.chmod") as mock:
        mock.side_effect = OSError("dummy value")

        with pytest.raises(
            WorkspaceError,
            match=f"Could not set permissions for storage folder '{storage}': "
            "dummy value",
        ):
            Workspaces(storage=storage, filters=PathFilters())


def test_workspaces_load_workspaces(tmp_path: Path) -> None:
    storage = tmp_path / "storage"
    storage.mkdir()

    (storage / "test.toml").write_text(
        f"""path = "{tmp_path / "data"}"
        """
    )

    wss = Workspaces(storage=storage, filters=ALLOW_EVERYTHING)
    assert list(wss) == [Workspace(key="test", path=tmp_path / "data")]


@pytest.mark.parametrize("ext", ["", ".txt"])
def test_workspaces_load_skips_unknown_extensions(ext: str, tmp_path: Path) -> None:
    storage = tmp_path / "storage"
    storage.mkdir()

    (storage / f"test{ext}").write_text(
        f"""path = "{tmp_path / "data"}"
        """
    )

    wss = Workspaces(storage=storage, filters=ALLOW_EVERYTHING)
    assert list(wss) == []


def test_workspaces_load_skips_non_files(tmp_path: Path) -> None:
    storage = tmp_path / "storage"
    (storage / "test.toml").mkdir(parents=True)

    wss = Workspaces(storage=storage, filters=ALLOW_EVERYTHING)
    assert list(wss) == []


def test_workspaces_load_logs_error_invalid_toml(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    toml = tmp_path / "test.toml"
    toml.write_text("path = 1")

    with caplog.at_level(logging.ERROR):
        ws = Workspaces(storage=tmp_path, filters=ALLOW_EVERYTHING)

    assert list(ws) == []
    assert f"skipping invalid workspace file '{toml}'" in caplog.text


def test_workspaces_list_workspaces_skips_global(tmp_path: Path) -> None:
    storage = tmp_path / "storage"
    storage.mkdir()

    (storage / "global.toml").write_text(
        f"""path = "{tmp_path / "data"}"
        """
    )

    wss = Workspaces(storage=storage, filters=ALLOW_EVERYTHING)
    assert list(wss) == []


def test_workspaces_load_workspaces_skips_disallowed_paths(tmp_path: Path) -> None:
    with patch("pathlib.Path.resolve", identity):
        (tmp_path / "test.toml").write_text('path = "/tmp/data"\n')

        wss = Workspaces(
            storage=tmp_path,
            filters=PathFilters(
                allow=[re.compile("/.*")],
                disallow=[re.compile("/tmp/.*")],
            ),
        )
        assert list(wss) == []


def test_workspaces_get_default_workspace(tmp_path: Path) -> None:
    with patch("pathlib.Path.resolve", identity):
        wss = Workspaces(storage=tmp_path, filters=ALLOW_EVERYTHING)

        assert wss.get(Path("/")) == Workspace("global", Path())
        assert wss.get(Path("/tmp")) == Workspace("global", Path())
        assert wss.get(Path("/home/foo")) == Workspace("global", Path())


def test_workspaces_get_default_workspace_with_disallows(tmp_path: Path) -> None:
    with patch("pathlib.Path.resolve", identity):
        wss = Workspaces(
            storage=tmp_path,
            filters=PathFilters(
                allow=[re.compile("/.*")],
                disallow=[re.compile("/tmp/.*")],
            ),
        )

        assert wss.get(Path("/")) == Workspace("global", Path())
        assert wss.get(Path("/tmp")) is None
        assert wss.get(Path("/home/foo")) == Workspace("global", Path())


@_with_and_without_reload
def test_workspaces_create_workspace(*, reload: bool, tmp_path: Path) -> None:
    with patch("pathlib.Path.resolve", identity):
        wss = Workspaces(storage=tmp_path, filters=ALLOW_EVERYTHING)

        with unittest.mock.patch(
            "agent_container._workspaces.Workspaces._hash_path"
        ) as mock:
            mock.return_value = "random-value"
            ws = wss.create(Path("/home/foo"))
            assert ws == Workspace(key="random-value", path=Path("/home/foo"))

        if reload:
            wss = Workspaces(storage=tmp_path, filters=ALLOW_EVERYTHING)
        assert wss.get(Path("/tmp")) == Workspace("global", Path())
        assert wss.get(Path("/home")) == Workspace("global", Path())
        assert wss.get(Path("/home/bar")) == Workspace("global", Path())
        assert wss.get(Path("/home/foo")) == ws
        assert wss.get(Path("/home/foo/bar")) == ws


def test_workspaces_disallows_overwriting_config(
    *, caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    with patch("pathlib.Path.resolve", identity):
        wss = Workspaces(storage=tmp_path, filters=ALLOW_EVERYTHING)
        with unittest.mock.patch(
            "agent_container._workspaces.Workspaces._hash_path"
        ) as mock:
            mock.return_value = "random-value"
            wss.create(Path("/home/foo"))

            mock.assert_called_once_with(Path("/home/foo"))

        wss = Workspaces(storage=tmp_path, filters=ALLOW_EVERYTHING)
        with unittest.mock.patch(
            "agent_container._workspaces.Workspaces._hash_path"
        ) as mock:
            mock.return_value = "random-value"

            with caplog.at_level(logging.ERROR):
                wss.create(Path("/home/bar"))
                mock.assert_called_once_with(Path("/home/bar"))
                assert "error saving workspace as 'random-value'" in caplog.text


@_with_and_without_reload
def test_workspaces_create_duplicate_workspace(*, reload: bool, tmp_path: Path) -> None:
    with patch("pathlib.Path.resolve", identity):
        wss = Workspaces(storage=tmp_path, filters=ALLOW_EVERYTHING)
        ws = wss.create(Path("/home/foo"))
        assert ws is not None

        if reload:
            wss = Workspaces(storage=tmp_path, filters=ALLOW_EVERYTHING)
        assert wss.create(Path("/home/foo")) == ws


@_with_and_without_reload
def test_workspaces_create_warns_on_already_existing_workspace(
    *, reload: bool, caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    with patch("pathlib.Path.resolve", identity):
        wss = Workspaces(storage=tmp_path, filters=ALLOW_EVERYTHING)
        ws = wss.create(Path("/home/foo"))
        assert ws is not None

        if reload:
            wss = Workspaces(storage=tmp_path, filters=ALLOW_EVERYTHING)

        with caplog.at_level(logging.WARNING):
            assert wss.create(Path("/home/foo")) == ws
            assert "workspace already exists for '/home/foo'" in caplog.text


@_with_and_without_reload
def test_workspaces_create_workspace_with_disallow(
    *, reload: bool, tmp_path: Path
) -> None:
    with patch("pathlib.Path.resolve", identity):
        filters = PathFilters(
            allow=[re.compile("/.*")],
            disallow=[re.compile("/tmp/.*")],
        )

        wss = Workspaces(storage=tmp_path, filters=filters)

        with unittest.mock.patch(
            "agent_container._workspaces.Workspaces._hash_path"
        ) as mock:
            mock.side_effect = ["random-value"]
            ws = wss.create(Path("/home/foo"))
            assert ws == Workspace(key="random-value", path=Path("/home/foo"))
            assert wss.create(Path("/tmp/foo")) is None

        if reload:
            wss = Workspaces(storage=tmp_path, filters=filters)
        assert wss.get(Path("/tmp")) is None
        assert wss.get(Path("/tmp/foo")) is None
        assert wss.get(Path("/home")) == Workspace("global", Path())
        assert wss.get(Path("/home/bar")) == Workspace("global", Path())
        assert wss.get(Path("/home/foo")) == ws
        assert wss.get(Path("/home/foo/bar")) == ws


_PATH_PERMUTATIONS = tuple(
    itertools.permutations(
        (Path("/tmp"), Path("/tmp/foo"), Path("/tmp/foo/bar/zed")), r=3
    )
)


@_with_and_without_reload
@pytest.mark.parametrize(("path_a", "path_b", "path_c"), _PATH_PERMUTATIONS)
def test_workspaces_get_workspace_always_returns_longest_match(
    *, reload: bool, path_a: Path, path_b: Path, path_c: Path, tmp_path: Path
) -> None:
    with patch("pathlib.Path.resolve", identity):
        wss = Workspaces(storage=tmp_path, filters=ALLOW_EVERYTHING)

        paths: dict[Path, Workspace] = {}
        for path in (path_a, path_b, path_c):
            ws = wss.create(path)
            assert ws is not None
            paths[ws.path] = ws

        if reload:
            wss = Workspaces(storage=tmp_path, filters=ALLOW_EVERYTHING)

        assert wss.get(Path("/tmp")) == paths[Path("/tmp")]
        assert wss.get(Path("/tmp/foo")) == paths[Path("/tmp/foo")]
        assert wss.get(Path("/tmp/foo/bar")) == paths[Path("/tmp/foo")]
        assert wss.get(Path("/tmp/foo/bar/xyz")) == paths[Path("/tmp/foo")]
        assert wss.get(Path("/tmp/foo/bar/zed")) == paths[Path("/tmp/foo/bar/zed")]
        assert wss.get(Path("/tmp/foo/bar/zed/nth")) == paths[Path("/tmp/foo/bar/zed")]


def test_workspaces_load_resolves_path(tmp_path: Path) -> None:
    wss = Workspaces(storage=tmp_path / "storage", filters=ALLOW_EVERYTHING)

    (tmp_path / "ws").mkdir()
    ws1 = wss.create(tmp_path / "ws")
    assert ws1 is not None
    assert ws1.path == tmp_path / "ws"

    (tmp_path / "ws").rename(tmp_path / "renamed")
    (tmp_path / "ws").symlink_to(tmp_path / "renamed")

    wss = Workspaces(storage=tmp_path / "storage", filters=ALLOW_EVERYTHING)
    ws2 = wss.get(tmp_path / "ws")
    assert ws2 is not None
    assert ws2.path == tmp_path / "renamed"
    assert ws1.key == ws2.key


def test_workspaces_create_resolves_path(tmp_path: Path) -> None:
    (tmp_path / "link").symlink_to(tmp_path / "actual")
    wss = Workspaces(storage=tmp_path / "storage", filters=ALLOW_EVERYTHING)
    ws = wss.create(tmp_path / "link")
    assert ws is not None
    assert ws.path == tmp_path / "actual"


@_with_and_without_reload
def test_workspaces_get_resolves_path(*, reload: bool, tmp_path: Path) -> None:
    wss = Workspaces(storage=tmp_path / "storage", filters=ALLOW_EVERYTHING)
    ws = wss.create(tmp_path / "actual")
    assert ws is not None

    (tmp_path / "link").symlink_to(tmp_path / "actual")

    if reload:
        wss = Workspaces(storage=tmp_path / "storage", filters=ALLOW_EVERYTHING)

    assert wss.get(tmp_path) == Workspace(key="global", path=Path())
    assert wss.get(tmp_path / "actual") == ws
    assert wss.get(tmp_path / "link") == ws


def test_workspaces_list_for_no_workspaces(tmp_path: Path) -> None:
    wss = Workspaces(storage=tmp_path, filters=PathFilters())
    assert list(wss.pretty_list()) == [
        "No workspaces configured; always using global configuration"
    ]


def test_workspaces_list_for_single_workspace(tmp_path: Path) -> None:
    with patch("pathlib.Path.resolve", identity):
        wss = Workspaces(storage=tmp_path, filters=ALLOW_EVERYTHING)
        ws = wss.create(Path("/home/foo"))
        assert ws is not None

        assert list(wss.pretty_list()) == [
            "─ /home/foo",
            "    └ No paths included",
        ]

        assert list(wss.pretty_list([Path("/tmp"), Path("/data/foo")])) == [
            "─ /home/foo",
            "    └ Includes:",
            "        ├ /data/foo",
            "        └ /tmp",
        ]


def test_workspaces_list_for_two_workspace(tmp_path: Path) -> None:
    with patch("pathlib.Path.resolve", identity):
        wss = Workspaces(storage=tmp_path, filters=ALLOW_EVERYTHING)
        ws = wss.create(Path("/home/foo"))
        ws = wss.create(Path("/etc"))
        assert ws is not None

        assert list(wss.pretty_list()) == [
            "─┬ /etc",
            " │   └ No paths included",
            " └ /home/foo",
            "     └ No paths included",
        ]

        assert list(wss.pretty_list([Path("/tmp"), Path("/data/foo")])) == [
            "─┬ /etc",
            " │   └ Includes:",
            " │       ├ /data/foo",
            " │       └ /tmp",
            " └ /home/foo",
            "     └ Includes:",
            "         ├ /data/foo",
            "         └ /tmp",
        ]
