# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Mikkel Schubert
from __future__ import annotations

import dataclasses
import re
import tomllib
from pathlib import Path
from typing import Any, cast

from koda_validate import (
    CoercionErr,
    DataclassValidator,
    Invalid,
    TypeErr,
    Valid,
    ValidationResult,
    Validator,
)
from koda_validate.serialization import to_serializable_errs
from koda_validate.typehints import get_typehint_validator_base

__all__ = [
    "ParseError",
    "parse",
    "parse_toml",
]


class ParseError(RuntimeError):
    pass


def parse[T](cls: type[T], data: object) -> T:
    validator: Validator[T] = _custom_resolver(cls)
    db = validator(data)

    if not isinstance(db, Valid):
        raise ParseError(f"invalid configuration: {to_serializable_errs(db)}")

    return db.val


def parse_toml[T](cls: type[T], filename: Path) -> T:
    try:
        with filename.open("rb") as fp:
            data = tomllib.load(fp)
    except tomllib.TOMLDecodeError as error:
        raise ParseError(f"error reading TOML file: {error}") from error

    try:
        return parse(cls, data)
    except ParseError as error:
        raise ParseError(f"failed to parse TOML file '{filename}': {error}") from None


def _custom_resolver[T](annotations: type[T]) -> Validator[Any]:
    if annotations == Path:
        return PathValidator()
    elif annotations == re.Pattern[str]:
        return RegexValidator()
    elif dataclasses.is_dataclass(annotations):
        return DataclassValidator(
            annotations,
            fail_on_unknown_keys=True,
            typehint_resolver=_custom_resolver,
        )

    return get_typehint_validator_base(_custom_resolver, annotations)


class RegexValidator(Validator[re.Pattern[str]]):
    def __call__(self, val: object) -> ValidationResult[re.Pattern[str]]:
        if isinstance(val, re.Pattern):
            if isinstance(val.pattern, str):  # pyright: ignore[reportUnknownMemberType]
                return Valid(cast("re.Pattern[str]", val))
        elif isinstance(val, str):
            try:
                return Valid(re.compile(val))
            except re.error:
                return Invalid(CoercionErr({str}, re.Pattern[str]), val, self)

        return Invalid(TypeErr(re.Pattern[str]), val, self)


class PathValidator(Validator[Path]):
    def __call__(self, val: object) -> ValidationResult[Path]:
        if isinstance(val, Path):
            return Valid(val)
        elif isinstance(val, str):
            if not val:
                # An empty string produces Path("."), which is probably not intended
                return Invalid(CoercionErr({str}, Path), val, self)

            return Valid(Path(val))
        else:
            return Invalid(TypeErr(Path), val, self)
