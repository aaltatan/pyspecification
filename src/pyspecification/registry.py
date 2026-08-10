from collections.abc import Callable, Iterable
from functools import wraps
from inspect import get_annotations
from typing import Any, Concatenate

from pydantic import TypeAdapter

from .predicate import Predicate, ReturnType

# -----------------------
# models
# -----------------------

type RuleDefinitionFn[T, R: ReturnType, **P] = Callable[Concatenate[T, P], R]
type RuleFn[T, R: ReturnType, **P] = Callable[P, Predicate[T, R]]
type ProcessFn = Callable[[Any], Any]

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
# registry
# -----------------------


class PredicateRegistry[T, R: ReturnType]:
    def __init__(self) -> None:
        self._rules: dict[str, RuleFn] = {}

    @property
    def rules(self) -> dict[str, RuleFn]:
        return self._rules

    @property
    def rules_schema(self) -> dict[str, Any]:
        schema = {
            name: {**self._get_annotations(fn), "description": fn.__doc__ or ""}
            for name, fn in self._rules.items()
        }
        return dict(sorted(schema.items(), key=lambda item: item[0]))

    def __getitem__(self, name: str) -> RuleFn:
        if name not in self._rules:
            raise RuleNotRegisteredError(name)
        return self._rules[name]

    def rule[**P](
        self,
        *,
        name: str | None = None,
        process_fn: ProcessFn | None = None,
    ) -> Callable[[RuleDefinitionFn[T, R, P]], RuleFn[T, R, P]]:
        def decorator(fn: RuleDefinitionFn[T, R, P]) -> RuleFn[T, R, P]:
            return self._register_rule(fn, name=name, process_fn=process_fn)

        return decorator

    def register_rule[**P](
        self,
        fn: RuleDefinitionFn[T, R, P],
        *,
        name: str | None = None,
        process_fn: ProcessFn | None = None,
    ) -> RuleFn[T, R, P]:
        return self._register_rule(fn, name=name, process_fn=process_fn)

    def register_rules[**P](
        self,
        fns: Iterable[tuple[str, RuleDefinitionFn[T, R, P]]],
        *,
        process_fn: ProcessFn | None = None,
    ) -> None:
        for name, fn in fns:
            self._register_rule(fn, name=name, process_fn=process_fn)

    def _register_rule[**P](
        self,
        fn: RuleDefinitionFn[T, R, P],
        *,
        name: str | None = None,
        process_fn: ProcessFn | None = None,
    ) -> RuleFn[T, R, P]:
        rule_name = name or fn.__name__

        if rule_name in self._rules:
            raise RuleAlreadyRegisteredError(rule_name)

        @wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> Predicate[T, R]:
            if process_fn is not None:
                processed_args = self._process_args(process_fn, *args)
                processed_kwargs = self._process_kwargs(process_fn, **kwargs)

                return Predicate(lambda obj: fn(obj, *processed_args, **processed_kwargs))

            return Predicate(lambda obj: fn(obj, *args, **kwargs))

        self._rules[name or fn.__name__] = wrapper

        return wrapper

    def _process(self, value: T | list[T], process_fn: ProcessFn) -> T | list[T]:
        return [process_fn(v) for v in value] if isinstance(value, list) else process_fn(value)

    def _process_args(self, process_fn: ProcessFn, *args: Any) -> tuple[Any, ...]:
        return tuple(self._process(arg, process_fn) for arg in args)

    def _process_kwargs(self, process_fn: ProcessFn, **kwargs: Any) -> dict[str, Any]:
        return {
            key: self._process(kwarg, process_fn)
            for key, kwarg in kwargs.items()
            if kwargs is not None
        }

    def _get_annotations(self, fn: Callable[..., Any]) -> dict[str, Any]:
        return {
            arg: TypeAdapter(typ).json_schema()
            for arg, typ in get_annotations(fn).items()
            if arg not in ("return", "obj")
        }
