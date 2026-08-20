from collections.abc import Callable
from typing import Any, Protocol


class ReturnType(Protocol):
    def __and__(self, value: Any, /) -> Any: ...
    def __or__(self, value: Any, /) -> Any: ...
    def __invert__(self) -> Any: ...


class Predicate[T, R: ReturnType]:
    """A predicate is a function that takes an object of type `T` and returns a boolean value.

    Attributes:
        fn: The function that implements the predicate.

    """

    def __init__(self, fn: Callable[[T], R]) -> None:
        self._fn = fn

    def __call__(self, obj: T) -> R:
        return self._fn(obj)

    def __and__(self, other: "Predicate[T, R]") -> "Predicate[T, R]":
        return Predicate(lambda obj: self(obj) and other(obj))

    def __or__(self, other: "Predicate[T, R]") -> "Predicate[T, R]":
        return Predicate(lambda obj: self(obj) or other(obj))

    def __invert__(self) -> "Predicate[T, R]":
        return Predicate(lambda obj: not self(obj)) # type: ignore  # noqa: PGH003
