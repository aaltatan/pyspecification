from typing import Any

import pytest
from pyspecification.schemas import PredicateSchema, SimplePredicateSchema


@pytest.mark.parametrize(
    "simple_form, data",
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
def test_predicate_schema(simple_form: dict[str, Any], data: dict[str, Any]) -> None:
    simple = SimplePredicateSchema(simple_form)

    assert simple.name == data["name"]
    assert simple.args == data["args"]
    assert simple.kwargs == data["kwargs"]
    assert simple.inverse == data["inverse"]

    regular = PredicateSchema(**data)

    assert regular.name == data["name"]
    assert regular.args == data["args"]
    assert regular.kwargs == data["kwargs"]
    assert regular.inverse == data["inverse"]


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
