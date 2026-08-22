# ruff: noqa: PGH003

from collections.abc import Callable
from typing import Any, Protocol


class ReturnType(Protocol):
    def __and__(self, value: Any, /) -> Any: ...
    def __or__(self, value: Any, /) -> Any: ...
    def __invert__(self) -> Any: ...


class Predicate[T, R: ReturnType]:
    def __init__(self, fn: Callable[[T], R], description: str | None = None) -> None:
        self._fn = fn
        self._description = description

    def __call__(self, obj: T) -> R:
        return self._fn(obj)

    def __and__(self, other: "Predicate[T, R]") -> "Predicate[T, R]":
        return Predicate(lambda obj: self(obj) and other(obj), f"({self} & {other})")

    def __or__(self, other: "Predicate[T, R]") -> "Predicate[T, R]":
        return Predicate(lambda obj: self(obj) or other(obj), f"({self} | {other})")

    def __invert__(self) -> "Predicate[T, R]":
        return Predicate(lambda obj: not self(obj), f"~{self}")  # type: ignore

    def __str__(self) -> str:
        return self._description or self._fn.__name__ or "Predicate"

    def __repr__(self) -> str:
        return f"Predicate({self})"
