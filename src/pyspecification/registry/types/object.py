from collections.abc import Callable
from functools import wraps
from typing import Concatenate

from pyspecification.predicate import Predicate, ReturnType, object_rule
from pyspecification.registry.exceptions import RuleAlreadyRegisteredError, RuleNotRegisteredError
from pyspecification.registry.processors import ProcessFn, process_arguments, process_rule_name

type RuleDefinitionFn[T, R: ReturnType, **P] = Callable[Concatenate[T, P], R]
type RuleFn[T, R: ReturnType, **P] = Callable[P, Predicate[T, R]]


class ObjectPredicateRegistry[T, R: ReturnType]:
    def __init__(self) -> None:
        self._rules: dict[str, RuleFn[T, R, ...]] = {}

    @property
    def rules(self) -> dict[str, RuleFn[T, R, ...]]:
        return self._rules

    def __getitem__(self, name: str) -> RuleFn[T, R, ...]:
        if name not in self._rules:
            raise RuleNotRegisteredError(name)
        return self._rules[name]

    def rule[**P](
        self,
        *,
        name: str | None = None,
        args_process_fn: ProcessFn | None = None,
        kwargs_process_fns: tuple[dict[str, ProcessFn], ProcessFn] | None = None,
    ) -> Callable[[RuleDefinitionFn[T, R, P]], RuleFn[T, R, P]]:
        def decorator(fn: RuleDefinitionFn[T, R, P]) -> RuleFn[T, R, P]:
            return self._register_rule(
                fn,
                name=name,
                args_process_fn=args_process_fn,
                kwargs_process_fns=kwargs_process_fns,
            )

        return decorator

    def register_rule[**P](
        self,
        fn: RuleDefinitionFn[T, R, P],
        *,
        name: str | None = None,
        args_process_fn: ProcessFn | None = None,
        kwargs_process_fns: tuple[dict[str, ProcessFn], ProcessFn] | None = None,
    ) -> RuleFn[T, R, P]:
        return self._register_rule(
            fn,
            name=name,
            args_process_fn=args_process_fn,
            kwargs_process_fns=kwargs_process_fns,
        )

    def _register_rule[**P](
        self,
        fn: RuleDefinitionFn[T, R, P],
        *,
        name: str | None = None,
        args_process_fn: ProcessFn | None = None,
        kwargs_process_fns: tuple[dict[str, ProcessFn], ProcessFn] | None = None,
    ) -> RuleFn[T, R, P]:
        rule_name = process_rule_name(fn, name)

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
