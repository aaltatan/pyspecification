from collections.abc import Callable
from functools import wraps
from typing import Any, Concatenate

from .constants import RESERVED_WORDS
from .exceptions import RuleNotFoundError
from .predicate import Predicate, ReturnType
from .processors import DEFAULT_PROCESSORS, ProcessFn, process_arguments
from .rules import object_rule, subscriptable_rule
from .validators import validate_python_vars_fn_naming_convention

# -----------------------
# models
# -----------------------


type ObjectRuleDefinitionFn[T, R: ReturnType, **P] = Callable[Concatenate[T, P], R]
type ObjectRuleFn[T, R: ReturnType, **P] = Callable[P, Predicate[T, R]]

type SubscriptableRuleDefinitionFn[T, K, R: ReturnType, **P] = Callable[Concatenate[T, K, P], R]
type SubscriptableRuleFn[T, K, R: ReturnType, **P] = Callable[Concatenate[K, P], Predicate[T, R]]


# -----------------------
# exceptions
# -----------------------


class RuleAlreadyRegisteredError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Rule '{name}' is already registered")


# -----------------------
# obj registry
# -----------------------


class ObjectRulesRegistry[T, R: ReturnType]:
    """A registry for object-based rules.

    Example:
    ```python
    from dataclasses import dataclass
    from typing import Any

    from pyspecification import ObjectRulesRegistry, Predicate, PredicateCompiler, object_rule


    @dataclass
    class User:
        name: str
        age: int
        is_admin: bool


    @object_rule
    def is_admin(user: User) -> bool:
        return user.is_admin


    @object_rule
    def name__istartswith(user: User, value: str) -> bool:
        return user.name.lower().startswith(value.lower())


    @object_rule
    def age__between(user: User, min_age: int, max_age: int) -> bool:
        return user.age >= min_age and user.age <= max_age


    def main() -> None:
        registry = ObjectRulesRegistry[User, bool]()

        # Access registered rules via registry
        is_admin = registry["is_admin"]
        name__istartswith = registry["name__istartswith"]
        age__between = registry["age__between"]

        # Manual composition: Manager OR (Engineering AND exp >= 5)
        rule = is_admin | (name__istartswith("admin") & age__between(18, 30))

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

    """

    def __init__(self) -> None:
        self._rules: dict[str, ObjectRuleFn[T, R, ...]] = {}

    @property
    def rules(self) -> dict[str, ObjectRuleFn[T, R, ...]]:
        return self._rules

    def __getitem__(self, name: str) -> ObjectRuleFn[T, R, ...]:
        if name not in self._rules:
            raise RuleNotFoundError(name, "registered")
        return self._rules[name]

    def rule[**P](
        self,
        *,
        name: str | None = None,
        processors: tuple[ProcessFn, dict[str, ProcessFn]] = DEFAULT_PROCESSORS,
    ) -> Callable[[ObjectRuleDefinitionFn[T, R, P]], ObjectRuleFn[T, R, P]]:
        def decorator(fn: ObjectRuleDefinitionFn[T, R, P]) -> ObjectRuleFn[T, R, P]:
            return self._register_rule(fn, name=name, processors=processors)

        return decorator

    def register_rule[**P](
        self,
        fn: ObjectRuleDefinitionFn[T, R, P],
        *,
        name: str | None = None,
        processors: tuple[ProcessFn, dict[str, ProcessFn]] = DEFAULT_PROCESSORS,
    ) -> ObjectRuleFn[T, R, P]:
        return self._register_rule(fn, name=name, processors=processors)

    def _register_rule[**P](
        self,
        fn: ObjectRuleDefinitionFn[T, R, P],
        *,
        name: str | None,
        processors: tuple[ProcessFn, dict[str, ProcessFn]],
    ) -> ObjectRuleFn[T, R, P]:
        rule_name = _process_rule_name(fn, name)

        if rule_name in self._rules:
            raise RuleAlreadyRegisteredError(rule_name)

        @wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> Predicate[T, R]:
            processed_args, processed_kwargs = process_arguments(processors, *args, **kwargs)
            return object_rule(fn)(*processed_args, **processed_kwargs)

        self._rules[rule_name] = wrapper

        return wrapper


# -----------------------
# subscriptable registry
# -----------------------


class SubscriptableRulesRegistry[T, K, R: ReturnType]:
    """A registry for subscriptable-based rules.

    Example:
    ```python
    from typing import Any

    from pyspecification import (
        SubscriptableRulesRegistry,
        Predicate,
        PredicateCompiler,
        subscriptable_rule,
    )


    @subscriptable_rule
    def eq(d: dict[str, int], key: str, value: Any) -> bool:
        return d[key] == value


    @subscriptable_rule
    def ge(d: dict[str, int], key: str, value: int | float) -> bool:
        return d[key] >= value


    def main() -> None:
        registry = SubscriptableRulesRegistry[dict[str, Any], str, bool]()

        # Access registered rules via registry
        eq = registry["eq"]
        ge = registry["ge"]

        # Manual composition: name == "abdullah" AND age >= 18
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

    Example:
    ```python
    from typing import Any

    from pyspecification import (
        SubscriptableRulesRegistry,
        Predicate,
        PredicateCompiler,
        subscriptable_rule,
    )


    @subscriptable_rule
    def eq(l: list[Any], idx: int, value: Any) -> bool:
        return l[idx] == value


    @subscriptable_rule
    def ge(l: list[Any], idx: int, value: int | float) -> bool:
        return l[idx] >= value


    def main() -> None:
        registry = SubscriptableRulesRegistry[list[Any], int, bool]()

        # Access registered rules via registry
        eq = registry["eq"]
        ge = registry["ge"]

        # Manual composition: seq[0] == "Abdullah" AND seq[1] >= 18
        rule = eq(-1, "Abdullah") & ge(0, 18)

        EMPLOYEES = [
            ["Abdullah", 18],
            ["Bob", 6],
            ["Charlie", 3],
            ["David", 12],
            ["Eve", 8],
        ]

        results = [rule(emp) for emp in EMPLOYEES]
        assert results == [True, True, False, False, True]


    if __name__ == "__main__":
        main()
    ```

    """

    def __init__(self) -> None:
        self._rules: dict[str, SubscriptableRuleFn[T, K, R, ...]] = {}

    @property
    def rules(self) -> dict[str, SubscriptableRuleFn[T, K, R, ...]]:
        return self._rules

    def __getitem__(self, name: str) -> SubscriptableRuleFn[T, K, R, ...]:
        if name not in self._rules:
            raise RuleNotFoundError(name, "registered")
        return self._rules[name]

    def rule[**P](
        self,
        *,
        name: str | None = None,
        processors: tuple[ProcessFn, dict[str, ProcessFn]] = DEFAULT_PROCESSORS,
    ) -> Callable[[SubscriptableRuleDefinitionFn[T, K, R, P]], SubscriptableRuleFn[T, K, R, P]]:
        def decorator(
            fn: SubscriptableRuleDefinitionFn[T, K, R, P],
        ) -> SubscriptableRuleFn[T, K, R, P]:
            return self._register_rule(fn, name=name, processors=processors)

        return decorator

    def register_rule[**P](
        self,
        fn: SubscriptableRuleDefinitionFn[T, K, R, P],
        *,
        name: str | None = None,
        processors: tuple[ProcessFn, dict[str, ProcessFn]] = DEFAULT_PROCESSORS,
    ) -> SubscriptableRuleFn[T, K, R, P]:
        return self._register_rule(fn, name=name, processors=processors)

    def _register_rule[**P](
        self,
        fn: SubscriptableRuleDefinitionFn[T, K, R, P],
        *,
        name: str | None,
        processors: tuple[ProcessFn, dict[str, ProcessFn]],
    ) -> SubscriptableRuleFn[T, K, R, P]:
        rule_name = _process_rule_name(fn, name)

        if rule_name in self._rules:
            raise RuleAlreadyRegisteredError(rule_name)

        @wraps(fn)
        def wrapper(key: K, *args: P.args, **kwargs: P.kwargs) -> Predicate[T, R]:
            processed_args, processed_kwargs = process_arguments(processors, *args, **kwargs)
            return subscriptable_rule(fn)(key, *processed_args, **processed_kwargs)

        self._rules[rule_name] = wrapper

        return wrapper


def _process_rule_name(fn: Callable[..., Any], name: str | None = None) -> str:
    rule_name = name or fn.__name__

    if rule_name.lower() in RESERVED_WORDS:
        msg = f"Rule name '{rule_name}' is reserved"
        raise ValueError(msg)

    validate_python_vars_fn_naming_convention(rule_name)

    return rule_name
