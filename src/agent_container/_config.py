# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Mikkel Schubert
from __future__ import annotations

import dataclasses
import logging
import re
from pathlib import Path
from typing import Self

from agent_container._parser import ParseError, parse_toml

__all__ = [
    "Config",
]

LOG = logging.getLogger(__name__)


@dataclasses.dataclass
class Config:
    # Regular expressions describing the paths of allowed workspaces. See `PathFilter`.
    allowed_workspaces: list[re.Pattern[str]] | None = None

    # Regular expressions describing paths should never be allowed. See `PathFilter`.
    disallowed_workspaces: list[re.Pattern[str]] = dataclasses.field(
        default_factory=list[re.Pattern[str]]
    )
    # Optional absolute path to agent singularity container. May be overridden
    container: Path | None = None
    # List of absolute paths to folders that should always be mounted
    includes: list[Path] = dataclasses.field(default_factory=list[Path])

    @classmethod
    def load(cls, global_config: Path, user_config: Path | None = None) -> Self | None:
        """
        Attempts to loads a global configuration and a user configuration. The user
        config is allowed to change the default container file, and to add additional
        includes and disallowed workspace folders. However, the user cannot specify
        allowed workspaces, if the global configuration includes sets this value
        """
        gconfig = cls._load_config(global_config)
        if user_config is not None and (uconfig := cls._load_config(user_config)):
            if gconfig is None:
                return uconfig

            if uconfig.container:
                LOG.debug("using container file specified in '%s'", user_config)
                gconfig.container = uconfig.container

            if uconfig.allowed_workspaces is not None:
                if gconfig.allowed_workspaces is not None:
                    LOG.warning("skipping `allowed_workspaces` in '%s'", user_config)
                else:
                    # this effectively narrows the allowed workspaces
                    gconfig.allowed_workspaces = uconfig.allowed_workspaces

            if uconfig.disallowed_workspaces:
                LOG.debug("adding `disallowed_workspaces` from '%s'", user_config)
                gconfig.disallowed_workspaces.extend(uconfig.disallowed_workspaces)

            if uconfig.includes:
                LOG.debug("adding `includes` from '%s'", user_config)
                gconfig.includes.extend(uconfig.includes)

        return gconfig

    @classmethod
    def _load_config(cls, filename: Path) -> Self | None:
        LOG.debug("loading config file: '%s'", filename)
        try:
            config = parse_toml(cls, filename)
        except FileNotFoundError:
            LOG.debug("config file not found: '%s'", filename)
            return None

        if config.container is not None and not config.container.is_absolute():
            raise ParseError(
                f"relative container path in '{filename}': '{config.container}'"
            )

        for include in config.includes:
            if not include.is_absolute():
                raise ParseError(f"relative include path in '{filename}': '{include}'")

        return config
