from collections.abc import Callable, Iterable
from functools import wraps
from typing import Any, Concatenate

from pyspecification.predicate import Predicate, ReturnType
from pyspecification.registry.exceptions import RuleAlreadyRegisteredError, RuleNotRegisteredError
from pyspecification.registry.processors import ProcessFn, process_args, process_kwargs
from pyspecification.registry.schema import get_rules_schema

type RuleDefinitionFn[T: dict, K, R: ReturnType, **P] = Callable[Concatenate[T, K, P], R]
type RuleFn[T: dict, K, R: ReturnType, **P] = Callable[Concatenate[K, P], Predicate[T, R]]


class PredicateKeyError(Exception):
    def __init__(self, key: str) -> None:
        super().__init__(f"Object has no key '{key}'")


class DictPredicateRegistry[T: dict, K, R: ReturnType]:
    def __init__(self) -> None:
        self._rules: dict[str, RuleFn[T, K, R, ...]] = {}

    @property
    def rules_schema(self) -> dict[str, Any]:
        return get_rules_schema(self._rules)

    def __str__(self) -> str:
        return str(self.rules_schema)

    def __repr__(self) -> str:
        return repr(self.rules_schema)

    def __getitem__(self, name: str) -> RuleFn:
        if name not in self._rules:
            raise RuleNotRegisteredError(name)
        return self._rules[name]

    def rule[**P](
        self,
        *,
        name: str | None = None,
        args_process_fn: ProcessFn | None = None,
        kwargs_process_fns: tuple[dict[str, ProcessFn], ProcessFn] | None = None,
    ) -> Callable[[RuleDefinitionFn[T, K, R, P]], RuleFn[T, K, R, P]]:
        def decorator(fn: RuleDefinitionFn[T, K, R, P]) -> RuleFn[T, K, R, P]:
            return self._register_rule(
                fn,
                name=name,
                args_process_fn=args_process_fn,
                kwargs_process_fns=kwargs_process_fns,
            )

        return decorator

    def register_rule[**P](
        self,
        fn: RuleDefinitionFn[T, K, R, P],
        *,
        name: str | None = None,
        args_process_fn: ProcessFn | None = None,
        kwargs_process_fns: tuple[dict[str, ProcessFn], ProcessFn] | None = None,
    ) -> RuleFn[T, K, R, P]:
        return self._register_rule(
            fn,
            name=name,
            args_process_fn=args_process_fn,
            kwargs_process_fns=kwargs_process_fns,
        )

    def register_rules[**P](
        self,
        fns: Iterable[tuple[str, RuleDefinitionFn[T, K, R, P]]],
        *,
        process_fn: ProcessFn | None = None,
    ) -> None:
        for name, fn in fns:
            self._register_rule(
                fn,
                name=name,
                args_process_fn=process_fn,
                kwargs_process_fns=({}, process_fn) if process_fn else None,
            )

    def _register_rule[**P](
        self,
        fn: RuleDefinitionFn[T, K, R, P],
        *,
        name: str | None = None,
        args_process_fn: ProcessFn | None = None,
        kwargs_process_fns: tuple[dict[str, ProcessFn], ProcessFn] | None = None,
    ) -> RuleFn[T, K, R, P]:
        rule_name = name or fn.__name__

        if rule_name in self._rules:
            raise RuleAlreadyRegisteredError(rule_name)

        @wraps(fn)
        def wrapper(key: K, *args: P.args, **kwargs: P.kwargs) -> Predicate[T, R]:
            processed_args = (
                process_args(args_process_fn, *args) if args_process_fn is not None else args
            )

            if kwargs_process_fns is not None:
                process_fns, fallback_process_fn = kwargs_process_fns
                processed_kwargs = process_kwargs(process_fns, fallback_process_fn, **kwargs)
            else:
                processed_kwargs = kwargs

            def predicate_fn(obj: T) -> R:
                if key not in obj:
                    raise PredicateKeyError(str(key))

                return fn(obj, key, *processed_args, **processed_kwargs)

            return Predicate(predicate_fn)

        self._rules[name or fn.__name__] = wrapper

        return wrapper
