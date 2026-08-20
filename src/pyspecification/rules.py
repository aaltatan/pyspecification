from collections.abc import Callable
from functools import wraps
from typing import Concatenate

from .core import Predicate, ReturnType


def object_rule[T, R: ReturnType, **P](
    fn: Callable[Concatenate[T, P], R],
) -> Callable[P, Predicate[T, R]]:
    """Decorator for creating rules for object-based predicates.

    Example:
    ```python
    from dataclasses import dataclass

    from pyspecification import object_rule


    @dataclass
    class User:
        name: str
        age: int
        is_admin: bool


    @object_rule
    def is_admin(user: User) -> bool:
        return user.is_admin


    @object_rule
    def age__gt(user: User, age: int) -> bool:
        return user.age > age


    @object_rule
    def age__lt(user: User, age: int) -> bool:
        return user.age < age


    rule = is_admin & age__gt(18) & age__lt(30)


    def main() -> None:
        assert rule(User("John", 20, True))
        assert not rule(User("John", 19, True))
        assert not rule(User("John", 30, True))
        assert not rule(User("John", 20, False))


    if __name__ == "__main__":
        main()
    ```

    """  # noqa: D401

    @wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Predicate[T, R]:
        @wraps(fn)
        def inner(obj: T) -> R:
            return fn(obj, *args, **kwargs)

        return Predicate(inner)

    return wrapper


def subscriptable_rule[T, K, R: ReturnType, **P](
    fn: Callable[Concatenate[T, K, P], R],
) -> Callable[Concatenate[K, P], Predicate[T, R]]:
    """Decorator for creating rules for subscriptable-based predicates.

    Example:
    ```python
    from typing import Any

    from pyspecification import subscriptable_rule


    @subscriptable_rule
    def eq(d: dict[str, int], key: str, value: Any) -> bool:
        return d[key] == value


    @subscriptable_rule
    def ge(d: dict[str, int], key: str, value: int | float) -> bool:
        return d[key] >= value


    rule = eq("name", "abdullah") & ge("age", 18)


    def main() -> None:
        assert rule({"name": "abdullah", "age": 18})
        assert not rule({"name": "abdullah", "age": 15})


    if __name__ == "__main__":
        main()
    ```

    """  # noqa: D401

    @wraps(fn)
    def wrapper(key: K, *args: P.args, **kwargs: P.kwargs) -> Predicate[T, R]:
        @wraps(fn)
        def inner(obj: T) -> R:
            return fn(obj, key, *args, **kwargs)

        return Predicate(inner)

    return wrapper
