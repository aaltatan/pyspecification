from collections.abc import Callable
from typing import Any

type ProcessFn = Callable[[Any], Any]


DEFAULT_PROCESSORS: tuple[ProcessFn, dict[str, ProcessFn]] = (lambda value: value, {})


def process_arguments(
    processors: tuple[ProcessFn, dict[str, ProcessFn]],
    *args: Any,
    **kwargs: Any,
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    """Process the arguments and kwargs using the provided processors.

    Args:
        processors (tuple[ProcessFn, dict[str, ProcessFn]]): The processors to use.
        *args: The positional arguments to process.
        **kwargs: The keyword arguments to process.

    Returns:
        tuple[tuple[Any, ...], dict[str, Any]]: The processed arguments and kwargs.

    Example:
    ```python
    from pyspecification.processors import ProcessFn, process_arguments


    def process_1(value: str) -> str:
        return value.upper()


    def process_2(value: int) -> int:
        return value * 2


    def main() -> None:
        args, kwargs = process_arguments(
            (process_1, {"value": process_2}),
            "hello",
            value=10,
        )
        print(args)
        # ["HELLO", "HELLO"]
        print(kwargs)
        # {"value": 20}


    if __name__ == "__main__":
        main()
    ```

    """
    default_fn, processors_map = processors

    return tuple(default_fn(arg) for arg in args), {
        key: processors_map.get(key, default_fn)(value) for key, value in kwargs.items()
    }
