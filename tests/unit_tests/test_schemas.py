from typing import Any

import pytest
from pyspecification.schemas import (
    ExpressionsWrapperSchema,
    PredicateSchema,
    RuleSchema,
)


@pytest.mark.parametrize(
    "predicate_data",
    [
        {"name": "_is_true", "args": [], "kwargs": {}, "inverse": False},
        {"name": "is_true", "args": [], "kwargs": {}, "inverse": False},
        {"name": "say_hello", "args": ["Abdullah"], "kwargs": {}, "inverse": False},
        {"name": "say_hello", "args": ["Abdullah"], "kwargs": {}, "inverse": True},
        {"name": "say_hello", "args": [{"value": "Abdullah"}], "kwargs": {}, "inverse": True},
        {"name": "say_hello", "args": [], "kwargs": {"value": "Abdullah"}, "inverse": True},
    ],
)
def test_predicate_schema(predicate_data: dict[str, Any]) -> None:
    predicate = PredicateSchema(**predicate_data)

    assert predicate.name == predicate_data["name"]
    assert predicate.args == predicate_data["args"]
    assert predicate.kwargs == predicate_data["kwargs"]
    assert predicate.inverse == predicate_data["inverse"]


@pytest.mark.parametrize(
    "predicate, dumped",
    (
        [
            (
                {
                    "operator": "all",
                    "inverse": False,
                    "expressions": [
                        {"name": "name__len_le", "args": [10], "kwargs": {}, "inverse": False},
                        {"name": "name__len_le", "args": [10], "kwargs": {}, "inverse": True},
                        {
                            "name": "name__contains",
                            "args": ["Abdullah"],
                            "kwargs": {},
                            "inverse": False,
                        },
                    ],
                },
                {
                    "operator": "all",
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
    assert RuleSchema(**predicate).model_dump() == dumped


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
                "operator": "all",
                "inverse": False,
                "expressions": [
                    {"name": "name__len_le", "args": [10], "kwargs": {}, "inverse": False},
                    {
                        "name": "name__contains",
                        "args": ["Abdullah"],
                        "kwargs": {},
                        "inverse": False,
                    },
                    {
                        "name": "name__startswith",
                        "args": [],
                        "kwargs": {"value": "Abdullah"},
                        "inverse": False,
                    },
                    {
                        "operator": "all",
                        "inverse": False,
                        "expressions": [
                            {"name": "age__gt", "args": [18], "kwargs": {}, "inverse": False},
                            {"name": "is_admin", "args": [True], "kwargs": {}, "inverse": False},
                        ],
                    },
                    {
                        "operator": "any",
                        "inverse": True,
                        "expressions": [
                            {"name": "age__gt", "args": [18], "kwargs": {}, "inverse": False},
                            {"name": "is_admin", "args": [True], "kwargs": {}, "inverse": False},
                        ],
                    },
                ],
            },
            RuleSchema(
                root=ExpressionsWrapperSchema(
                    operator="all",
                    inverse=False,
                    expressions=[
                        PredicateSchema(name="name__len_le", args=[10], kwargs={}, inverse=False),
                        PredicateSchema(
                            name="name__contains", args=["Abdullah"], kwargs={}, inverse=False
                        ),
                        PredicateSchema(
                            name="name__startswith",
                            args=[],
                            kwargs={"value": "Abdullah"},
                            inverse=False,
                        ),
                        ExpressionsWrapperSchema(
                            operator="all",
                            inverse=False,
                            expressions=[
                                PredicateSchema(
                                    name="age__gt", args=[18], kwargs={}, inverse=False
                                ),
                                PredicateSchema(
                                    name="is_admin", args=[True], kwargs={}, inverse=False
                                ),
                            ],
                        ),
                        ExpressionsWrapperSchema(
                            operator="any",
                            inverse=True,
                            expressions=[
                                PredicateSchema(
                                    name="age__gt", args=[18], kwargs={}, inverse=False
                                ),
                                PredicateSchema(
                                    name="is_admin", args=[True], kwargs={}, inverse=False
                                ),
                            ],
                        ),
                    ],
                )
            ),
        )
    ],
)
def test_expression_schema(expression_dict: dict[str, Any], schema: RuleSchema) -> None:
    assert RuleSchema(**expression_dict) == schema
