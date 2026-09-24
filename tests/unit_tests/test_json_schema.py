import json
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any, Literal, NotRequired, Required, TypedDict
from uuid import UUID

import pytest
from pyspecification import (
    ExpressionWrapperDict,
    ObjectRulesRegistry,
    Predicate,
    PredicateCompiler,
    PredicateDict,
    SubscriptableRulesRegistry,
    get_expression_json_schema,
    get_json_schema,
    get_rule_json_schema,
    object_rule,
    subscriptable_rule,
)
from pyspecification.compilers import EXPRESSION_WRAPPER_DICT_KEYS, PREDICATE_DICT_KEYS
from pyspecification.json_schema import JSON_SCHEMA_DIALECT


@dataclass
class User:
    name: str
    age: int
    is_admin: bool = True


@object_rule()
def name__istartswith(user: User, value: str) -> bool:
    """Whether the name starts with a value."""
    return user.name.startswith(value)


def test_get_rule_json_schema_describes_the_predicate_dictionary() -> None:
    assert get_rule_json_schema("name__istartswith", name__istartswith) == {
        "type": "object",
        "properties": {
            "name": {"const": "name__istartswith"},
            "args": {
                "type": "array",
                "prefixItems": [{"type": "string"}],
                "items": False,
            },
            "kwargs": {
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": [],
                "additionalProperties": False,
            },
            "inverse": {"type": "boolean"},
        },
        "required": ["name", "args", "kwargs", "inverse"],
        "additionalProperties": False,
        "description": "Whether the name starts with a value.",
    }


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


def test_get_json_schema_for_boolean_literal_has_no_string_type() -> None:
    assert get_json_schema(Literal[True, False]) == {"enum": [True, False]}


def test_get_json_schema_for_nested_containers() -> None:

    assert get_json_schema(list[list[int]]) == {
        "type": "array",
        "items": {"type": "array", "items": {"type": "integer"}},
    }


def test_get_json_schema_for_dict_with_non_string_key_ignores_key_type() -> None:
    assert get_json_schema(dict[int, str]) == {
        "type": "object",
        "additionalProperties": {"type": "string"},
    }


def test_get_json_schema_for_empty_tuple_type() -> None:

    assert get_json_schema(tuple[()]) == {"type": "array", "items": {}}


def test_get_json_schema_for_heterogeneous_tuple_only_reflects_first_member() -> None:
    assert get_json_schema(tuple[int, str]) == {
        "type": "array",
        "items": {"type": "integer"},
    }


class ExamplePayload(TypedDict):
    name: str
    age: int


def test_get_json_schema_for_typed_dict() -> None:

    assert get_json_schema(ExamplePayload) == {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
    }


class Flavor(Enum):
    VANILLA = "vanilla"
    MOCHA = "mocha"


class Level(Enum):
    LOW = 1
    HIGH = 2


class Mixed(Enum):
    TEXT = "text"
    NUMBER = 1


class Empty(Enum):
    pass


FLAVOR_SCHEMA = {"enum": ["vanilla", "mocha"], "type": "string"}


@pytest.mark.parametrize(
    ("annotation", "expected"),
    [
        (Decimal, {"type": "number"}),
        (Flavor, FLAVOR_SCHEMA),
        (Level, {"enum": [1, 2]}),
        (Mixed, {"enum": ["text", 1]}),
        (Empty, {"enum": []}),
        (Annotated[int, "metadata"], {"type": "integer"}),
        (Annotated[list[str], "a", "b"], {"type": "array", "items": {"type": "string"}}),
        (Flavor | None, {"anyOf": [FLAVOR_SCHEMA, {"type": "null"}]}),
        (list[Decimal], {"type": "array", "items": {"type": "number"}}),
        (dict[str, Flavor], {"type": "object", "additionalProperties": FLAVOR_SCHEMA}),
    ],
)
def test_get_json_schema_for_enum_decimal_and_annotated(
    annotation: Any, expected: dict[str, Any]
) -> None:

    assert get_json_schema(annotation) == expected


type Age = int
type MaybeAge = Age | None
type AgeList = list[Age]


def test_get_json_schema_resolves_type_aliases() -> None:

    assert get_json_schema(Age) == {"type": "integer"}
    assert get_json_schema(MaybeAge) == {"anyOf": [{"type": "integer"}, {"type": "null"}]}
    assert get_json_schema(AgeList) == {"type": "array", "items": {"type": "integer"}}


class OptionalFields(TypedDict, total=False):
    required_field: Required[str]
    optional_field: int


class WithNotRequired(TypedDict):
    always: str
    sometimes: NotRequired[int]


class Nested(TypedDict):
    payload: WithNotRequired
    tags: list[str]


def test_get_json_schema_for_typed_dict_required_and_not_required_markers() -> None:

    assert get_json_schema(OptionalFields) == {
        "type": "object",
        "properties": {
            "required_field": {"type": "string"},
            "optional_field": {"type": "integer"},
        },
        "required": ["required_field"],
    }
    assert get_json_schema(WithNotRequired)["required"] == ["always"]
    assert get_json_schema(WithNotRequired)["properties"]["sometimes"] == {"type": "integer"}


def test_get_json_schema_for_nested_typed_dict() -> None:

    assert get_json_schema(Nested) == {
        "type": "object",
        "properties": {
            "payload": get_json_schema(WithNotRequired),
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["payload", "tags"],
    }


def test_get_json_schema_returns_an_independent_copy() -> None:
    first = get_json_schema(int)
    first["default"] = 1

    assert get_json_schema(int) == {"type": "integer"}


def args_of(schema: dict[str, Any]) -> dict[str, Any]:
    return schema["properties"]["args"]


def kwargs_of(schema: dict[str, Any]) -> dict[str, Any]:
    return schema["properties"]["kwargs"]


def test_get_rule_json_schema_excludes_object_argument() -> None:
    @object_rule()
    def rule(payload: ExamplePayload, value: int, label: str) -> bool:
        return value > 0 and bool(label) and bool(payload)

    schema = get_rule_json_schema("rule", rule)

    assert args_of(schema)["prefixItems"] == [{"type": "integer"}, {"type": "string"}]
    assert list(kwargs_of(schema)["properties"]) == ["value", "label"]


def test_get_rule_json_schema_preserves_parameter_order() -> None:
    @object_rule()
    def rule(_: object, first: str, second: int, third: bool) -> bool:  # noqa: FBT001
        return bool(first) and second > 0 and third

    schema = get_rule_json_schema("rule", rule)

    assert list(kwargs_of(schema)["properties"]) == ["first", "second", "third"]


def test_get_rule_json_schema_for_unannotated_rule() -> None:
    @object_rule()
    def rule(_: object, value) -> bool:  # type: ignore[no-untyped-def]  # noqa: ANN001
        return bool(value)

    assert args_of(get_rule_json_schema("rule", rule))["prefixItems"] == [{}]


def test_get_rule_json_schema_for_rule_without_parameters() -> None:
    @object_rule()
    def rule(_: object) -> bool:
        return True

    schema = get_rule_json_schema("rule", rule)

    assert args_of(schema) == {"type": "array", "prefixItems": [], "items": False}
    assert kwargs_of(schema) == {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }


def test_get_rule_json_schema_without_docstring_has_no_description() -> None:
    @object_rule()
    def rule(_: object) -> bool:
        return True

    assert "description" not in get_rule_json_schema("rule", rule)


def test_get_rule_json_schema_includes_json_defaults_only() -> None:
    @object_rule()
    def rule(
        _: object,
        limit: int = 10,
        ratio: Decimal = Decimal(1),
        tag: str | None = None,
    ) -> bool:
        return True

    prefix_items = args_of(get_rule_json_schema("rule", rule))["prefixItems"]

    assert prefix_items[0] == {"type": "integer", "default": 10}
    assert prefix_items[1] == {"type": "number"}
    assert prefix_items[2] == {"anyOf": [{"type": "string"}, {"type": "null"}], "default": None}


def test_get_rule_json_schema_positional_only_and_keyword_only_parameters() -> None:
    @object_rule()
    def rule(_: object, first: int, /, second: int, *, third: int, fourth: int = 4) -> bool:
        return True

    schema = get_rule_json_schema("rule", rule)

    assert len(args_of(schema)["prefixItems"]) == 2
    assert list(kwargs_of(schema)["properties"]) == ["second", "third", "fourth"]
    assert kwargs_of(schema)["required"] == ["third"]


def test_get_rule_json_schema_var_positional_and_var_keyword() -> None:
    @object_rule()
    def rule(_: object, *ages: int, **labels: str) -> bool:
        return True

    schema = get_rule_json_schema("rule", rule)

    assert args_of(schema)["items"] == {"type": "integer"}
    assert kwargs_of(schema)["additionalProperties"] == {"type": "string"}


def test_get_rule_json_schema_resolves_string_annotations() -> None:
    @object_rule()
    def rule(_: object, value: "int") -> bool:
        return True

    assert args_of(get_rule_json_schema("rule", rule))["prefixItems"] == [{"type": "integer"}]


def test_get_rule_json_schema_unresolvable_string_annotation_accepts_anything() -> None:
    @object_rule()
    def rule(_: object, value: "DoesNotExist") -> bool:  # type: ignore[name-defined]  # noqa: F821
        return True

    assert args_of(get_rule_json_schema("rule", rule))["prefixItems"] == [{}]


def test_get_rule_json_schema_of_subscriptable_rule_starts_with_the_key() -> None:
    @subscriptable_rule()
    def is_age(obj: dict[str, Any], key: str, age: int) -> bool:
        return obj[key] == age

    schema = get_rule_json_schema("is_age", is_age)

    assert args_of(schema)["prefixItems"] == [{"type": "string"}, {"type": "integer"}]
    assert list(kwargs_of(schema)["properties"]) == ["key", "age"]


def test_get_rule_json_schema_of_registered_rules() -> None:
    obj_registry = ObjectRulesRegistry[User, bool](operator="logical")
    sub_registry = SubscriptableRulesRegistry[dict[str, Any], str, bool](operator="logical")

    @obj_registry.rule(processors={"value": str})
    def name__eq(user: User, value: str) -> bool:
        """Name equals."""
        return user.name == value

    @sub_registry.rule()
    def is_age(obj: dict[str, Any], key: str, age: int) -> bool:
        return obj[key] == age

    obj_schema = get_rule_json_schema("name__eq", obj_registry["name__eq"])
    sub_schema = get_rule_json_schema("is_age", sub_registry["is_age"])

    assert args_of(obj_schema)["prefixItems"] == [{"type": "string"}]
    assert obj_schema["description"] == "Name equals."
    assert args_of(sub_schema)["prefixItems"] == [{"type": "string"}, {"type": "integer"}]


def test_rule_schema_keys_match_the_keys_the_compiler_requires() -> None:
    schema = get_rule_json_schema("name__istartswith", name__istartswith)

    assert set(schema["properties"]) == PREDICATE_DICT_KEYS
    assert set(schema["required"]) == PREDICATE_DICT_KEYS
    assert schema["additionalProperties"] is False


# -----------------------
# expression schema
# -----------------------


@object_rule()
def is_admin(user: User) -> bool:
    return user.is_admin


def test_get_expression_json_schema_structure() -> None:
    schema = get_expression_json_schema(
        {"is_admin": is_admin, "name__istartswith": name__istartswith}
    )

    assert schema["$schema"] == JSON_SCHEMA_DIALECT
    assert schema["$ref"] == "#/$defs/expression"

    *rule_schemas, wrapper_ref = schema["$defs"]["expression"]["oneOf"]

    assert [rule["properties"]["name"]["const"] for rule in rule_schemas] == [
        "is_admin",
        "name__istartswith",
    ]
    assert wrapper_ref == {"$ref": "#/$defs/wrapper"}


def test_get_expression_json_schema_wrapper_is_recursive() -> None:
    wrapper = get_expression_json_schema({})["$defs"]["wrapper"]

    assert wrapper["properties"]["operator"] == {"enum": ["all", "any"], "type": "string"}
    assert wrapper["properties"]["expressions"] == {
        "type": "array",
        "items": {"$ref": "#/$defs/expression"},
    }
    assert set(wrapper["required"]) == EXPRESSION_WRAPPER_DICT_KEYS
    assert set(wrapper["properties"]) == EXPRESSION_WRAPPER_DICT_KEYS
    assert wrapper["additionalProperties"] is False


def test_get_expression_json_schema_without_rules_only_accepts_wrappers() -> None:
    schema = get_expression_json_schema({})

    assert schema["$defs"]["expression"]["oneOf"] == [{"$ref": "#/$defs/wrapper"}]


def test_get_expression_json_schema_is_json_serializable() -> None:
    schema = get_expression_json_schema({"is_admin": is_admin})

    assert json.loads(json.dumps(schema)) == schema


def test_get_expression_json_schema_of_registry_skips_hidden_rules() -> None:
    registry = ObjectRulesRegistry[User, bool](operator="logical")

    @registry.rule()
    def visible(user: User) -> bool: ...

    @registry.rule(hidden=True)
    def secret(user: User) -> bool: ...

    schema = get_expression_json_schema(registry.rules)

    names = [
        rule["properties"]["name"]["const"]
        for rule in schema["$defs"]["expression"]["oneOf"][:-1]
    ]
    assert names == ["visible"]


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
