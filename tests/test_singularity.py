from pathlib import Path
from unittest.mock import patch

import pytest

from agent_container._singularity import BindDir, SingularityError, run_singularity


def test_binddir_format_read_only() -> None:
    assert BindDir(Path("/a"), Path("/b")).format(read_only=False) == "/a:/b"
    assert BindDir(Path("/a"), Path("/b")).format(read_only=True) == "/a:/b:ro"


def test_binddir_format_escapes_src() -> None:
    def _format(a: str | Path, b: str | Path) -> str:
        return BindDir(Path(a), Path(b)).format(read_only=False)

    assert _format(Path(), "/foo") == ".:/foo"
    assert _format("/foo/bar", "/foo") == "/foo/bar:/foo"
    assert _format("c:", "/foo") == "c\\::/foo"
    assert _format("a,b,c", "/foo") == "a\\,b\\,c:/foo"
    assert _format("a\\b\\c", "/foo") == "a\\\\b\\\\c:/foo"
    assert _format("\\a,b:c\\", "/foo") == "\\\\a\\,b\\:c\\\\:/foo"


def test_binddir_format_escapes_dst() -> None:
    def _format(a: str | Path, b: str | Path) -> str:
        return BindDir(Path(a), Path(b)).format(read_only=False)

    assert _format("/foo", Path()) == "/foo:."
    assert _format("/foo", "/foo/bar") == "/foo:/foo/bar"
    assert _format("/foo", "c:") == "/foo:c\\:"
    assert _format("/foo", "a,b,c") == "/foo:a\\,b\\,c"
    assert _format("/foo", "a\\b\\c") == "/foo:a\\\\b\\\\c"
    assert _format("/foo", "\\a,b:c\\") == "/foo:\\\\a\\,b\\:c\\\\"


def test_run_singularity_basic_call() -> None:
    with patch("os.execv") as mock:
        run_singularity(
            exe="/path/to/singularity",
            image=Path("/path/to/container.sif"),
            home=Path("/home/sweet/home"),
            cwd=Path("/home/user"),
        )

        mock.assert_called_once_with(
            "/path/to/singularity",
            [
                "/path/to/singularity",
                "run",
                "--containall",
                "--writable-tmpfs",
                "--home",
                "/home/sweet/home:/home/singularity",
                "--pwd",
                "/home/user",
                "--bind",
                "/home/user:/home/user",
                "/path/to/container.sif",
            ],
        )


def test_run_singularity_with_binds() -> None:
    with patch("os.execv") as mock:
        run_singularity(
            exe="/path/to/singularity",
            image=Path("/path/to/container.sif"),
            home=Path("/home/sweet/home"),
            cwd=Path("/home/user"),
            binds=[
                BindDir(Path("/foo"), Path("/bar")),
                BindDir(Path("/tmp"), Path("/tmp")),
            ],
        )

        mock.assert_called_once_with(
            "/path/to/singularity",
            [
                "/path/to/singularity",
                "run",
                "--containall",
                "--writable-tmpfs",
                "--home",
                "/home/sweet/home:/home/singularity",
                "--pwd",
                "/home/user",
                "--bind",
                "/foo:/bar,/home/user:/home/user,/tmp:/tmp",
                "/path/to/container.sif",
            ],
        )


def test_run_singularity_with_read_only_binds() -> None:
    with patch("os.execv") as mock:
        run_singularity(
            exe="/path/to/singularity",
            image=Path("/path/to/container.sif"),
            home=Path("/home/sweet/home"),
            cwd=Path("/home/user"),
            binds=[
                BindDir(Path("/foo"), Path("/bar")),
                BindDir(Path("/tmp"), Path("/tmp")),
            ],
            read_only=True,
        )

        mock.assert_called_once_with(
            "/path/to/singularity",
            [
                "/path/to/singularity",
                "run",
                "--containall",
                "--writable-tmpfs",
                "--home",
                "/home/sweet/home:/home/singularity",
                "--pwd",
                "/home/user",
                "--bind",
                "/foo:/bar:ro,/home/user:/home/user:ro,/tmp:/tmp:ro",
                "/path/to/container.sif",
            ],
        )


def test_run_singularity_with_argv() -> None:
    with patch("os.execv") as mock:
        run_singularity(
            exe="/path/to/singularity",
            image=Path("/path/to/container.sif"),
            home=Path("/home/sweet/home"),
            cwd=Path("/home/user"),
            argv=["claude", "--dangerously-skip-permissions"],
        )

        mock.assert_called_once_with(
            "/path/to/singularity",
            [
                "/path/to/singularity",
                "run",
                "--containall",
                "--writable-tmpfs",
                "--home",
                "/home/sweet/home:/home/singularity",
                "--pwd",
                "/home/user",
                "--bind",
                "/home/user:/home/user",
                "/path/to/container.sif",
                "claude",
                "--dangerously-skip-permissions",
            ],
        )


def test_run_singularity_different_bindings_to_same_destination_not_allowed() -> None:
    with pytest.raises(
        SingularityError,
        match="conflicting bindings at destination '/target'",
    ):
        run_singularity(
            exe="/path/to/singularity",
            image=Path("/path/to/container.sif"),
            home=Path("/home/sweet/home"),
            cwd=Path("/home/user"),
            binds=[
                BindDir(Path("/somewhere"), Path("/target")),
                BindDir(Path("/tmp/foo"), Path("/target")),
            ],
            argv=[],
            read_only=False,
        )


def test_run_singularity_binding_home_singularity_not_allowed() -> None:
    with pytest.raises(
        SingularityError,
        match="cannot bind '/home/singularity': path is reserved",
    ):
        run_singularity(
            exe="/path/to/singularity",
            image=Path("/path/to/container.sif"),
            home=Path("/home/sweet/home"),
            cwd=Path("/home/user"),
            binds=[BindDir(Path("/somewhere"), Path("/home/singularity"))],
            argv=[],
            read_only=False,
        )


def test_run_singularity_rethrows_exec_errors(tmp_path: Path) -> None:
    with pytest.raises(SingularityError, match="failed to run singularity"):
        run_singularity(
            exe=str(tmp_path / "singularity"),
            image=tmp_path / "container.sif",
            home=tmp_path / "home",
            cwd=tmp_path,
            binds=[],
            argv=[],
            read_only=False,
        )
