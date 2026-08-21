from collections.abc import Callable, Sequence
from functools import wraps
from typing import Any, Concatenate

from pyspecification.constants import RESERVED_WORDS
from pyspecification.predicate import Predicate, ReturnType
from pyspecification.rules import object_rule, subscriptable_rule
from pyspecification.validators import validate_python_vars_fn_naming_convention

# -----------------------
# models
# -----------------------

type ProcessFn = Callable[[Any], Any]

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
        args_process_fn: ProcessFn | None = None,
        kwargs_process_fns: tuple[dict[str, ProcessFn], ProcessFn] | None = None,
    ) -> Callable[[ObjectRuleDefinitionFn[T, R, P]], ObjectRuleFn[T, R, P]]:
        def decorator(fn: ObjectRuleDefinitionFn[T, R, P]) -> ObjectRuleFn[T, R, P]:
            return self._register_rule(
                fn,
                name=name,
                args_process_fn=args_process_fn,
                kwargs_process_fns=kwargs_process_fns,
            )

        return decorator

    def register_rule[**P](
        self,
        fn: ObjectRuleDefinitionFn[T, R, P],
        *,
        name: str | None = None,
        args_process_fn: ProcessFn | None = None,
        kwargs_process_fns: tuple[dict[str, ProcessFn], ProcessFn] | None = None,
    ) -> ObjectRuleFn[T, R, P]:
        return self._register_rule(
            fn,
            name=name,
            args_process_fn=args_process_fn,
            kwargs_process_fns=kwargs_process_fns,
        )

    def _register_rule[**P](
        self,
        fn: ObjectRuleDefinitionFn[T, R, P],
        *,
        name: str | None = None,
        args_process_fn: ProcessFn | None = None,
        kwargs_process_fns: tuple[dict[str, ProcessFn], ProcessFn] | None = None,
    ) -> ObjectRuleFn[T, R, P]:
        rule_name = _process_rule_name(fn, name)

        if rule_name in self._rules:
            raise RuleAlreadyRegisteredError(rule_name)

        @wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> Predicate[T, R]:
            processed_args, processed_kwargs = process_arguments(
                args,
                kwargs,
                args_process_fn=args_process_fn,
                kwargs_process_fns=kwargs_process_fns,
            )
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
        args_process_fn: ProcessFn | None = None,
        kwargs_process_fns: tuple[dict[str, ProcessFn], ProcessFn] | None = None,
    ) -> Callable[[SubscriptableRuleDefinitionFn[T, K, R, P]], SubscriptableRuleFn[T, K, R, P]]:
        def decorator(
            fn: SubscriptableRuleDefinitionFn[T, K, R, P],
        ) -> SubscriptableRuleFn[T, K, R, P]:
            return self._register_rule(
                fn,
                name=name,
                args_process_fn=args_process_fn,
                kwargs_process_fns=kwargs_process_fns,
            )

        return decorator

    def register_rule[**P](
        self,
        fn: SubscriptableRuleDefinitionFn[T, K, R, P],
        *,
        name: str | None = None,
        args_process_fn: ProcessFn | None = None,
        kwargs_process_fns: tuple[dict[str, ProcessFn], ProcessFn] | None = None,
    ) -> SubscriptableRuleFn[T, K, R, P]:
        return self._register_rule(
            fn,
            name=name,
            args_process_fn=args_process_fn,
            kwargs_process_fns=kwargs_process_fns,
        )

    def _register_rule[**P](
        self,
        fn: SubscriptableRuleDefinitionFn[T, K, R, P],
        *,
        name: str | None = None,
        args_process_fn: ProcessFn | None = None,
        kwargs_process_fns: tuple[dict[str, ProcessFn], ProcessFn] | None = None,
    ) -> SubscriptableRuleFn[T, K, R, P]:
        rule_name = _process_rule_name(fn, name)

        if rule_name in self._rules:
            raise RuleAlreadyRegisteredError(rule_name)

        @wraps(fn)
        def wrapper(key: K, *args: P.args, **kwargs: P.kwargs) -> Predicate[T, R]:
            processed_args, processed_kwargs = process_arguments(
                args, kwargs, args_process_fn=args_process_fn, kwargs_process_fns=kwargs_process_fns
            )
            return subscriptable_rule(fn)(key, *processed_args, **processed_kwargs)

        self._rules[rule_name] = wrapper

        return wrapper


# -----------------------
# processors
# -----------------------


def _process_rule_name(fn: Callable[..., Any], name: str | None = None) -> str:
    rule_name = name or fn.__name__

    if rule_name.lower() in RESERVED_WORDS:
        msg = f"Rule name '{rule_name}' is reserved"
        raise ValueError(msg)

    validate_python_vars_fn_naming_convention(rule_name)

    return rule_name


def process_arguments(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    *,
    args_process_fn: ProcessFn | None,
    kwargs_process_fns: tuple[dict[str, ProcessFn], ProcessFn] | None,
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    processed_args = _process_args(args_process_fn, *args) if args_process_fn is not None else args

    if kwargs_process_fns is None:
        return processed_args, kwargs

    process_fns, fallback_process_fn = kwargs_process_fns

    processed_kwargs = _process_kwargs(process_fns, fallback_process_fn, **kwargs)

    return processed_args, processed_kwargs


def _process[T](value: T | list[T], processor: ProcessFn) -> T | list[T]:
    return [processor(v) for v in value] if isinstance(value, list) else processor(value)


def _process_args(processor: ProcessFn, *args: Any) -> tuple[Any, ...]:
    return tuple(_process(arg, processor) for arg in args)


def _process_kwargs(
    processors: dict[str, ProcessFn], fallback_processor: ProcessFn, **kwargs: Any
) -> dict[str, Any]:
    processed_kwargs = {}

    for key, kwarg in kwargs.items():
        process_fn = processors.get(key, fallback_processor)
        processed_kwargs[key] = _process(kwarg, process_fn)

    return processed_kwargs
