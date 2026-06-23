# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Mikkel Schubert
import logging
import re
from collections.abc import Iterable
from pathlib import Path

LOG = logging.getLogger(__name__)

__all__ = [
    "PathFilters",
]


class PathFilters:
    """
    Implements filtering of potential workspaces by checking these against an allow-list
    and a disallow-list implemented as regular expressions. If nothing is explicitly
    allowed, then all paths are filtered.

    Path are resolved and a trailing `/` is appended (if not already present)
    before matching. `allow` patterns must match the *entire* path, including any
    trailing `/`. `disallow` patterns need only match the *start* of the path, meaning
    that `/home/private/` excludes that directory and everything below it.

    If no `allow` patterns are configured, no path is allowed.
    """

    def __init__(
        self,
        *,
        allow: Iterable[re.Pattern[str]] = (),
        disallow: Iterable[re.Pattern[str]] = (),
    ) -> None:
        self._allow: tuple[re.Pattern[str], ...] = tuple(allow)
        self._disallow: tuple[re.Pattern[str], ...] = tuple(disallow)

    def __call__(self, path: Path) -> bool:
        r"""
        Returns true if `path` is allowed: it must fully match at least one `allow`
        pattern and must not be excluded by any `disallow` pattern. Patterns are checked
        as described in the class docstring.
        """
        if not self._allow:
            return False

        path_s = str(path.resolve())
        if not path_s.endswith("/"):
            path_s = f"{path_s}/"

        for regex in self._allow:
            LOG.debug("checking path %r against allowed pattern %r", path_s, regex)
            if match := regex.fullmatch(path_s):
                LOG.debug("found match %r", match)
                break
        else:
            return False

        for regex in self._disallow:
            LOG.debug("checking path %r against disallowed pattern %r", path_s, regex)
            if match := regex.match(path_s):
                LOG.debug("found match %r", match)
                return False

        return True
