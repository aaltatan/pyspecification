from collections.abc import Callable
from typing import Any

type ProcessFn = Callable[[Any], Any]


def process[T](value: T | list[T], processor: ProcessFn) -> T | list[T]:
    return [processor(v) for v in value] if isinstance(value, list) else processor(value)


def process_args(processor: ProcessFn, *args: Any) -> tuple[Any, ...]:
    return tuple(process(arg, processor) for arg in args)


def process_kwargs(
    processors: dict[str, ProcessFn],
    fallback_processor: ProcessFn,
    **kwargs: Any,
) -> dict[str, Any]:
    processed_kwargs = {}

    for key, kwarg in kwargs.items():
        process_fn = processors.get(key, fallback_processor)
        processed_kwargs[key] = process(kwarg, process_fn)

    return processed_kwargs
