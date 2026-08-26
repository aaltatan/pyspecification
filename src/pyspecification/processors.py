from collections.abc import Callable
from typing import Any

type ProcessFn = Callable[[Any], Any]


DEFAULT_PROCESSORS: tuple[ProcessFn, dict[str, ProcessFn]] = (lambda value: value, {})


def process_arguments(
    processors: tuple[ProcessFn, dict[str, ProcessFn]],
    *args: Any,
    **kwargs: Any,
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    default_fn, processors_map = processors

    return tuple(default_fn(arg) for arg in args), {
        key: processors_map.get(key, default_fn)(value) for key, value in kwargs.items()
    }
