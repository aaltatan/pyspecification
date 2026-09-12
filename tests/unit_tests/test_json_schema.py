from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any, Literal, TypedDict
from uuid import UUID

import pytest
from pyspecification import (
    ExpressionWrapperDict,
    Predicate,
    PredicateCompiler,
    PredicateDict,
    get_rule_json_schema,
    object_rule,
)
from pyspecification.json_schema import get_json_schema


@dataclass
class User:
    name: str
    age: int
    is_admin: bool = True


@object_rule()
def name__istartswith(user: User, value: str) -> bool: ...


def test_get_rule_json_schema() -> None:
    schema = get_rule_json_schema(name__istartswith)

    assert "user" not in schema
    assert "value" in schema
    assert "return" in schema

    assert schema["value"]["type"] == "string"
    assert schema["return"]["type"] == "boolean"


@pytest.mark.parametrize(
    ("annotation", "expected"),
    [
        (str, {"type": "string"}),
        (int, {"type": "integer"}),
        (float, {"type": "number"}),
        (bool, {"type": "boolean"}),
        (None, {"type": "null"}),
        (Any, {}),
        (datetime, {"type": "string", "format": "date-time"}),
        (date, {"type": "string", "format": "date"}),
        (time, {"type": "string", "format": "time"}),
        (UUID, {"type": "string", "format": "uuid"}),
        (bytes, {}),
        (object, {}),
    ],
)
def test_get_json_schema_for_scalar_annotations(annotation: Any, expected: dict[str, Any]) -> None:

    assert get_json_schema(annotation) == expected


@pytest.mark.parametrize(
    ("annotation", "expected"),
    [
        (list[str], {"type": "array", "items": {"type": "string"}}),
        (set[int], {"type": "array", "items": {"type": "integer"}}),
        (tuple[bool, ...], {"type": "array", "items": {"type": "boolean"}}),
        (list, {"type": "array", "items": {}}),
        (dict[str, int], {"type": "object", "additionalProperties": {"type": "integer"}}),
        (dict, {"type": "object", "additionalProperties": {}}),
    ],
)
def test_get_json_schema_for_container_annotations(
    annotation: Any, expected: dict[str, Any]
) -> None:

    assert get_json_schema(annotation) == expected


@pytest.mark.parametrize(
    ("annotation", "expected"),
    [
        (Literal["active", "pending"], {"enum": ["active", "pending"], "type": "string"}),
        (Literal[1, 2], {"enum": [1, 2]}),
        (str | None, {"anyOf": [{"type": "string"}, {"type": "null"}]}),
        (int | str, {"anyOf": [{"type": "integer"}, {"type": "string"}]}),
    ],
)
def test_get_json_schema_for_literal_and_union_annotations(
    annotation: Any, expected: dict[str, Any]
) -> None:

    assert get_json_schema(annotation) == expected


def test_get_json_schema_for_empty_literal() -> None:

    assert get_json_schema(Literal[()]) == {"enum": []}


class ExamplePayload(TypedDict):
    name: str
    age: int


def test_get_json_schema_for_typed_dict() -> None:

    assert get_json_schema(ExamplePayload) == {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
    }


def test_get_rule_json_schema_excludes_object_argument() -> None:
    @object_rule()
    def rule(_: ExamplePayload, value: int, label: str) -> bool:
        return value > 0 and bool(label)

    assert get_rule_json_schema(rule) == {
        "value": {"type": "integer"},
        "label": {"type": "string"},
        "return": {"type": "boolean"},
    }


def test_get_rule_json_schema_preserves_annotation_order() -> None:
    def rule(_: object, first: str, second: int) -> bool:
        return bool(first) and second > 0

    assert list(get_rule_json_schema(rule)) == ["first", "second", "return"]


def test_get_rule_json_schema_for_unannotated_rule() -> None:
    def rule(_: object, value) -> bool:  # type: ignore[no-untyped-def]  # noqa: ANN001
        return bool(value)

    assert get_rule_json_schema(rule) == {"value": {}, "return": {"type": "boolean"}}


def test_get_rule_json_schema_for_rule_without_parameters() -> None:
    def rule() -> bool:
        return True

    assert get_rule_json_schema(rule) == {"return": {"type": "boolean"}}


def test_compiler_error_message_includes_predicate_schema() -> None:
    compiler = PredicateCompiler[object, bool](
        {}, lambda _: Predicate(lambda _: True, operator="logical")
    )

    with pytest.raises(TypeError, match="Predicate:") as error:
        compiler.compile({"name": "broken"})  # type: ignore[arg-type]

    assert '"name"' in str(error.value)
    assert '"inverse"' in str(error.value)


def test_compiler_error_message_includes_wrapper_schema() -> None:
    compiler = PredicateCompiler[object, bool](
        {}, lambda _: Predicate(lambda _: True, operator="logical")
    )

    with pytest.raises(TypeError, match="Expression wrapper:") as error:
        compiler.compile({"operator": "all"})  # type: ignore[arg-type]

    assert '"expressions"' in str(error.value)


def test_compiler_error_message_includes_received_expression() -> None:
    compiler = PredicateCompiler[object, bool](
        {}, lambda _: Predicate(lambda _: True, operator="logical")
    )

    with pytest.raises(TypeError, match="Received:") as error:
        compiler.compile({"unexpected": True})  # type: ignore[arg-type]

    assert "unexpected" in str(error.value)


def test_compiler_error_message_includes_nested_path() -> None:
    compiler = PredicateCompiler[object, bool](
        {}, lambda _: Predicate(lambda _: True, operator="logical")
    )
    expression = {"operator": "all", "expressions": [{"unexpected": True}]}

    with pytest.raises(TypeError, match=r"\$\.expressions\[0\]"):
        compiler.compile(expression)  # type: ignore[arg-type]


def test_predicate_typed_dict_schema_has_all_fields() -> None:

    schema = get_json_schema(PredicateDict)

    assert schema["type"] == "object"
    assert set(schema["properties"]) == {"name", "args", "kwargs", "inverse"}


def test_wrapper_typed_dict_schema_has_all_fields() -> None:

    schema = get_json_schema(ExpressionWrapperDict)

    assert schema["type"] == "object"
    assert set(schema["properties"]) == {"operator", "expressions"}
