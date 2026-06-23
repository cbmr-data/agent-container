# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Mikkel Schubert
from __future__ import annotations

import os
import uuid
from pathlib import Path

from tests.testutils import environment, identity


def _new_value() -> str:
    """Returns a random string usable as an environment variable key or value"""
    return "AC_" + str(uuid.uuid4()).upper().replace("-", "_")


def test_identity_returns_same_object() -> None:
    assert identity(None) is None

    obj = object()
    assert identity(obj) is obj

    number = 123567890
    assert identity(number) is number


def test_environment_replaces_current_value() -> None:
    key = _new_value()
    old_value = _new_value()
    new_value = _new_value()

    assert key not in os.environ

    try:
        os.environ[key] = old_value
        with environment(**{key: new_value}):
            assert os.environ[key] == new_value

        assert os.environ[key] == old_value
    finally:
        os.environ.pop(key, None)


def test_environment_adds_current_value() -> None:
    key = _new_value()
    value = _new_value()

    assert key not in os.environ

    with environment(**{key: value}):
        assert os.environ[key] == value

    assert key not in os.environ


def test_environment_replaces_only_current_value() -> None:
    key = _new_value()
    old_value = _new_value()
    new_value = _new_value()

    assert key not in os.environ

    try:
        os.environ[key] = old_value
        environ = dict(os.environ)

        with environment(**{key: new_value}):
            assert dict(os.environ) == {**environ, key: new_value}

        assert dict(os.environ) == environ
    finally:
        os.environ.pop(key, None)


def test_environment_none_removes_current_value() -> None:
    original_home = os.environ.get("HOME")

    with environment(HOME=None):
        assert "HOME" not in os.environ

    assert os.environ.get("HOME") == original_home


def test_environment_none_has_no_effect_if_key_is_unset() -> None:
    key = _new_value()
    assert os.environ.get(key) is None

    with environment(**{key: None}):
        assert key not in os.environ

    assert key not in os.environ


def test_environment_removes_only_current_value() -> None:
    key = _new_value()
    value = _new_value()

    assert key not in os.environ

    try:
        environ = dict(os.environ)
        os.environ[key] = value

        with environment(**{key: None}):
            assert dict(os.environ) == environ

        assert dict(os.environ) == {**environ, key: value}
    finally:
        os.environ.pop(key, None)


def test_environment_clobbers_subsequent_changes() -> None:
    original_values = dict(os.environ)
    key = _new_value()

    try:
        assert original_values.get(key) != "New Value"
        with environment(**{key: "Tmp Value"}):
            os.environ[key] = "New Value"

        assert dict(os.environ) == original_values
    finally:
        os.environ.clear()
        os.environ.update(original_values)


def test_environment_affects_other_functions() -> None:
    original_home = os.environ.get("HOME")
    new_home = _new_value()

    with environment(HOME=new_home):
        assert Path.home() == Path(new_home)

    assert os.environ.get("HOME") == original_home
