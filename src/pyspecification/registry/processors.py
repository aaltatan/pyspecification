from collections.abc import Callable
from typing import Any

from pyspecification.validators import validate_python_vars_fn_naming_convention


def process_rule_name(fn: Callable[..., Any], name: str | None = None) -> str:
    rule_name = name or fn.__name__

    if rule_name.lower() in {"name", "expressions", "operator", "inverse", "args", "kwargs"}:
        msg = f"Rule name '{rule_name}' is reserved"
        raise ValueError(msg)

    validate_python_vars_fn_naming_convention(rule_name)

    return rule_name


type ProcessFn = Callable[[Any], Any]


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
