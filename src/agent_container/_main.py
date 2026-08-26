# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Mikkel Schubert
from __future__ import annotations

import logging
import re
import shutil
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Literal

import colorlog

from agent_container._args import AGENT_COMMANDS, SHELL_COMMANDS, LogLevel, parse_args
from agent_container._common import get_environment_path
from agent_container._config import Config
from agent_container._filters import PathFilters
from agent_container._singularity import BindDir, SingularityError, run_singularity
from agent_container._workspaces import WorkspaceError, Workspaces

LOG = logging.getLogger(__name__)


def setup_logging(level: LogLevel) -> None:
    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter("%(log_color)s%(asctime)s %(levelname)s %(message)s")
    )

    logger = colorlog.getLogger()
    logger.setLevel(level)
    logger.addHandler(handler)


def select_container(default_container: Path | None) -> Path | None:
    """Determines the container image to use and validates that the path is valid"""
    user_container = get_environment_path("AGENT_CONTAINER")
    if user_container is not None and not user_container.is_absolute():
        LOG.critical("AGENT_CONTAINER set to relative path: '%s'", user_container)
        return None

    user_container = user_container or default_container
    if user_container is None:
        LOG.critical("no singularity container has been configured")
        return None

    try:
        if not user_container.exists():
            LOG.critical("Singularity image not found: '%s'", user_container)
            return None
        elif not user_container.is_file():
            LOG.critical("Singularity image is not a file: '%s'", user_container)
            return None
    except OSError as error:
        LOG.critical("Could not access singularity container: %s", error)
        return None

    return user_container


def prepare_binds(
    filters: PathFilters,
    includes: Iterable[Path],
) -> list[BindDir] | None:
    any_errors = False
    binds: dict[Path, BindDir] = {}

    for include in includes:
        mode: Literal["ro", "rw"] | None
        for mode in ("ro", "rw"):  # zuban: ignore[assignment]
            flag = f":{mode}"
            if include.name.endswith(flag):
                include = include.parent / include.name.removesuffix(flag)
                break
        else:
            mode = None

        if include != include.resolve():
            # This should not happen; config requires resolved paths and args resolves
            LOG.critical("BUG: unresolved including directory '%s'", include)
            any_errors = True
        elif filters(include):
            bind = BindDir(include, include, mode)
            if binds.setdefault(include, bind) != bind:
                LOG.error("include with conflicting :ro/:rw flags: '%s'", include)
                any_errors = True
            else:
                LOG.debug("including directory '%s'", include)
        else:
            LOG.error("include directory is invalid: '%s'", include)
            any_errors = True

    return None if any_errors else list(binds.values())


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    setup_logging(args.log_level)

    global_config = Path("/etc") / "agent-container.toml"

    try:
        user_config = Path.home() / ".config" / "agent-container.toml"
    except RuntimeError as error:
        LOG.error("Could not resolve user home: %s", error)
        user_config = None

    try:
        # Load the first available config file, if any
        config = Config.load(global_config, user_config)
    except (OSError, RuntimeError) as error:
        LOG.critical("error reading configuration: %s", error)
        return 1

    if config is None:
        # Allow all paths by default, if no limits have been configured
        config = Config(allowed_workspaces=[re.compile("/.*")])
    elif config.allowed_workspaces is None:
        LOG.debug("no allowlist has been configured; defaulting to `/.*`")
        config.allowed_workspaces = [re.compile("/.*")]
    elif not config.allowed_workspaces:
        LOG.critical("allowlist does not permit any workspaces; aborting")
        return 1

    # Certain directories cause failures if mounted
    config.disallowed_workspaces += [re.compile("/$"), re.compile("/home/$")]

    filters = PathFilters(
        allow=config.allowed_workspaces or (),
        disallow=config.disallowed_workspaces,
    )

    agent_storage = get_environment_path(
        "AGENT_CONTAINER_STORAGE",
        default=Path.home() / ".local/share/agent-container",
    )
    if not agent_storage.is_absolute():
        LOG.critical("AGENT_CONTAINER_STORAGE is relative path: '%s'", agent_storage)
        return 1

    try:
        workspaces = Workspaces(storage=agent_storage, filters=filters)
    except WorkspaceError as error:
        LOG.critical("failed to set up workspaces: %s", error)
        return 1

    if args.command == "list":
        for line in workspaces.pretty_list(config.includes):
            print(line)  # noqa: T201

        return 0

    cwd = Path.cwd().resolve()
    if (workspace := workspaces.get(cwd)) is None:
        LOG.error("agent-container cannot be run in the current directory")
        LOG.error("  agent-container must be run in a directory matching")
        if config.allowed_workspaces:
            for root in config.allowed_workspaces:
                LOG.error("    - '%s'", root.pattern)
        if config.disallowed_workspaces:
            LOG.error("  agent-container must NOT be run in a directory matching")
            for root in config.disallowed_workspaces:
                LOG.error("    - '%s'", root.pattern)

        return 1

    if args.command == "new":
        if not workspaces.create(cwd):
            LOG.critical("could not create workspace in current directory")
            return 1

        return 0

    for executable in ("apptainer", "singularity"):
        if singularity := shutil.which(executable):
            LOG.debug("running containers using '%s'", singularity)
            break
    else:
        LOG.critical("neither `apptainer` nor `singularity` not found on PATH")
        return 1

    if (container := select_container(config.container)) is None:
        return 1

    if (binds := prepare_binds(filters, [*config.includes, *args.include])) is None:
        return 1

    if args.command == "shell":
        args.command = "bash"

    LOG.info("starting %s container in '%s'", args.command, cwd)

    if args.command not in SHELL_COMMANDS and args.command not in AGENT_COMMANDS:
        raise NotImplementedError(f"unexpected command {args.command!r}")

    # storage must be created before running singularity
    (agent_storage / workspace.key).mkdir(mode=0o700, exist_ok=True)

    try:
        run_singularity(
            exe=singularity,
            image=container,
            home=agent_storage / workspace.key,
            cwd=cwd,
            binds=binds,
            read_only=args.read_only,
            argv=[args.command, *args.arguments],
        )
    except SingularityError as error:
        LOG.critical("error running singularity: %s", error)
        return 1

    return 0
