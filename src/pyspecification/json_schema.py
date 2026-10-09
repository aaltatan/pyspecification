"""Generate JSON Schemas describing rules and whole expressions.

The schemas describe the exact shape accepted by `PredicateCompiler`, so they can
be handed to a form builder, a validator, or an LLM that writes rules as JSON.
"""

from collections.abc import Callable, Mapping
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from inspect import Parameter, get_annotations, signature
from types import NoneType, UnionType
from typing import (
    Annotated,
    Any,
    Literal,
    NotRequired,
    Required,
    TypeAliasType,
    Union,
    get_args,
    get_origin,
    is_typeddict,
)
from uuid import UUID

from .annotations import annotated_metadata, resolved_annotations
from .parsers import Parse, input_annotation

JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"

_SCALAR_SCHEMAS: dict[Any, dict[str, Any]] = {
    str: {"type": "string"},
    int: {"type": "integer"},
    float: {"type": "number"},
    Decimal: {"type": "number"},
    bool: {"type": "boolean"},
    None: {"type": "null"},
    NoneType: {"type": "null"},
    datetime: {"type": "string", "format": "date-time"},
    date: {"type": "string", "format": "date"},
    time: {"type": "string", "format": "time"},
    UUID: {"type": "string", "format": "uuid"},
}

_ARRAY_TYPES = (list, tuple, set, frozenset)
_WRAPPER_ORIGINS = (Annotated, Required, NotRequired)
_POSITIONAL_KINDS = (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD)
_KEYWORD_KINDS = (Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY)


def get_json_schema(annotation: Any) -> dict[str, Any]:
    """Return the JSON Schema of a Python type annotation.

    Unknown or unannotated types map to `{}`, which accepts any value. A type
    marked with `Parse(fn)` is described by what `fn` accepts, because that is
    what the JSON has to send.

    Example:
    ```python
    >>> get_json_schema(int)
    {'type': 'integer'}
    >>> get_json_schema(list[str])
    {'type': 'array', 'items': {'type': 'string'}}
    >>> get_json_schema(Literal["active", "pending"])
    {'enum': ['active', 'pending'], 'type': 'string'}
    >>> get_json_schema(int | None)
    {'anyOf': [{'type': 'integer'}, {'type': 'null'}]}

    ```

    """
    origin = get_origin(annotation)

    if is_typeddict(annotation):
        return _typeddict_schema(annotation)

    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return _enum_schema([member.value for member in annotation])

    if isinstance(annotation, TypeAliasType):
        return get_json_schema(annotation.__value__)

    if origin in _WRAPPER_ORIGINS:
        return get_json_schema(_sent_annotation(annotation))

    if origin is Literal:
        return _enum_schema(list(get_args(annotation)))

    if origin in (Union, UnionType):
        return {"anyOf": [get_json_schema(arg) for arg in get_args(annotation)]}

    if (origin or annotation) in _ARRAY_TYPES:
        return _array_schema(get_args(annotation))

    if (origin or annotation) is dict:
        return _dict_schema(get_args(annotation))

    return dict(_SCALAR_SCHEMAS.get(annotation, {}))


def get_rule_json_schema(name: str, rule: Callable[..., Any]) -> dict[str, Any]:
    """Return the JSON Schema of one predicate dictionary, e.g. `{"name": ..., "args": [...]}`.

    `rule` is a rule factory (as returned by `object_rule`, `subscriptable_rule`
    or a registry), whose signature excludes the object under test. Positional
    parameters are described under `args` (via `prefixItems`), keyword-capable
    parameters under `kwargs`, and the rule docstring becomes the description.

    Example:
    ```python
    >>> from pyspecification import object_rule
    >>> @object_rule()
    ... def age__between(user, min_age: int, max_age: int = 120) -> bool:
    ...     '''Whether the age is within a range.'''
    ...     return min_age <= user.age <= max_age
    >>> schema = get_rule_json_schema("age__between", age__between)
    >>> schema["properties"]["name"]
    {'const': 'age__between'}
    >>> schema["properties"]["args"]["prefixItems"]
    [{'type': 'integer'}, {'type': 'integer', 'default': 120}]
    >>> schema["description"]
    'Whether the age is within a range.'

    ```

    """
    parameters = list(signature(rule).parameters.values())
    annotations = resolved_annotations(rule)

    def parameter_schema(parameter: Parameter) -> dict[str, Any]:
        schema = get_json_schema(annotations.get(parameter.name, Any))
        if parameter.default is not Parameter.empty and _is_json_value(parameter.default):
            schema["default"] = parameter.default
        return schema

    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "name": {"const": name},
            "args": _args_schema(parameters, parameter_schema),
            "kwargs": _kwargs_schema(parameters, parameter_schema),
            "inverse": {"type": "boolean"},
        },
        "required": ["name", "args", "kwargs", "inverse"],
        "additionalProperties": False,
    }

    if rule.__doc__:
        schema["description"] = rule.__doc__.strip()

    return schema


def get_expression_json_schema(rules: Mapping[str, Callable[..., Any]]) -> dict[str, Any]:
    """Return the JSON Schema of a whole expression accepted by `PredicateCompiler.compile`.

    An expression is either a predicate dictionary (one per rule) or a wrapper
    (`{"operator": "all" | "any", "expressions": [...]}`) of nested expressions.
    Pass `registry.rules` (or any name-to-rule mapping given to `PredicateCompiler`).

    Example:
    ```python
    >>> from pyspecification import object_rule
    >>> @object_rule()
    ... def is_admin(user) -> bool:
    ...     return user.is_admin
    >>> schema = get_expression_json_schema({"is_admin": is_admin})
    >>> schema["$ref"], len(schema["$defs"]["expression"]["oneOf"])
    ('#/$defs/expression', 2)

    ```

    """
    return {
        "$schema": JSON_SCHEMA_DIALECT,
        "$defs": {
            "expression": {
                "oneOf": [
                    *(get_rule_json_schema(name, rule) for name, rule in rules.items()),
                    {"$ref": "#/$defs/wrapper"},
                ],
            },
            "wrapper": {
                "type": "object",
                "properties": {
                    "operator": {"enum": ["all", "any"], "type": "string"},
                    "expressions": {"type": "array", "items": {"$ref": "#/$defs/expression"}},
                },
                "required": ["operator", "expressions"],
                "additionalProperties": False,
            },
        },
        "$ref": "#/$defs/expression",
    }


def _args_schema(
    parameters: list[Parameter],
    parameter_schema: Callable[[Parameter], dict[str, Any]],
) -> dict[str, Any]:
    positional = [parameter for parameter in parameters if parameter.kind in _POSITIONAL_KINDS]
    var_positional = next(
        (parameter for parameter in parameters if parameter.kind is Parameter.VAR_POSITIONAL),
        None,
    )
    return {
        "type": "array",
        "prefixItems": [parameter_schema(parameter) for parameter in positional],
        "items": parameter_schema(var_positional) if var_positional else False,
    }


def _kwargs_schema(
    parameters: list[Parameter],
    parameter_schema: Callable[[Parameter], dict[str, Any]],
) -> dict[str, Any]:
    keyword = [parameter for parameter in parameters if parameter.kind in _KEYWORD_KINDS]
    var_keyword = next(
        (parameter for parameter in parameters if parameter.kind is Parameter.VAR_KEYWORD),
        None,
    )
    return {
        "type": "object",
        "properties": {parameter.name: parameter_schema(parameter) for parameter in keyword},
        "required": [
            parameter.name
            for parameter in keyword
            if parameter.kind is Parameter.KEYWORD_ONLY and parameter.default is Parameter.empty
        ],
        "additionalProperties": parameter_schema(var_keyword) if var_keyword else False,
    }


def _enum_schema(values: list[Any]) -> dict[str, Any]:
    schema: dict[str, Any] = {"enum": values}
    if values and all(isinstance(value, str) for value in values):
        schema["type"] = "string"
    return schema


def _array_schema(args: tuple[Any, ...]) -> dict[str, Any]:
    return {"type": "array", "items": get_json_schema(args[0]) if args else {}}


def _dict_schema(args: tuple[Any, ...]) -> dict[str, Any]:
    return {"type": "object", "additionalProperties": get_json_schema(args[1]) if args else {}}


def _typeddict_schema(annotation: Any) -> dict[str, Any]:
    annotations = get_annotations(annotation)
    return {
        "type": "object",
        "properties": {name: get_json_schema(typ) for name, typ in annotations.items()},
        "required": [name for name in annotations if name in annotation.__required_keys__],
    }


def _sent_annotation(annotation: Any) -> Any:
    """Return the type the JSON must send for an `Annotated`/`Required`/`NotRequired` type."""
    parser = next(
        (item for item in annotated_metadata(annotation) if isinstance(item, Parse)), None
    )
    sent = input_annotation(parser) if parser else None
    return get_args(annotation)[0] if sent is None else sent


def _is_json_value(value: Any) -> bool:
    return value is None or isinstance(value, str | int | float | bool | list | dict)
