from collections.abc import Callable, Sequence
from functools import wraps
from typing import Any, Concatenate

from .constants import RESERVED_WORDS
from .predicate import Predicate, ReturnType
from .processors import DEFAULT_PROCESSORS, ProcessFn, process_arguments
from .rules import object_rule, subscriptable_rule
from .validators import validate_python_vars_fn_naming_convention

# -----------------------
# models
# -----------------------


type ObjectRuleDefinitionFn[T, R: ReturnType, **P] = Callable[Concatenate[T, P], R]
type ObjectRuleFn[T, R: ReturnType, **P] = Callable[P, Predicate[T, R]]

type SubscriptableRuleDefinitionFn[T: (dict, Sequence), K, R: ReturnType, **P] = Callable[
    Concatenate[T, K, P], R
]
type SubscriptableRuleFn[T: (dict, Sequence), K, R: ReturnType, **P] = Callable[
    Concatenate[K, P], Predicate[T, R]
]


# -----------------------
# exceptions
# -----------------------


class RuleAlreadyRegisteredError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Rule '{name}' is already registered")


class RuleNotRegisteredError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Rule '{name}' is not registered")


# -----------------------
# obj registry
# -----------------------


class ObjectPredicateRegistry[T, R: ReturnType]:
    def __init__(self) -> None:
        self._rules: dict[str, ObjectRuleFn[T, R, ...]] = {}

    @property
    def rules(self) -> dict[str, ObjectRuleFn[T, R, ...]]:
        return self._rules

    def __getitem__(self, name: str) -> ObjectRuleFn[T, R, ...]:
        if name not in self._rules:
            raise RuleNotRegisteredError(name)
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


class SubscriptablePredicateRegistry[T: (dict, Sequence), K, R: ReturnType]:
    def __init__(self) -> None:
        self._rules: dict[str, SubscriptableRuleFn[T, K, R, ...]] = {}

    @property
    def rules(self) -> dict[str, SubscriptableRuleFn[T, K, R, ...]]:
        return self._rules

    def __getitem__(self, name: str) -> SubscriptableRuleFn[T, K, R, ...]:
        if name not in self._rules:
            raise RuleNotRegisteredError(name)
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


def _process_rule_arguments(
    process_fn: ProcessFn | None = None,
    *args: Any,
    **kwargs: Any,
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    if process_fn:
        return tuple([process_fn(arg) for arg in args]), {
            key: process_fn(value) for key, value in kwargs
        }

    return args, kwargs


def _process_rule_name(fn: Callable[..., Any], name: str | None = None) -> str:
    rule_name = name or fn.__name__

    if rule_name.lower() in RESERVED_WORDS:
        msg = f"Rule name '{rule_name}' is reserved"
        raise ValueError(msg)

    validate_python_vars_fn_naming_convention(rule_name)

    return rule_name
