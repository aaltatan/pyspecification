from collections.abc import Callable
from functools import wraps
from inspect import BoundArguments, Parameter, Signature, signature
from typing import Any, Concatenate

from pyargprocessors import Process, find_processors, process_arguments

from .exceptions import (
    InvalidRuleError,
    PositionalOnlyArgumentError,
    RuleKeyDoesNotExistError,
    to_argument_error,
)
from .predicate import OperatorType, Predicate, ReturnType

_POSITIONAL_KINDS = (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD)


def object_rule[T, R: ReturnType, **P](
    *,
    operator: OperatorType = "logical",
    predicate_name: str | None = None,
) -> Callable[[Callable[Concatenate[T, P], R]], Callable[P, Predicate[T, R]]]:
    """A Decorator for creating object-based rules.

    Arguments are bound to the rule signature as soon as the rule is called, so
    mistakes raise an `ArgumentError` subclass while the predicate is being built,
    not when it is evaluated. A parameter annotated with `Annotated[T, Process(fn)]`
    has `fn` applied to its value at that moment, see `pyargprocessors.Process`.

    Args:
        operator (Literal["bitwise", "logical"]): The operator to use for combining predicates.
        predicate_name (str, optional): The name of the predicate. Defaults to None.

    Raises:
        InvalidRuleError: If the function does not accept the object under test positionally.
        InvalidProcessorError: If a `Process` marker is misplaced.

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

    """  # noqa: D401, E501

    def decorator(
        fn: Callable[Concatenate[T, P], R],
    ) -> Callable[P, Predicate[T, R]]:
        rule_name = predicate_name or fn.__name__
        arguments_signature = rule_signature(fn, rule_name, reserved=1)
        processors = find_processors(fn, name=rule_name, skip=1)

        @wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> Predicate[T, R]:
            bound = bind_arguments(arguments_signature, processors, rule_name, args, kwargs)

            @wraps(fn)
            def inner(obj: T) -> R:
                return fn(obj, *bound.args, **bound.kwargs)

            return Predicate(inner, operator=operator, name=predicate_name)

        wrapper.__signature__ = arguments_signature  # type: ignore[attr-defined]

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

    The rule factory takes the key first, then the rule's own arguments. They are
    bound to the rule signature as soon as the rule is called, so mistakes raise
    an `ArgumentError` subclass while the predicate is being built, not when it is
    evaluated. A parameter annotated with `Annotated[T, Process(fn)]` has `fn`
    applied to its value at that moment, see `pyargprocessors.Process`; the key
    itself cannot be processed.

    Args:
        operator (Literal["bitwise", "logical"]): The operator to use for combining predicates.
        predicate_name (str, optional): The name of the predicate. Defaults to None.
        check_key_existence (bool, optional): Whether to check if the key exists in the dictionary or list. Defaults to False.
        forbidden_keys (set[str], optional): A set of keys that are not allowed in the dictionary. Defaults to None.

    Raises:
        InvalidRuleError: If the function does not accept the object and the key positionally.
        InvalidProcessorError: If a `Process` marker is misplaced.

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
        rule_name = predicate_name or fn.__name__
        arguments_signature = rule_signature(fn, rule_name, reserved=2)
        processors = find_processors(fn, name=rule_name, skip=2)
        key_name = next(iter(arguments_signature.parameters))

        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Predicate[T, R]:
            bound = bind_arguments(arguments_signature, processors, rule_name, args, kwargs)
            key = bound.arguments[key_name]

            @wraps(fn)
            def inner(obj: T) -> R:

                checkers = [
                    lambda: forbidden_keys is not None and key in forbidden_keys,
                    lambda: (
                        check_key_existence
                        and isinstance(obj, list)
                        and isinstance(key, int)
                        and not (-len(obj) <= key < len(obj))
                    ),
                    lambda: check_key_existence and isinstance(obj, dict) and key not in obj,
                ]

                if any(checker() for checker in checkers):
                    raise RuleKeyDoesNotExistError(str(key), fn.__name__)

                return fn(obj, *bound.args, **bound.kwargs)

            return Predicate(inner, operator=operator, name=predicate_name)

        wrapper.__signature__ = arguments_signature  # type: ignore[attr-defined]

        return wrapper

    return decorator


def rule_signature(fn: Callable[..., Any], rule_name: str, *, reserved: int) -> Signature:
    """Return the signature of a rule factory: `fn` without the object under test.

    `fn` must accept its first `reserved` parameters positionally: just the
    object under test for object rules, plus the key for subscriptable rules.
    Only the object under test is dropped, the key stays an argument of the factory.

    Raises:
        InvalidRuleError: If `fn` does not accept them positionally.
    """
    try:
        parameters = list(signature(fn).parameters.values())
    except ValueError as error:
        msg = f"Rule '{rule_name}' must accept the object under test as its first positional parameter"
        raise InvalidRuleError(msg) from error

    leading = parameters[:reserved]

    if len(leading) < reserved or any(p.kind not in _POSITIONAL_KINDS for p in leading):
        needed = "the object under test and the key" if reserved == 2 else "the object under test"  # noqa: PLR2004
        msg = f"Rule '{rule_name}' must accept {needed} as its leading positional parameters"
        raise InvalidRuleError(msg)

    return Signature(parameters[1:])


def bind_arguments(
    arguments_signature: Signature,
    processors: dict[str, tuple[Process, ...]],
    rule_name: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> BoundArguments:
    """Bind rule arguments to a signature, raising the matching `ArgumentError`, then process them.

    Problems are reported in the order Python itself reports them for a call:
    keywords that cannot be passed by name first, then surplus or repeated
    arguments, and only then the missing ones. So a typo in a keyword is
    reported as an unexpected keyword rather than as a missing argument.
    """
    parameters = arguments_signature.parameters

    if not any(p.kind is Parameter.VAR_KEYWORD for p in parameters.values()) and (
        positional_only := [
            name
            for name in kwargs
            if name in parameters and parameters[name].kind is Parameter.POSITIONAL_ONLY
        ]
    ):
        msg = (
            "got some positional-only arguments passed as keyword arguments: "
            f"{', '.join(positional_only)} for rule '{rule_name}'"
        )
        raise PositionalOnlyArgumentError(msg)

    try:
        arguments_signature.bind_partial(*args, **kwargs)
        bound = arguments_signature.bind(*args, **kwargs)
    except TypeError as error:
        raise to_argument_error(error, rule_name) from error

    return process_arguments(processors, bound) if processors else bound
