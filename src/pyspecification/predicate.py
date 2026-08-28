# ruff: noqa: PGH003

from collections.abc import Callable
from typing import Any, Protocol


class ReturnType(Protocol):
    def __and__(self, value: Any, /) -> Any: ...
    def __or__(self, value: Any, /) -> Any: ...
    def __invert__(self) -> Any: ...


class Predicate[T, R: ReturnType]:
    """A predicate is a function that takes an object of type T and returns a value of type R.

    Args:
        fn (Callable[[T], R]): The function to wrap.
        description (str, optional): A description of the predicate. Defaults to None.

    Example:
    ```python
    from pyspecification import Predicate


    def is_admin(user: User) -> bool:
        return user.is_admin


    def name__istartswith(user: User, value: str) -> bool:
        return user.name.lower().startswith(value.lower())


    def age__between(user: User, min_age: int, max_age: int) -> bool:
        return user.age >= min_age and user.age <= max_age


    is_admin: Predicate[User, bool] = Predicate(is_admin)
    name__istartswith: Predicate[User, bool] = Predicate(name__istartswith)
    age__between: Predicate[User, bool] = Predicate(age__between)


    rule = is_admin | (name__istartswith("admin") & age__between(18, 30))


    def main() -> None:
        assert rule(User(name="Abdullah", age=18, is_admin=True))
        assert rule(User(name="Abdullah", age=16, is_admin=True))
        assert rule(User(name="admin", age=20, is_admin=False))


    if __name__ == "__main__":
        main()
    ```

    """

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
