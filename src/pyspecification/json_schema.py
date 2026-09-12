from collections.abc import Callable
from datetime import date, datetime, time
from inspect import get_annotations, signature
from types import UnionType
from typing import Any, Literal, Union, get_args, get_origin, is_typeddict
from uuid import UUID


def get_json_schema(annotation: Any) -> dict[str, Any]:
    if is_typeddict(annotation):
        annotations = get_annotations(annotation)
        return {
            "type": "object",
            "properties": {name: get_json_schema(typ) for name, typ in annotations.items()},
            "required": [name for name in annotations if name in annotation.__required_keys__],
        }

    origin = get_origin(annotation)

    if origin is Literal:
        values = list(get_args(annotation))
        schema: dict[str, Any] = {"enum": values}
        if values and all(isinstance(value, str) for value in values):
            schema["type"] = "string"
        return schema

    if origin in (Union, UnionType):
        return {"anyOf": [get_json_schema(arg) for arg in get_args(annotation)]}

    if origin is not None or annotation in (list, set, frozenset, tuple, dict):
        origin = annotation if origin is None else origin
        if origin in (list, set, frozenset, tuple):
            args = get_args(annotation)
            item_schema = get_json_schema(args[0]) if args else {}
            return {"type": "array", "items": item_schema}
        if origin is dict:
            args = get_args(annotation)
            value_schema = get_json_schema(args[1]) if len(args) > 1 else {}
            return {"type": "object", "additionalProperties": value_schema}

    schemas = {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
        None: {"type": "null"},
        type(None): {"type": "null"},
        datetime: {"type": "string", "format": "date-time"},
        date: {"type": "string", "format": "date"},
        time: {"type": "string", "format": "time"},
        UUID: {"type": "string", "format": "uuid"},
        Any: {},
    }
    return schemas.get(annotation, {})


def get_rule_json_schema(rule: Callable[..., Any]) -> dict[str, Any]:
    """Get the JSON schema for a rule.

    Args:
        rule (Callable): The rule to get the JSON schema for.

    Returns:
        dict[str, Any]: The JSON schema for the rule.

    Example:
    ```python
    from pyspecification import get_rule_json_schema, object_rule


    @object_rule()
    def is_admin(user: User) -> bool:
        return user.is_admin


    @object_rule()
    def name__istartswith(user: User, value: str) -> bool:
        return user.name.lower().startswith(value.lower())


    @object_rule()
    def age__between(user: User, min_age: int, max_age: int) -> bool:
        return user.age >= min_age and user.age <= max_age


    def main() -> None:
        schema = get_rule_json_schema(is_admin)
        print(schema)
        # {"return": {"type": "boolean"}}

        schema = get_rule_json_schema(name__istartswith)
        print(schema)
        # {"value": {"type": "string"}, "return": {"type": "boolean"}}

        schema = get_rule_json_schema(age__between)
        print(schema)
        # {
        #     "min_age": {"type": "integer"},
        #     "max_age": {"type": "integer"},
        #     "return": {"type": "boolean"},
        # }


    if __name__ == "__main__":
        main()
    ```

    """
    annotations = get_annotations(rule)
    parameters = list(signature(rule).parameters)
    schema: dict[str, Any] = {}

    for index, name in enumerate(parameters):
        if index == 0:
            continue
        schema[name] = get_json_schema(annotations.get(name, Any))

    if "return" in annotations:
        schema["return"] = get_json_schema(annotations["return"])

    return schema
