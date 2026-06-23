# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Mikkel Schubert
from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from agent_container._common import ascii_tree
from agent_container._filters import PathFilters
from agent_container._parser import ParseError, parse_toml

LOG = logging.getLogger(__name__)

_DEFAULT_WORKSPACE = "global"


class WorkspaceError(RuntimeError):
    pass


@dataclass
class _WorkspaceConfig:
    path: Path  # absolute path


class Workspace(NamedTuple):
    key: str  # unique key used as stem for toml file; `global` is reserved
    path: Path  # absolute path


class Workspaces:
    def __init__(self, *, storage: Path, filters: PathFilters) -> None:
        self._filters: PathFilters = filters
        self._storage: Path = storage

        self._initialize(self._storage)
        self._workspaces: list[Workspace] = self._collect(self._storage, filters)

        self._default: Workspace = Workspace(
            path=Path(),
            key=_DEFAULT_WORKSPACE,
        )

    def get(self, path: Path) -> Workspace | None:
        path = path.resolve()
        if not self._filters(path):
            return None

        LOG.debug("identifying workspace for '%s'", path)

        longest_path = Path("/")
        longest_ws = self._default
        for ws in self._workspaces:
            LOG.debug("checking against workspace '%s'", ws.path)
            if ws.path == path or (
                path.is_relative_to(ws.path) and ws.path.is_relative_to(longest_path)
            ):
                LOG.debug("found match")
                longest_path = ws.path
                longest_ws = ws

        return longest_ws

    def create(self, path: Path) -> Workspace | None:
        path = path.resolve()
        if not self._filters(path):
            return None

        workspace = self.get(path)
        if workspace is not None and workspace.path == path:
            LOG.warning("workspace already exists for '%s'; skipping", path)
            return workspace

        workspace = Workspace(path=path, key=self._hash_path(path))

        try:
            self._save_workspace(self._storage, workspace, overwrite=False)
        except OSError as error:
            LOG.error("error saving workspace as '%s': %s", workspace.key, error)
            return None

        self._workspaces.append(workspace)

        LOG.info("workspace configured in '%s'", path)
        return workspace

    def pretty_list(self, default_includes: Sequence[Path] = ()) -> Iterable[str]:
        workspaces = sorted(self._workspaces, key=lambda it: it.path)
        if workspaces:
            first = "─" if len(workspaces) > 1 else ""
            for node, to_next, ws in ascii_tree(workspaces):
                yield f"{first}{node} {ws.path}"
                first = " " if first else ""
                if default_includes:
                    yield f"{first}{to_next}   └ Includes:"

                    includes = sorted(default_includes)
                    for node, _, include in ascii_tree(includes, inner=True):
                        yield f"{first}{to_next}       {node} {include}"
                else:
                    yield f"{first}{to_next}   └ No paths included"

        else:
            yield "No workspaces configured; always using global configuration"

    def __iter__(self) -> Iterator[Workspace]:
        return iter(self._workspaces)

    @classmethod
    def _save_workspace(
        cls,
        storage: Path,
        workspace: Workspace,
        *,
        overwrite: bool,
    ) -> None:
        path = json.dumps(str(workspace.path))
        config = [
            f"path = {path}\n",
        ]

        mode = "w" if overwrite else "x"
        with (storage / f"{workspace.key}.toml").open(mode) as handle:
            handle.writelines(config)

    @classmethod
    def _collect(cls, storage: Path, filters: PathFilters) -> list[Workspace]:
        workspaces: list[Workspace] = []
        for it in storage.iterdir():
            if it.is_file() and it.suffix == ".toml":
                if it.stem == _DEFAULT_WORKSPACE:
                    LOG.warning("config file '%s' skipped", it)
                    continue

                LOG.debug("loading workspace config file '%s'", it)
                try:
                    workspace = parse_toml(_WorkspaceConfig, it)
                except ParseError as error:
                    LOG.error("skipping invalid workspace file '%s': %s ", it, error)
                    continue

                resolved = workspace.path.resolve()
                if workspace.path != resolved:
                    LOG.warning("workspace '%s' has moved to '%s'", it, resolved)
                    workspace.path = resolved

                if not filters(workspace.path):
                    LOG.warning("Invalid workspace '%s': %s", it, workspace.path)
                    continue

                workspaces.append(
                    Workspace(
                        path=workspace.path,
                        key=it.stem,
                    )
                )

        return workspaces

    @classmethod
    def _initialize(cls, root: Path) -> None:
        try:
            root.parent.mkdir(parents=True, exist_ok=True)
            root.mkdir(exist_ok=True, mode=0o700)
        except OSError as error:
            raise WorkspaceError(
                f"Could not create storage folder '{root}': {error}"
            ) from error

        try:
            # Enforce limited access to directory, since it will contain secrets, etc.
            root.chmod(0o700)
        except OSError as error:
            raise WorkspaceError(
                f"Could not set permissions for storage folder '{root}': {error}"
            ) from error

    @classmethod
    def _hash_path(cls, path: Path) -> str:
        hasher = hashlib.sha256()
        hasher.update(bytes(path))

        return hasher.hexdigest()
