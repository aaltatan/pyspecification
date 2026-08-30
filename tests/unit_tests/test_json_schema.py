from dataclasses import dataclass

from pyspecification import get_json_schema, object_rule


@dataclass
class User:
    name: str
    age: int
    is_admin: bool = True


@object_rule()
def name__istartswith(user: User, value: str) -> bool: ...


def test_get_json_schema() -> None:
    schema = get_json_schema(name__istartswith)

    assert "user" not in schema
    assert "value" in schema
    assert "return" in schema

    assert schema["value"]["type"] == "string"
    assert schema["return"]["type"] == "boolean"
