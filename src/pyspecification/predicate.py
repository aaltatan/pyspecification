from collections.abc import Callable
from typing import Any, Protocol


class PredicateResult(Protocol):
    def __and__(self, value: Any, /) -> Any: ...
    def __or__(self, value: Any, /) -> Any: ...
    def __invert__(self) -> Any: ...


class Predicate[T, R: PredicateResult]:
    def __init__(self, fn: Callable[[T], R]) -> None:
        self._fn = fn

    def __call__(self, obj: T) -> R:
        return self._fn(obj)

    def __and__(self, other: "Predicate[T, R]") -> "Predicate[T, R]":
        return Predicate(lambda obj: self(obj) & other(obj))

    def __or__(self, other: "Predicate[T, R]") -> "Predicate[T, R]":
        return Predicate(lambda obj: self(obj) | other(obj))

    def __invert__(self) -> "Predicate[T, R]":
        return Predicate(lambda obj: ~self(obj))
