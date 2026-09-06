from collections.abc import Callable
from inspect import get_annotations
from typing import Any

from pydantic import TypeAdapter


def get_json_schema(rule: Callable[..., Any]) -> dict[str, Any]:
    """Get the JSON schema for a rule.

    Args:
        rule (Callable): The rule to get the JSON schema for.

    Returns:
        dict[str, Any]: The JSON schema for the rule.

    Example:
    ```python
    from pyspecification import get_json_schema, object_rule


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
        schema = get_json_schema(is_admin)
        print(schema)
        # {"return": {"type": "boolean"}}

        schema = get_json_schema(name__istartswith)
        print(schema)
        # {"value": {"type": "string"}, "return": {"type": "boolean"}}

        schema = get_json_schema(age__between)
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
    return {
        arg: TypeAdapter(typ).json_schema()
        for idx, (arg, typ) in enumerate(get_annotations(rule).items())
        if idx > 0
    }
