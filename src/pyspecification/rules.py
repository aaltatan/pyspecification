from collections.abc import Callable
from functools import wraps
from typing import Concatenate

from .exceptions import RuleKeyDoesNotExistError
from .predicate import OperatorType, Predicate, ReturnType


def object_rule[T, R: ReturnType, **P](
    *,
    operator: OperatorType = "logical",
) -> Callable[[Callable[Concatenate[T, P], R]], Callable[P, Predicate[T, R]]]:
    """A Decorator for creating object-based rules.

    Args:
        operator (Literal["bitwise", "logical"]): The operator to use for combining predicates.

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


    @object_rule(operator="logical")
    def is_admin(user: User) -> bool:
        return user.is_admin


    @object_rule(operator="bitwise")
    def name__istartswith(user: User, value: str) -> bool:
        return user.name.lower().startswith(value.lower())


    @object_rule(operator="logical")
    def age__between(user: User, min_age: int, max_age: int) -> bool:
        return user.age >= min_age and user.age <= max_age


    def main() -> None:
        rule = is_admin() | (name__istartswith("admin") & age__between(18, 30))

        EMPLOYEES = [
            User(name="Alice", age=18, is_admin=True),
            User(name="Bob", age=6, is_admin=True),
            User(name="Charlie", age=3, is_admin=False),
            User(name="David", age=12, is_admin=False),
            User(name="Eve", age=8, is_admin=True),
        ]

        results = [rule(emp) for emp in EMPLOYEES]
        assert results == [True, True, False, False, True]


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
                return fn(obj, *args, **kwargs)

            return Predicate(inner, operator=operator)

        return wrapper

    return decorator


def subscriptable_rule[T, K, R: ReturnType, **P](
    *,
    operator: OperatorType = "logical",
    check_key_existence: bool = False,
    forbidden_keys: tuple[str, ...] | tuple[int, ...] = (),
) -> Callable[[Callable[Concatenate[T, K, P], R]], Callable[Concatenate[K, P], Predicate[T, R]]]:
    """A Decorator for creating subscriptable-based rules.

    Args:
        operator (Literal["bitwise", "logical"]): The operator to use for combining predicates.
        check_key_existence (bool, optional): Whether to check if the key exists in the dictionary or list. Defaults to False.
        forbidden_keys (set[str], optional): A set of keys that are not allowed in the dictionary. Defaults to None.

    Example:
    ```python
    from typing import Any

    from pyspecification import subscriptable_rule


    @subscriptable_rule(operator="logical")
    def eq(d: dict[str, int], key: str, value: Any) -> bool:
        return d[key] == value


    @subscriptable_rule(operator="bitwise")
    def ge(d: dict[str, int], key: str, value: int | float) -> bool:
        return d[key] >= value


    def main() -> None:
        rule = eq("name", "abdullah") & ge("age", 18)

        EMPLOYEES = [
            {"name": "Alice", "age": 18},
            {"name": "Bob", "age": 6},
            {"name": "Charlie", "age": 3},
            {"name": "David", "age": 12},
            {"name": "Eve", "age": 8},
        ]

        results = [rule(emp) for emp in EMPLOYEES]
        assert results == [True, True, False, False, True]


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

                return fn(obj, key, *args, **kwargs)

            return Predicate(inner, operator=operator)

        return wrapper

    return decorator
