# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Mikkel Schubert
from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from agent_container._common import ascii_tree, get_environment_path, value_list
from tests.testutils import environment


@pytest.mark.parametrize("value", [None, ""])
def test_get_environment_path_with_key_not_set(value: None | str) -> None:
    key = str(uuid.uuid4())
    with environment(**{key: value}):
        assert get_environment_path(key) is None
        assert get_environment_path(key, default=None) is None
        assert get_environment_path(key, default=Path("/foo/bar")) == Path("/foo/bar")


def test_get_environment_path_with_key_set() -> None:
    key = str(uuid.uuid4())
    with environment(**{key: "/some/path"}):
        assert get_environment_path(key) == Path("/some/path")
        assert get_environment_path(key, default=None) == Path("/some/path")
        assert get_environment_path(key, default=Path("/foo/bar")) == Path("/some/path")


def test_ascii_tree() -> None:
    assert list(ascii_tree(())) == []

    assert list(ascii_tree(range(1))) == [
        ("─", " ", 0),
    ]

    assert list(ascii_tree(range(2))) == [
        ("┬", "│", 0),
        ("└", " ", 1),
    ]

    assert list(ascii_tree(range(3))) == [
        ("┬", "│", 0),
        ("├", "│", 1),
        ("└", " ", 2),
    ]

    assert list(ascii_tree(range(4))) == [
        ("┬", "│", 0),
        ("├", "│", 1),
        ("├", "│", 2),
        ("└", " ", 3),
    ]


def test_ascii_tree_inner_list() -> None:
    assert list(ascii_tree((), inner=True)) == []

    assert list(ascii_tree(range(1), inner=True)) == [
        ("└", " ", 0),
    ]

    assert list(ascii_tree(range(2), inner=True)) == [
        ("├", "│", 0),
        ("└", " ", 1),
    ]

    assert list(ascii_tree(range(3), inner=True)) == [
        ("├", "│", 0),
        ("├", "│", 1),
        ("└", " ", 2),
    ]

    assert list(ascii_tree(range(4), inner=True)) == [
        ("├", "│", 0),
        ("├", "│", 1),
        ("├", "│", 2),
        ("└", " ", 3),
    ]


def test_ascii_tree_identifies_first_and_last_by_position() -> None:
    # First/last detection should not depend on the identity of the values
    # This is tested using `range(300, 304)`, where `x[0] is x[0] == False`
    assert list(ascii_tree(range(300, 304))) == [
        ("┬", "│", 300),
        ("├", "│", 301),
        ("├", "│", 302),
        ("└", " ", 303),
    ]


def test_ascii_tree_with_duplicate_elements() -> None:
    obj = object()
    assert list(ascii_tree([obj, obj, obj])) == [
        ("┬", "│", obj),
        ("├", "│", obj),
        ("└", " ", obj),
    ]


def test_value_list() -> None:
    assert value_list(()) == ""
    assert value_list(("a",)) == "'a'"
    assert value_list(("a", "b")) == "'a' and 'b'"
    assert value_list(("a", "b", "c")) == "'a', 'b', and 'c'"
    assert value_list(("a", "b", "c", "d")) == "'a', 'b', 'c', and 'd'"

    assert value_list(range(0)) == ""
    assert value_list(range(1)) == "0"
    assert value_list(range(2)) == "0 and 1"
    assert value_list(range(3)) == "0, 1, and 2"
    assert value_list(range(4)) == "0, 1, 2, and 3"
