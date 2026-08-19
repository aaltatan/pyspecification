from collections.abc import Callable
from functools import wraps
from typing import Any, Concatenate, Protocol


class ReturnType(Protocol):
    def __and__(self, value: Any, /) -> Any: ...
    def __or__(self, value: Any, /) -> Any: ...
    def __invert__(self) -> Any: ...


class Predicate[T, R: ReturnType]:
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


def obj_rule[T, R: ReturnType, **P](
    fn: Callable[Concatenate[T, P], R],
) -> Callable[P, Predicate[T, R]]:
    @wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Predicate[T, R]:
        return Predicate(lambda obj: fn(obj, *args, **kwargs))

    return wrapper


def dict_rule[T, K, R: ReturnType, **P](
    fn: Callable[Concatenate[T, K, P], R],
) -> Callable[Concatenate[K, P], Predicate[T, R]]:
    @wraps(fn)
    def wrapper(key: K, *args: P.args, **kwargs: P.kwargs) -> Predicate[T, R]:
        return Predicate(lambda obj: fn(obj, key, *args, **kwargs))

    return wrapper


def sequence_rule[T, R: ReturnType, **P](
    fn: Callable[Concatenate[T, int, P], R],
) -> Callable[Concatenate[int, P], Predicate[T, R]]:
    @wraps(fn)
    def wrapper(idx: int, *args: P.args, **kwargs: P.kwargs) -> Predicate[T, R]:
        return Predicate(lambda obj: fn(obj, idx, *args, **kwargs))

    return wrapper
