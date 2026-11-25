"""Generate JSON Schemas describing rules and whole expressions.

The schemas describe the exact shape accepted by `PredicateCompiler`, so they can
be handed to a form builder, a validator, or an LLM that writes rules as JSON.
"""

from collections.abc import Callable, Mapping
from typing import Any

from pyvocabulary import JSON_SCHEMA_DIALECT, Text, call_json_schema, json_schema_of

__all__ = [
    "JSON_SCHEMA_DIALECT",
    "get_expression_json_schema",
    "get_json_schema",
    "get_rule_json_schema",
]


def get_json_schema(annotation: Any) -> dict[str, Any]:
    """Return the JSON Schema of a Python type annotation.

    Unknown or unannotated types map to `{}`, which accepts any value. A type
    marked with `Process(fn)` is described by what `fn` accepts, because that is
    what the JSON has to send. See `pyvocabulary.json_schema_of`.

    Example:
    ```python
    >>> from typing import Literal
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
    return json_schema_of(annotation)


def get_rule_json_schema(
    name: str,
    rule: Callable[..., Any],
    *,
    label: Text | None = None,
) -> dict[str, Any]:
    """Return the JSON Schema of one predicate dictionary, e.g. `{"name": ..., "args": [...]}`.

    `rule` is a rule factory (as returned by `object_rule`, `subscriptable_rule`
    or a registry), whose signature excludes the object under test. Positional
    parameters are described under `args` (via `prefixItems`), keyword-capable
    parameters under `kwargs`, and the rule docstring becomes the description.

    A `<field>__<operator>` name is split at its last `__` into `x-field` and
    `x-operator`, so editors can offer the field first, then the operator.
    `label` becomes `x-label`; arguments marked with pyvocabulary's `Label` or
    `Choices` carry their `x-label` or `x-choices`.

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
    >>> schema["description"], schema["x-field"], schema["x-operator"]
    ('Whether the age is within a range.', 'age', 'between')

    ```

    """
    schema = call_json_schema(
        name,
        rule,
        extra_properties={"inverse": {"type": "boolean"}},
        required=("name", "args", "kwargs", "inverse"),
        label=label,
    )
    field, _, operator = name.rpartition("__")

    if field and operator:
        schema["x-field"], schema["x-operator"] = field, operator

    return schema


def get_expression_json_schema(
    rules: Mapping[str, Callable[..., Any]],
    *,
    labels: Mapping[str, Text] | None = None,
) -> dict[str, Any]:
    """Return the JSON Schema of a whole expression accepted by `PredicateCompiler.compile`.

    An expression is either a predicate dictionary (one per rule) or a wrapper
    (`{"operator": "all" | "any", "expressions": [...]}`) of nested expressions.
    Pass `registry.rules` (or any name-to-rule mapping given to `PredicateCompiler`),
    and `registry.labels` to label the rules. The root has `x-kind: "predicate"`.

    Raises:
        ValueError: If `labels` names a rule that is not in `rules`.

    Example:
    ```python
    >>> from pyspecification import object_rule
    >>> @object_rule()
    ... def is_admin(user) -> bool:
    ...     return user.is_admin
    >>> schema = get_expression_json_schema({"is_admin": is_admin})
    >>> schema["$ref"], schema["x-kind"], len(schema["$defs"]["expression"]["oneOf"])
    ('#/$defs/expression', 'predicate', 2)

    ```

    """
    labels = labels or {}

    if unknown := sorted(set(labels) - set(rules)):
        msg = f"Labels for unknown rules: {', '.join(unknown)}"
        raise ValueError(msg)

    return {
        "$schema": JSON_SCHEMA_DIALECT,
        "x-kind": "predicate",
        "$defs": {
            "expression": {
                "oneOf": [
                    *(
                        get_rule_json_schema(name, rule, label=labels.get(name))
                        for name, rule in rules.items()
                    ),
                    {"$ref": "#/$defs/wrapper"},
                ],
            },
            "wrapper": {
                "type": "object",
                "properties": {
                    "operator": {"enum": ["all", "any"], "type": "string"},
                    "expressions": {
                        "type": "array",
                        "items": {"$ref": "#/$defs/expression"},
                    },
                },
                "required": ["operator", "expressions"],
                "additionalProperties": False,
            },
        },
        "$ref": "#/$defs/expression",
    }
