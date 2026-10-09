"""Argument parsing: turn the raw values a rule receives into the objects it wants.

Rules often come from JSON or a web form, where every value is a string,
number, boolean, list, dict or null, while rule functions want dates, decimals,
enums, clean text or loaded data. Mark the parameter with `Parse(fn)` inside
`Annotated` and `fn` is applied to the value when the rule is built:

    @object_rule()
    def age__gt(user: User, age: Annotated[int, Parse(int)]) -> bool: ...

    age__gt("18")  # age is 18

Name a parsed type once with a `type` alias and reuse it in many rules:

    type Text = Annotated[str, Parse(str.strip), Parse(str.lower)]
    type Names = Annotated[frozenset[str], Parse(load_names)]  # the JSON passes a path

Parsing happens once, when a rule is built, so a bad value fails before the
predicate runs. Default values are never parsed. The object under test and, for
subscriptable rules, the key are not arguments and cannot be parsed.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import reduce
from inspect import BoundArguments, Parameter, signature
from typing import Any

from .annotations import annotated_metadata, resolved_annotations
from .exceptions import InvalidParserError, ParseArgumentError


@dataclass(frozen=True, slots=True)
class Parse:
    """Mark a rule parameter: apply `fn` to the value passed for it.

    Use it inside `Annotated`, directly or through a `type` alias. Several
    markers on one parameter run left to right. On `*args` the function is
    applied to each item, on `**kwargs` to each value.

    Example:
    ```python
    >>> from typing import Annotated
    >>> from pyspecification import object_rule
    >>> type Text = Annotated[str, Parse(str.strip), Parse(str.lower)]
    >>> @object_rule()
    ... def name__eq(name: str, value: Text, times: Annotated[int, Parse(int)] = 1) -> bool:
    ...     return name == value
    >>> name__eq("  Tea ", "2")("tea")
    True
    >>> name__eq(" Milk")("tea")
    False
    >>> name__eq("tea", "two")
    Traceback (most recent call last):
    ...
    pyspecification.exceptions.ParseArgumentError: Argument 'times' with value 'two' failed to parse...

    ```

    """

    fn: Callable[[Any], Any]

    def __post_init__(self) -> None:
        if not callable(self.fn):
            msg = f"Parse needs a callable, got {self.fn!r}"
            raise InvalidParserError(msg)


def find_parsers(
    fn: Callable[..., Any],
    rule_name: str,
    *,
    skip: int = 1,
) -> dict[str, tuple[Parse, ...]]:
    """Return the `Parse` markers of every parameter of a rule function that has some.

    The first `skip` parameters of `fn` (the object under test, and the key of
    subscriptable rules) are not arguments, so they can carry no marker.

    Raises:
        InvalidParserError: If a marker is used as a default value, or sits on a skipped parameter.

    Example:
    ```python
    >>> from typing import Annotated
    >>> def age__gt(user, age: Annotated[int, Parse(int)] = 18): ...
    >>> find_parsers(age__gt, "age__gt")
    {'age': (Parse(fn=<class 'int'>),)}

    ```

    """
    parameters = signature(fn).parameters
    annotations = resolved_annotations(fn)

    for name, parameter in parameters.items():
        if isinstance(parameter.default, Parse):
            msg = (
                f"Rule '{rule_name}' uses Parse as the default of '{name}'; write it as "
                f"`{name}: Annotated[<type>, Parse(...)]` so the parameter can keep a real default"
            )
            raise InvalidParserError(msg)

    found = {name: _markers(annotations.get(name)) for name in parameters}
    parsers = {name: markers for name, markers in found.items() if markers}

    for name in list(parameters)[:skip]:
        if name in parsers:
            msg = f"Rule '{rule_name}' cannot parse '{name}': it is not an argument of the rule"
            raise InvalidParserError(msg)

    return parsers


def parse_arguments(
    parsers: Mapping[str, tuple[Parse, ...]],
    bound: BoundArguments,
) -> BoundArguments:
    """Return new bound arguments with every marked value parsed.

    Values of unmarked parameters are kept as they are, and the original
    `bound` object is left untouched.

    Raises:
        ParseArgumentError: If a parser raises; the original exception is chained.

    Example:
    ```python
    >>> def between(low: int, *extras: str, **options: str): ...
    >>> bound = signature(between).bind("2", " a ", " b ", mode="L", note="Hot")
    >>> strip, lower = (Parse(str.strip),), (Parse(str.lower),)
    >>> parsers = {"low": (Parse(int),), "extras": strip, "options": lower}
    >>> parse_arguments(parsers, bound).arguments
    {'low': 2, 'extras': ('a', 'b'), 'options': {'mode': 'l', 'note': 'hot'}}

    ```

    """
    parameters = bound.signature.parameters
    parsed = {
        name: _parse_parameter(parsers.get(name, ()), parameters[name], value)
        for name, value in bound.arguments.items()
    }
    return BoundArguments(bound.signature, parsed)  # type: ignore[arg-type]


def input_annotation(parser: Parse) -> Any:
    """Return the annotation of the value `parser` accepts, or `None` if it has none.

    The JSON schema uses it to describe what the JSON must send.

    Example:
    ```python
    >>> def load_names(path: str) -> frozenset[str]: ...
    >>> input_annotation(Parse(load_names))
    <class 'str'>
    >>> input_annotation(Parse(int)) is None
    True

    ```

    """
    try:
        first = next(iter(signature(parser.fn).parameters), None)
    except (TypeError, ValueError):  # builtins without a signature
        return None

    return resolved_annotations(parser.fn).get(first) if first else None


def _markers(annotation: Any) -> tuple[Parse, ...]:
    return tuple(item for item in annotated_metadata(annotation) if isinstance(item, Parse))


def _parse_parameter(markers: tuple[Parse, ...], parameter: Parameter, value: Any) -> Any:
    match parameter.kind:
        case Parameter.VAR_POSITIONAL:
            return tuple(_parse_value(markers, parameter.name, item) for item in value)
        case Parameter.VAR_KEYWORD:
            return {key: _parse_value(markers, key, item) for key, item in value.items()}
        case _:
            return _parse_value(markers, parameter.name, value)


def _parse_value(markers: tuple[Parse, ...], name: str, value: Any) -> Any:
    try:
        return reduce(lambda current, marker: marker.fn(current), markers, value)
    except Exception as error:
        msg = f"Argument '{name}' with value {value!r} failed to parse, {error}"
        raise ParseArgumentError(msg) from error
