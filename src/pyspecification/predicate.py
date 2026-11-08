# ruff: noqa: PGH003, SLF001

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from typing import Any, Literal, Protocol

type OperatorType = Literal["bitwise", "logical"]

ANONYMOUS = "anonymous"


@dataclass(frozen=True, slots=True)
class Failure:
    """A rule that made a predicate fail for an object.

    `negated` is `True` when the rule passed but the predicate required it not to,
    as in `~is_admin()` for an admin. `message` is the rule's `message=`, its
    description or its docstring, for showing to users.
    """

    rule: str
    args: tuple[Any, ...] = ()
    kwargs: Mapping[str, Any] = field(default_factory=dict)
    negated: bool = False
    message: str | None = None

    def __str__(self) -> str:
        arguments = [
            *map(repr, self.args),
            *(f"{k}={v!r}" for k, v in self.kwargs.items()),
        ]
        call = f"{self.rule}({', '.join(arguments)})" if arguments else self.rule
        return f"NOT {call}" if self.negated else call


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
        failure: Failure | None = None,
    ) -> None:
        self._fn = fn
        self._name = name
        self._operator = operator
        self._failure = failure
        self._failures: Callable[[T], tuple[Failure, ...]] = self._leaf_failures

    def __call__(self, obj: T) -> R:
        return self._fn(obj)

    def failures(self, obj: T) -> tuple[Failure, ...]:
        """Return the rules that make this predicate fail for `obj`; `()` when it passes.

        For `a & b` every failing side is listed, for `a | b` both sides are listed
        only when neither passes, and `~a` reports `a` as negated when `a` passed.
        Unnamed predicates (plain lambdas) are not reported.

        Raises:
            TypeError: For bitwise predicates, whose results (e.g. SQL expressions)
                cannot be evaluated in Python.

        Example:
        ```python
        >>> from pyspecification import object_rule
        >>> @object_rule()
        ... def age__ge(user: dict, minimum: int) -> bool:
        ...     return user["age"] >= minimum
        >>> @object_rule()
        ... def email__endswith(user: dict, domain: str) -> bool:
        ...     return user["email"].endswith(domain)
        >>> rule = age__ge(18) & email__endswith("@company.com")
        >>> rule.failures({"age": 30, "email": "sara@company.com"})
        ()
        >>> [str(failure) for failure in rule.failures({"age": 16, "email": "x@gmail.com"})]
        ['age__ge(18)', "email__endswith('@company.com')"]
        >>> [str(failure) for failure in (~age__ge(18)).failures({"age": 30, "email": ""})]
        ['NOT age__ge(18)']

        ```

        """
        if self._operator == "bitwise":
            msg = (
                f"failures() needs a logical predicate, {self!r} is bitwise: "
                "its results are expressions that cannot be evaluated in Python"
            )
            raise TypeError(msg)

        return self._failures(obj)

    def __and__(self, other: "Predicate[T, R]") -> "Predicate[T, R]":
        self._insure_matching_operators(other)

        if self._operator == "bitwise":
            return Predicate(
                lambda obj: self(obj) & other(obj),
                name=f"({self} & {other})",
                operator="bitwise",
            )

        combined: Predicate[T, R] = Predicate(
            lambda obj: self(obj) and other(obj),
            name=f"({self} AND {other})",
            operator="logical",
        )
        combined._failures = lambda obj: (*self._failures(obj), *other._failures(obj))
        return combined

    def __or__(self, other: "Predicate[T, R]") -> "Predicate[T, R]":
        self._insure_matching_operators(other)

        if self._operator == "bitwise":
            return Predicate(
                lambda obj: self(obj) | other(obj),
                name=f"({self} | {other})",
                operator="bitwise",
            )

        combined: Predicate[T, R] = Predicate(
            lambda obj: self(obj) or other(obj),
            name=f"({self} OR {other})",
            operator="logical",
        )
        combined._failures = lambda obj: _either_failures(self, other, obj)
        return combined

    def __invert__(self) -> "Predicate[T, R]":
        if self._operator == "bitwise":
            return Predicate(
                lambda obj: ~self(obj),
                name=f"~{self}",
                operator="bitwise",
            )

        inner_failure = self._failure or Failure(str(self))
        negated_failure = replace(inner_failure, negated=not inner_failure.negated)
        inverted: Predicate[T, R] = Predicate(
            lambda obj: not self(obj),  # type: ignore
            name=f"NOT {self}",
            operator="logical",
            failure=negated_failure,
        )
        inverted._failures = lambda obj: (
            (negated_failure,) if self(obj) and str(self) != ANONYMOUS else ()
        )
        return inverted

    def __str__(self) -> str:
        if self._name is not None:
            return self._name

        if self._fn.__name__ == "<lambda>":
            return ANONYMOUS

        return self._fn.__name__

    def __repr__(self) -> str:
        return f"Predicate({self})"

    def _leaf_failures(self, obj: T) -> tuple[Failure, ...]:
        if self(obj) or str(self) == ANONYMOUS:
            return ()
        return (self._failure or Failure(str(self)),)

    def _insure_matching_operators(self, other: "Predicate[T, R]") -> None:
        if self._operator != other._operator:
            msg = (
                "Cannot combine predicates with different operators:"
                f" {self._operator} != {other._operator}"
            )
            raise ValueError(msg)


def _either_failures[T](
    left: Predicate[T, Any], right: Predicate[T, Any], obj: T
) -> tuple[Failure, ...]:
    if left(obj) or right(obj):
        return ()
    return (*left._failures(obj), *right._failures(obj))
