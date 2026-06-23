# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Mikkel Schubert
from __future__ import annotations

import os
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path
from typing import Protocol, TypeVar, overload

_T_co = TypeVar("_T_co", covariant=True)


# Based on https://github.com/python/typing/issues/256#issuecomment-1442633430
class SequenceNotStr(Protocol[_T_co]):
    # We only need the sequence to be iterable
    def __iter__(self) -> Iterator[_T_co]: ...
    # This signature does not match `str.__contains__`, preventing use of raw strings
    def __contains__(self, value: object, /) -> bool: ...


@overload
def get_environment_path(key: str, *, default: Path) -> Path: ...


@overload
def get_environment_path(key: str, *, default: Path | None = None) -> Path | None: ...


def get_environment_path(key: str, *, default: Path | None = None) -> Path | None:
    """
    Returns an environment variable as a Path. A default value may be provided, which
    must either be a Path or None. The default value is returned if the environment
    variable is unset or set to an empty string.
    """
    value = os.environ.get(key, None)
    if not value:
        return default

    return Path(value)


def ascii_tree[T](
    items: Sequence[T],
    *,
    inner: bool = False,
) -> Iterable[tuple[str, str, T]]:
    """
    Generates a sequence of ascii characters for drawing one level of an ascii tree. The
    values returned are `(node, to_next, value)`, where `node` represents the current
    node, `to_next` is the character that should be drawn under the current node if the
    tree is extended, and `value` is the value associated with the node.

    This allows an tree of arbitrary depth to be drawn, by prefixing the current line
    with each of the `to_next` values returned from previous levels:

    ```
    for node1, to_next1, value1 in ascii_tree(values1):
        print(node1, value1)
        for node2, to_next2, value2 in ascii_tree(values2, inner=True):
            print(to_next1, node2, value2)
    ```
    """
    if inner:
        single, head, body, tail = "└", "├", "├", "└"
    else:
        single, head, body, tail = "─", "┬", "├", "└"

    last = len(items) - 1
    for index, item in enumerate(items):
        to_next = " "
        if index == 0:
            if index == last:
                node = single
            else:
                node = head
                to_next = "│"
        elif index == last:
            node = tail
        else:
            node = body
            to_next = "│"

        yield node, to_next, item


def value_list[T](values: Sequence[T]) -> str:
    """Format a list of values for pretty-printing: range(3) -> '0, 1, and 2'"""
    last = len(values) - 1
    result: list[str] = []
    for index, value in enumerate(values):
        if index == 0:
            result.append(f"{value!r}")
        elif index == last:
            if index == 1:
                result.append(f" and {value!r}")
            else:
                result.append(f", and {value!r}")
        else:
            result.append(f", {value!r}")

    return "".join(result)
