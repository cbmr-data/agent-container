# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Mikkel Schubert
from __future__ import annotations

import contextlib
import os
from collections.abc import Generator


def identity[T](value: T) -> T:
    """Identity function. Used to monkey-patch functions that touch the filesystem"""
    return value


@contextlib.contextmanager
def environment(**kwargs: str | None) -> Generator[None]:
    """
    Temporarily modifies environment variables for the duration of the context. Setting
    a variable to a string sets this value, while setting a variable to None unsets the
    variable if it was set. These changes, and any subsequent changes to the specified
    environment variables, are reverted once the context is exited
    """
    original_values: dict[str, str | None] = {
        key: os.environ.get(key) for key in kwargs
    }

    def _update_environ(values: dict[str, str | None]) -> None:
        for key, value in values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    try:
        _update_environ(kwargs)

        yield None
    finally:
        _update_environ(original_values)
