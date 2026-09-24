"""Argument processors: transform raw rule arguments before a rule is built.

Processors are most useful when rules come from JSON, where every value is a
string, number, boolean, list, dict or null. They turn those raw values into
the rich objects your rule functions expect (dates, enums, decimals, ...).

The `processors` option of a registry accepts:

- `None`: arguments are passed through untouched (the default).
- a callable: applied to every argument.
- a mapping from parameter name to callable: applied to those arguments only.
  The key `...` (Ellipsis) means "every argument not named here".

    processors=float
    processors={"value": float}
    processors={"min_age": int, ...: str.strip}

A processor for a parameter applies whether the value was passed positionally
or by keyword. For `*args` it applies to each item, and for `**kwargs` each
extra keyword name is looked up individually. The object under test and, for
subscriptable rules, the key are not arguments and are never processed.
"""

from collections.abc import Callable, Mapping
from inspect import BoundArguments, Parameter
from types import EllipsisType
from typing import Any

from .exceptions import InvalidProcessorsError, ProcessArgumentError


def processor_lookup(
    processors: Callable[[Any], Any] | Mapping[str | EllipsisType, Callable[[Any], Any]],
    parameters: Mapping[str, Parameter],
    rule_name: str,
) -> Callable[[str], Callable[[Any], Any] | None]:
    """Validate a `processors` option and turn it into a name-to-processor lookup.

    Mapping keys are checked against `parameters`, so a typo fails at
    registration instead of silently never running. Rules accepting `**kwargs`
    allow any key.

    Raises:
        InvalidProcessorsError: If the option has the wrong type, a processor is
            not callable, or a key names no parameter.

    Example:
    ```python
    >>> from inspect import signature
    >>> parameters = signature(lambda min_age, max_age: None).parameters
    >>> lookup = processor_lookup({"min_age": int, ...: str.strip}, parameters, "age__between")
    >>> lookup("min_age"), lookup("max_age")
    (<class 'int'>, <method 'strip' of 'str' objects>)
    >>> lookup = processor_lookup({"min_age": int}, parameters, "age__between")
    >>> lookup("max_age") is None
    True
    >>> processor_lookup({"min": int}, parameters, "age__between")
    Traceback (most recent call last):
    ...
    pyspecification.exceptions.InvalidProcessorsError: Processors of rule 'age__between' name unknown parameters ['min'], available parameters: min_age, max_age

    ```

    """  # noqa: E501
    if isinstance(processors, Mapping):
        _validate_mapping(processors, parameters, rule_name)
        rest = processors.get(...)
        return lambda name: processors.get(name, rest)

    if callable(processors):
        return lambda _: processors

    msg = (
        f"Processors of rule '{rule_name}' must be a callable or a mapping of "
        f"parameter names to callables, got {processors!r}"
    )
    raise InvalidProcessorsError(msg)


def process_arguments(
    lookup: Callable[[str], Callable[[Any], Any] | None], bound: BoundArguments
) -> BoundArguments:
    """Return new bound arguments with every value run through its processor.

    Values without a processor are kept as they are, and the original `bound`
    object is left untouched.

    Raises:
        ProcessArgumentError: If any processor raises; the original exception is chained.

    Example:
    ```python
    >>> from inspect import signature
    >>> def between(low: int, *extras: str, **options: str): ...
    >>> bound = signature(between).bind("2", " a ", " b ", mode="L", note=" hot ")
    >>> lookup = {"low": int, "extras": str.strip, "mode": str.lower}.get
    >>> process_arguments(lookup, bound).arguments
    {'low': 2, 'extras': ('a', 'b'), 'options': {'mode': 'l', 'note': ' hot '}}

    ```

    """
    parameters = bound.signature.parameters
    processed = {
        name: _process_parameter(lookup, parameters[name], value)
        for name, value in bound.arguments.items()
    }
    return BoundArguments(bound.signature, processed)  # type: ignore[arg-type]


def _validate_mapping(
    processors: Mapping[Any, Any],
    parameters: Mapping[str, Parameter],
    rule_name: str,
) -> None:
    if not_callable := sorted(str(key) for key, fn in processors.items() if not callable(fn)):
        msg = f"Processors of rule '{rule_name}' must be callables, not for {not_callable}"
        raise InvalidProcessorsError(msg)

    if any(parameter.kind is Parameter.VAR_KEYWORD for parameter in parameters.values()):
        return

    if unknown := sorted(map(str, processors.keys() - parameters.keys() - {...})):
        msg = (
            f"Processors of rule '{rule_name}' name unknown parameters {unknown}, "
            f"available parameters: {', '.join(parameters) or '(none)'}"
        )
        raise InvalidProcessorsError(msg)


def _process_parameter(
    lookup: Callable[[str], Callable[[Any], Any] | None], parameter: Parameter, value: Any
) -> Any:
    match parameter.kind:
        case Parameter.VAR_POSITIONAL:
            return tuple(_process_value(lookup, parameter.name, item) for item in value)
        case Parameter.VAR_KEYWORD:
            return {key: _process_value(lookup, key, item) for key, item in value.items()}
        case _:
            return _process_value(lookup, parameter.name, value)


def _process_value(
    lookup: Callable[[str], Callable[[Any], Any] | None], name: str, value: Any
) -> Any:
    process = lookup(name)

    if process is None:
        return value

    try:
        return process(value)
    except Exception as error:
        msg = f"Argument '{name}' with value {value!r} failed to process, {error}"
        raise ProcessArgumentError(msg) from error
