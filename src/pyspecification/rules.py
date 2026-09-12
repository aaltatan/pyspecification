from collections.abc import Callable
from functools import wraps
from typing import Any, Concatenate

from .exceptions import (
    MissingArgumentError,
    PositionalOnlyArgumentError,
    RuleKeyDoesNotExistError,
    TooManyArgumentsError,
    UnexpectedKeywordArgumentError,
    is_missing_argument_exception,
    is_positional_only_argument_exception,
    is_too_many_arguments_exception,
    is_unexpected_keyword_argument_exception,
)
from .predicate import OperatorType, Predicate, ReturnType


def object_rule[T, R: ReturnType, **P](
    *,
    operator: OperatorType = "logical",
    predicate_name: str | None = None,
) -> Callable[[Callable[Concatenate[T, P], R]], Callable[P, Predicate[T, R]]]:
    """A Decorator for creating object-based rules.

    Args:
        operator (Literal["bitwise", "logical"]): The operator to use for combining predicates.
        predicate_name (str, optional): The name of the predicate. Defaults to None.

    Example:
    ```python
    from dataclasses import dataclass
    from typing import Any

    from pyspecification import object_rule


    @dataclass
    class User:
        name: str
        age: int
        is_admin: bool


    @object_rule()
    def is_admin(user: User) -> bool:
        return user.is_admin


    @object_rule()
    def name__istartswith(user: User, value: str) -> bool:
        return user.name.lower().startswith(value.lower())


    @object_rule()
    def age__between(user: User, min_age: int, max_age: int) -> bool:
        return user.age >= min_age and user.age <= max_age


    def main() -> None:
        rule = is_admin() | (name__istartswith("admin") & age__between(18, 30))

        EMPLOYEES = [
            User(name="Alice", age=18, is_admin=True),
            User(name="Admin", age=6, is_admin=False),
            User(name="Admin", age=18, is_admin=False),
            User(name="David", age=12, is_admin=False),
            User(name="Eve", age=8, is_admin=True),
        ]

        print([e for e in EMPLOYEES if rule(e)])
        # [User(name='Alice', age=18, is_admin=True), User(name='Admin', age=18, is_admin=False), User(name='Eve', age=8, is_admin=True)]


    if __name__ == "__main__":
        main()
    ```

    """  # noqa: D401

    def decorator(
        fn: Callable[Concatenate[T, P], R],
    ) -> Callable[P, Predicate[T, R]]:
        @wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> Predicate[T, R]:

            @wraps(fn)
            def inner(obj: T) -> R:
                try:
                    return fn(obj, *args, **kwargs)
                except TypeError as e:
                    _raise_appropriate_type_error(e, fn)
                    raise

            return Predicate(inner, operator=operator, name=predicate_name)

        return wrapper

    return decorator


def subscriptable_rule[T, K, R: ReturnType, **P](
    *,
    operator: OperatorType = "logical",
    predicate_name: str | None = None,
    check_key_existence: bool = False,
    forbidden_keys: tuple[str, ...] | tuple[int, ...] = (),
) -> Callable[[Callable[Concatenate[T, K, P], R]], Callable[Concatenate[K, P], Predicate[T, R]]]:
    """A Decorator for creating subscriptable-based rules.

    Args:
        operator (Literal["bitwise", "logical"]): The operator to use for combining predicates.
        predicate_name (str, optional): The name of the predicate. Defaults to None.
        check_key_existence (bool, optional): Whether to check if the key exists in the dictionary or list. Defaults to False.
        forbidden_keys (set[str], optional): A set of keys that are not allowed in the dictionary. Defaults to None.

    Example:
    ```python
    from typing import Any

    from pyspecification import subscriptable_rule


    @subscriptable_rule()
    def string__ieq(d: dict[str, int], key: str, value: Any) -> bool:
        return d[key] == value


    @subscriptable_rule()
    def int__ge(d: dict[str, int], key: str, value: int | float) -> bool:
        return d[key] >= value


    def main() -> None:
        rule = string__ieq("name", "alice") | int__ge("age", 18)

        EMPLOYEES = [
            {"name": "Alice", "age": 5},
            {"name": "Admin", "age": 6},
            {"name": "Bob", "age": 6},
            {"name": "Charlie", "age": 3},
            {"name": "David", "age": 25},
            {"name": "Eve", "age": 30},
        ]

        print([e for e in EMPLOYEES if rule(e)])
        # [{'name': 'Alice', 'age': 5}, {'name': 'David', 'age': 25}, {'name': 'Eve', 'age': 30}]


    if __name__ == "__main__":
        main()
    ```

    """  # noqa: D401, E501

    def decorator(
        fn: Callable[Concatenate[T, K, P], R],
    ) -> Callable[Concatenate[K, P], Predicate[T, R]]:
        @wraps(fn)
        def wrapper(key: K, *args: P.args, **kwargs: P.kwargs) -> Predicate[T, R]:

            @wraps(fn)
            def inner(obj: T) -> R:

                checkers = [
                    lambda: forbidden_keys is not None and key in forbidden_keys,
                    lambda: (
                        check_key_existence
                        and isinstance(obj, list)
                        and isinstance(key, int)
                        and len(obj) <= key
                    ),
                    lambda: check_key_existence and isinstance(obj, dict) and key not in obj,
                ]

                if any(checker() for checker in checkers):
                    raise RuleKeyDoesNotExistError(str(key), fn.__name__)

                try:
                    return fn(obj, key, *args, **kwargs)
                except TypeError as e:
                    _raise_appropriate_type_error(e, fn)
                    raise

            return Predicate(inner, operator=operator, name=predicate_name)

        return wrapper

    return decorator


def _raise_appropriate_type_error(e: TypeError, fn: Callable[..., Any]) -> None:
    error_message = str(e) + f" at {fn.__name__}"

    if is_missing_argument_exception(e):
        raise MissingArgumentError(error_message) from e

    if is_unexpected_keyword_argument_exception(e):
        raise UnexpectedKeywordArgumentError(error_message) from e

    if is_too_many_arguments_exception(e):
        raise TooManyArgumentsError(error_message) from e

    if is_positional_only_argument_exception(e):
        raise PositionalOnlyArgumentError(error_message) from e
