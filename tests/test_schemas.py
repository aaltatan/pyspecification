from typing import Any

import pytest
from pyspecification.schemas import (
    ExpressionSchema,
    ExpressionsWrapperSchema,
    PredicateSchema,
    SimplePredicateSchema,
)


@pytest.mark.parametrize(
    "simple_predicate_data, predicate_data",
    [
        (
            {"_is_true": None},
            {"name": "_is_true", "args": [], "kwargs": {}, "inverse": False},
        ),
        (
            {"is_true": None},
            {"name": "is_true", "args": [], "kwargs": {}, "inverse": False},
        ),
        (
            {"is_true": []},
            {"name": "is_true", "args": [], "kwargs": {}, "inverse": False},
        ),
        (
            {"is_true": {}},
            {"name": "is_true", "args": [], "kwargs": {}, "inverse": False},
        ),
        (
            {"say_hello": "Abdullah"},
            {"name": "say_hello", "args": ["Abdullah"], "kwargs": {}, "inverse": False},
        ),
        (
            {"-say_hello": "Abdullah"},
            {"name": "say_hello", "args": ["Abdullah"], "kwargs": {}, "inverse": True},
        ),
        (
            {"-say_hello": ["Abdullah"]},
            {"name": "say_hello", "args": ["Abdullah"], "kwargs": {}, "inverse": True},
        ),
        (
            {"-say_hello": [{"value": "Abdullah"}]},
            {"name": "say_hello", "args": [{"value": "Abdullah"}], "kwargs": {}, "inverse": True},
        ),
        (
            {"-say_hello": {"value": "Abdullah"}},
            {"name": "say_hello", "args": [], "kwargs": {"value": "Abdullah"}, "inverse": True},
        ),
    ],
)
def test_predicate_schema(
    simple_predicate_data: dict[str, Any], predicate_data: dict[str, Any]
) -> None:
    simple_predicate = SimplePredicateSchema(simple_predicate_data)
    predicate = PredicateSchema(**predicate_data)

    assert simple_predicate.name == predicate.name == predicate_data["name"]
    assert simple_predicate.args == predicate.args == predicate_data["args"]
    assert simple_predicate.kwargs == predicate.kwargs == predicate_data["kwargs"]
    assert simple_predicate.inverse == predicate.inverse == predicate_data["inverse"]


@pytest.mark.parametrize(
    "predicate, dumped",
    (
        [
            (
                {
                    "expressions": [
                        {"name__len_le": 10},
                        {"-name__len_le": 10},
                        {"name": "name__contains", "args": ["Abdullah"]},
                    ]
                },
                {
                    "operator": "and",
                    "inverse": False,
                    "expressions": [
                        {
                            "name": "name__len_le",
                            "inverse": False,
                            "args": [10],
                            "kwargs": {},
                        },
                        {
                            "name": "name__len_le",
                            "inverse": True,
                            "args": [10],
                            "kwargs": {},
                        },
                        {
                            "name": "name__contains",
                            "inverse": False,
                            "args": ["Abdullah"],
                            "kwargs": {},
                        },
                    ],
                },
            )
        ]
    ),
)
def test_expression_schema_serialization(predicate: dict[str, Any], dumped: dict[str, Any]) -> None:
    assert ExpressionSchema(**predicate).model_dump() == dumped


def test_simple_predicate() -> None:
    assert SimplePredicateSchema({"name": "is_true"}).type == "simple"


def test_error_when_simple_predicate_has_multiple_keys() -> None:
    with pytest.raises(ValueError):
        SimplePredicateSchema({"is_admin": True, "name__startswith": "admin"})


@pytest.mark.parametrize(
    "schema_dict",
    [
        {"name": "1is_true"},
        {"name": "is_true*"},
        {"name": "is_*true"},
        {"name": "is true"},
        {"name": "Is True"},
        {"name": "is_true", "kwargs": {"1value": "Abdullah"}},
        {"name": "-is_true", "kwargs": {"value is": "Abdullah"}},
        {"name": "-is_true", "kwargs": {"value is 1": "Abdullah"}},
        {"name": "-is_true", "kwargs": {"value is 1": "Abdullah", "value is 2": "Abdullah"}},
    ],
)
def test_invalid_naming_convention_predicate_schema(schema_dict: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        PredicateSchema(**schema_dict)


@pytest.mark.parametrize(
    "expression_dict, schema",
    [
        (
            {
                "expressions": [
                    {"name__len_le": 10},
                    {"name": "name__contains", "args": ["Abdullah"]},
                    {"name": "name__startswith", "kwargs": {"value": "Abdullah"}},
                    {"age__gt": 18, "is_admin": True},
                    {
                        "operator": "or",
                        "inverse": True,
                        "expressions": [
                            {"name": "age__gt", "args": [18]},
                            {"name": "is_admin", "args": [True]},
                        ],
                    },
                ]
            },
            ExpressionSchema(
                ExpressionsWrapperSchema(
                    expressions=[
                        SimplePredicateSchema({"name__len_le": 10}),
                        PredicateSchema(name="name__contains", args=["Abdullah"]),
                        PredicateSchema(name="name__startswith", kwargs={"value": "Abdullah"}),
                        ExpressionsWrapperSchema(
                            expressions=[
                                SimplePredicateSchema({"age__gt": 18}),
                                SimplePredicateSchema({"is_admin": True}),
                            ]
                        ),
                        ExpressionsWrapperSchema(
                            operator="or",
                            inverse=True,
                            expressions=[
                                PredicateSchema(name="age__gt", args=[18]),
                                PredicateSchema(name="is_admin", args=[True]),
                            ],
                        ),
                    ]
                )
            ),
        )
    ],
)
def test_expression_schema(expression_dict: dict[str, Any], schema: ExpressionSchema) -> None:
    assert ExpressionSchema(**expression_dict) == schema
