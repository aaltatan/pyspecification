from collections.abc import Callable
from typing import Any

from .exceptions import ProcessArgumentError

type ProcessFn = Callable[[Any], Any]


DEFAULT_PROCESSORS: tuple[ProcessFn, dict[str, ProcessFn]] = (lambda value: value, {})


def process_arguments(
    processors: tuple[ProcessFn, dict[str, ProcessFn]],
    *args: Any,
    **kwargs: Any,
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    default_fn, processors_map = processors

    processed_args = []
    current_arg = None

    try:
        for arg in args:
            current_arg = arg
            processed_args.append(default_fn(arg))
    except Exception as e:
        msg = f"Argument '{current_arg}' failed to process, {e}"
        raise ProcessArgumentError(msg) from e

    processed_kwargs = {}
    current_key, current_value = None, None

    try:
        for key, value in kwargs.items():
            current_key, current_value = key, value
            processed_kwargs[key] = processors_map.get(key, default_fn)(value)
    except Exception as e:
        msg = (
            f"Keyword argument '{current_key}' with value '{current_value}' failed to process, {e}"
        )
        raise ProcessArgumentError(msg) from e

    return tuple(processed_args), processed_kwargs
