# ruff: noqa: PLR0913
from collections.abc import Callable
from functools import wraps
from typing import Any, Concatenate

from .constants import RESERVED_WORDS
from .exceptions import RuleAlreadyRegisteredError, RuleDoesNotExistError
from .predicate import OperatorType, Predicate, ReturnType
from .processors import DEFAULT_PROCESSORS, ProcessFn, process_arguments
from .rules import object_rule, subscriptable_rule
from .validators import validate_python_vars_fn_naming_convention

type ObjectRuleDefinitionFn[T, R: ReturnType, **P] = Callable[Concatenate[T, P], R]
type ObjectRuleFn[T, R: ReturnType, **P] = Callable[P, Predicate[T, R]]

type SubscriptableRuleDefinitionFn[T, K, R: ReturnType, **P] = Callable[Concatenate[T, K, P], R]
type SubscriptableRuleFn[T, K, R: ReturnType, **P] = Callable[Concatenate[K, P], Predicate[T, R]]


class ObjectRulesRegistry[T, R: ReturnType]:
    """A registry for object-based rules.

    Args:
        operator (Literal["bitwise", "logical"]): The operator to use for combining predicates.

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

    def __init__(self, operator: OperatorType) -> None:
        self._rules: dict[str, ObjectRuleFn[T, R, ...]] = {}
        self._hidden: set[str] = set()

        self._operator = operator

    @property
    def rules(self) -> dict[str, ObjectRuleFn[T, R, ...]]:
        """A dictionary of registered rules."""
        return {
            rule_name: rule
            for rule_name, rule in self._rules.items()
            if rule_name not in self._hidden
        }

    def __getitem__(self, name: str) -> ObjectRuleFn[T, R, ...]:
        if name not in self._rules or name in self._hidden:
            raise RuleDoesNotExistError(name, self.rules.keys())
        return self._rules[name]

    def rule[**P](
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        processors: tuple[ProcessFn, dict[str, ProcessFn]] = DEFAULT_PROCESSORS,
        hidden: bool = False,
    ) -> Callable[[ObjectRuleDefinitionFn[T, R, P]], ObjectRuleFn[T, R, P]]:
        """A decorator for registering an object-based rule.

        Args:
            name (str, optional): The name of the rule, this will override the name of the function. Defaults to None.
            description (str, optional): The description of the rule, this will override the docstring of the function. Defaults to None.
            processors (tuple[ProcessFn, dict[str, ProcessFn]], optional): The processors to use for processing arguments and keywords. Defaults to DEFAULT_PROCESSORS.
            hidden (bool, optional): Whether to hide the rule from the registry. Defaults to False.

        Returns:
            Callable[[ObjectRuleDefinitionFn[T, R, P]], ObjectRuleFn[T, R, P]]: The decorator.

        """  # noqa: D401, E501

        def decorator(fn: ObjectRuleDefinitionFn[T, R, P]) -> ObjectRuleFn[T, R, P]:
            return self._register_rule(
                fn,
                name=name,
                description=description,
                processors=processors,
                hidden=hidden,
            )

        return decorator

    def register_rule[**P](
        self,
        fn: ObjectRuleDefinitionFn[T, R, P],
        /,
        *,
        name: str | None = None,
        description: str | None = None,
        processors: tuple[ProcessFn, dict[str, ProcessFn]] = DEFAULT_PROCESSORS,
        hidden: bool = False,
    ) -> ObjectRuleFn[T, R, P]:
        """A method for registering an object-based rule.

        Args:
            fn (ObjectRuleDefinitionFn[T, R, P]): The function to register.
            name (str, optional): The name of the rule, this will override the name of the function. Defaults to None.
            description (str, optional): The description of the rule, this will override the docstring of the function. Defaults to None.
            processors (tuple[ProcessFn, dict[str, ProcessFn]], optional): The processors to use for processing arguments and keywords. Defaults to DEFAULT_PROCESSORS.
            hidden (bool, optional): Whether to hide the rule from the registry. Defaults to False.

        Returns:
            ObjectRuleFn[T, R, P]: The registered rule.

        """  # noqa: D401, E501
        return self._register_rule(
            fn,
            name=name,
            description=description,
            processors=processors,
            hidden=hidden,
        )

    def _register_rule[**P](
        self,
        fn: ObjectRuleDefinitionFn[T, R, P],
        *,
        name: str | None,
        description: str | None,
        processors: tuple[ProcessFn, dict[str, ProcessFn]],
        hidden: bool,
    ) -> ObjectRuleFn[T, R, P]:
        rule_name = _process_rule_name(fn, name)

        if hidden:
            self._hidden.add(rule_name)

        if rule_name in self._rules:
            raise RuleAlreadyRegisteredError(rule_name)

        @wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> Predicate[T, R]:
            processed_args, processed_kwargs = process_arguments(processors, *args, **kwargs)
            return object_rule(
                operator=self._operator,  # type: ignore  # noqa: PGH003
                predicate_name=rule_name,
            )(fn)(*processed_args, **processed_kwargs)

        wrapper.__doc__ = description or fn.__doc__

        self._rules[rule_name] = wrapper

        return wrapper


class SubscriptableRulesRegistry[T, K, R: ReturnType]:
    """A registry for subscriptable-based rules.

    Args:
        operator (Literal["bitwise", "logical"]): The operator to use for combining predicates.

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

    def __init__(
        self,
        *,
        operator: OperatorType,
        check_key_existence: bool = False,
        forbidden_keys: tuple[str, ...] | tuple[int, ...] = (),
    ) -> None:
        self._rules: dict[str, SubscriptableRuleFn[T, K, R, ...]] = {}
        self._hidden: set[str] = set()

        self._operator = operator
        self._check_key_existence = check_key_existence
        self._forbidden_keys = forbidden_keys

    @property
    def rules(self) -> dict[str, SubscriptableRuleFn[T, K, R, ...]]:
        """A dictionary of registered rules."""
        return {
            rule_name: rule
            for rule_name, rule in self._rules.items()
            if rule_name not in self._hidden
        }

    def __getitem__(self, name: str) -> SubscriptableRuleFn[T, K, R, ...]:
        if name not in self._rules or name in self._hidden:
            raise RuleDoesNotExistError(name, self.rules.keys())
        return self._rules[name]

    def rule[**P](
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        processors: tuple[ProcessFn, dict[str, ProcessFn]] = DEFAULT_PROCESSORS,
        hidden: bool = False,
        check_key_existence: bool | None = None,
        forbidden_keys: tuple[str, ...] | tuple[int, ...] = (),
    ) -> Callable[[SubscriptableRuleDefinitionFn[T, K, R, P]], SubscriptableRuleFn[T, K, R, P]]:
        """A decorator for registering a subscriptable-based rule.

        Args:
            name (str, optional): The name of the rule, this will override the name of the function. Defaults to None.
            description (str, optional): The description of the rule, this will override the docstring of the function. Defaults to None.
            processors (tuple[ProcessFn, dict[str, ProcessFn]], optional): The processors to use for processing arguments and keywords. Defaults to DEFAULT_PROCESSORS.
            hidden (bool, optional): Whether to hide the rule from the registry. Defaults to False.
            check_key_existence (bool, optional): Whether to check if the key exists in the dictionary or list. Defaults to None.
            forbidden_keys (tuple[str, ...] | tuple[int, ...], optional): A set of keys that are not allowed in the dictionary. Defaults to ().

        Returns:
            Callable[[SubscriptableRuleDefinitionFn[T, K, R, P]], SubscriptableRuleFn[T, K, R, P]]: The decorator.

        """  # noqa: D401, E501

        def decorator(
            fn: SubscriptableRuleDefinitionFn[T, K, R, P],
        ) -> SubscriptableRuleFn[T, K, R, P]:
            return self._register_rule(
                fn,
                name=name,
                description=description,
                processors=processors,
                hidden=hidden,
                check_key_existence=check_key_existence,
                forbidden_keys=forbidden_keys,
            )

        return decorator

    def register_rule[**P](
        self,
        fn: SubscriptableRuleDefinitionFn[T, K, R, P],
        /,
        *,
        name: str | None = None,
        description: str | None = None,
        processors: tuple[ProcessFn, dict[str, ProcessFn]] = DEFAULT_PROCESSORS,
        hidden: bool = False,
        check_key_existence: bool | None = None,
        forbidden_keys: tuple[str, ...] | tuple[int, ...] = (),
    ) -> SubscriptableRuleFn[T, K, R, P]:
        """A method for registering a subscriptable-based rule.

        Args:
            fn (SubscriptableRuleDefinitionFn[T, K, R, P]): The function to register.
            name (str, optional): The name of the rule, this will override the name of the function. Defaults to None.
            description (str, optional): The description of the rule, this will override the docstring of the function. Defaults to None.
            processors (tuple[ProcessFn, dict[str, ProcessFn]], optional): The processors to use for processing arguments and keywords. Defaults to DEFAULT_PROCESSORS.
            hidden (bool, optional): Whether to hide the rule from the registry. Defaults to False.
            check_key_existence (bool, optional): Whether to check if the key exists in the dictionary or list. Defaults to None.
            forbidden_keys (tuple[str, ...] | tuple[int, ...], optional): A set of keys that are not allowed in the dictionary. Defaults to ().

        Returns:
            SubscriptableRuleFn[T, K, R, P]: The registered rule.

        """  # noqa: D401, E501
        return self._register_rule(
            fn,
            name=name,
            description=description,
            processors=processors,
            hidden=hidden,
            check_key_existence=check_key_existence,
            forbidden_keys=forbidden_keys,
        )

    def _register_rule[**P](
        self,
        fn: SubscriptableRuleDefinitionFn[T, K, R, P],
        *,
        name: str | None,
        description: str | None,
        processors: tuple[ProcessFn, dict[str, ProcessFn]],
        hidden: bool,
        check_key_existence: bool | None,
        forbidden_keys: tuple[str, ...] | tuple[int, ...],
    ) -> SubscriptableRuleFn[T, K, R, P]:
        rule_name = _process_rule_name(fn, name)

        if hidden:
            self._hidden.add(rule_name)

        if rule_name in self._rules:
            raise RuleAlreadyRegisteredError(rule_name)

        @wraps(fn)
        def wrapper(key: K, *args: P.args, **kwargs: P.kwargs) -> Predicate[T, R]:

            processed_args, processed_kwargs = process_arguments(processors, *args, **kwargs)

            return subscriptable_rule(
                operator=self._operator,  # type: ignore  # noqa: PGH003
                predicate_name=rule_name,
                check_key_existence=(
                    check_key_existence
                    if check_key_existence is not None
                    else self._check_key_existence
                ),
                forbidden_keys=(
                    forbidden_keys if forbidden_keys is not None else self._forbidden_keys
                ),
            )(fn)(key, *processed_args, **processed_kwargs)

        wrapper.__doc__ = description or fn.__doc__

        self._rules[rule_name] = wrapper

        return wrapper


def _process_rule_name(fn: Callable[..., Any], name: str | None = None) -> str:
    rule_name = name or fn.__name__

    if rule_name.lower() in RESERVED_WORDS:
        msg = f"Rule name '{rule_name}' is reserved"
        raise ValueError(msg)

    validate_python_vars_fn_naming_convention(rule_name)

    return rule_name
