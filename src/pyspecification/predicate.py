# ruff: noqa: PGH003, SLF001

from collections.abc import Callable
from typing import Any, Literal, Protocol

type OperatorType = Literal["bitwise", "logical"]


class ReturnType(Protocol):
    def __and__(self, value: Any, /) -> Any: ...
    def __or__(self, value: Any, /) -> Any: ...
    def __invert__(self) -> Any: ...


class Predicate[T, R: ReturnType]:
    """A predicate is a function that takes an object of type T and returns a value of type R.

    Args:
        fn (Callable[[T], R]): The function to wrap.
        operator (Literal["bitwise", "logical"]): The operator to use for combining predicates.
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


    is_admin: Predicate[User, bool] = Predicate(
        is_admin,
        operator="logical",
    )
    name__istartswith: Predicate[User, bool] = Predicate(
        name__istartswith,
        operator="logical",
    )
    age__between: Predicate[User, bool] = Predicate(
        age__between,
        operator="logical",
    )


    rule = is_admin | (name__istartswith("admin") & age__between(18, 30))


    def main() -> None:
        assert rule(User(name="Abdullah", age=18, is_admin=True))
        assert rule(User(name="Abdullah", age=16, is_admin=True))
        assert rule(User(name="admin", age=20, is_admin=False))

        print(rule(User(name="Abdullah", age=18, is_admin=True)))
        # True

        print(repr(rule))
        # Predicate((is_admin OR (name__istartswith AND age__between)))


    if __name__ == "__main__":
        main()
    ```

    """

    def __init__(
        self,
        fn: Callable[[T], R],
        /,
        *,
        operator: OperatorType,
        name: str | None = None,
    ) -> None:
        self._fn = fn
        self._name = name
        self._operator = operator

    def __call__(self, obj: T) -> R:
        return self._fn(obj)

    def __and__(self, other: "Predicate[T, R]") -> "Predicate[T, R]":
        self._insure_matching_operators(other)

        if self._operator == "bitwise":
            return Predicate(
                lambda obj: self(obj) & other(obj),
                name=f"({self} & {other})",
                operator="bitwise",
            )

        return Predicate(
            lambda obj: self(obj) and other(obj),
            name=f"({self} AND {other})",
            operator="logical",
        )

    def __or__(self, other: "Predicate[T, R]") -> "Predicate[T, R]":
        self._insure_matching_operators(other)

        if self._operator == "bitwise":
            return Predicate(
                lambda obj: self(obj) | other(obj),
                name=f"({self} | {other})",
                operator="bitwise",
            )

        return Predicate(
            lambda obj: self(obj) or other(obj),
            name=f"({self} OR {other})",
            operator="logical",
        )

    def __invert__(self) -> "Predicate[T, R]":
        if self._operator == "bitwise":
            return Predicate(
                lambda obj: ~self(obj),
                name=f"~{self}",
                operator="bitwise",
            )

        return Predicate(
            lambda obj: not self(obj),  # type: ignore
            name=f"NOT {self}",
            operator="logical",
        )

    def __str__(self) -> str:
        if self._name is not None:
            return self._name

        if self._fn.__name__ == "<lambda>":
            return "anonymous"

        return self._fn.__name__

    def __repr__(self) -> str:
        return f"Predicate({self})"

    def _insure_matching_operators(self, other: "Predicate[T, R]") -> None:
        if self._operator != other._operator:
            msg = (
                "Cannot combine predicates with different operators:"
                f" {self._operator} != {other._operator}"
            )
            raise ValueError(msg)
