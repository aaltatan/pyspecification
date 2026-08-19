from collections.abc import Callable
from typing import Any

import pytest
from pyspecification import ExpressionSchema, Predicate, PredicateCompiler

from .rules import eq, gt, is_true, le, predicates

# -----------------------
# fixtures
# -----------------------


@pytest.fixture
def employee() -> dict[str, Any]:
    return {
        "name": "Abdullah",
        "age": 31,
        "salary": 1000,
        "gender": "male",
        "is_active": True,
    }


@pytest.fixture
def compiler() -> PredicateCompiler:
    return PredicateCompiler(
        rules=predicates.rules,
        initial_predicate_factory=lambda schema: Predicate(
            lambda _: schema.operator == "and",
        ),
    )


@pytest.fixture
def predicate_getter(
    compiler: PredicateCompiler,
) -> Callable[[dict[str, Any]], Predicate[Any, Any]]:
    def inner(rule_dict: dict[str, Any]) -> Predicate[Any, Any]:
        expression = ExpressionSchema(**rule_dict)
        return compiler.compile(expression)

    return inner


# -----------------------
# test cases
# -----------------------


@pytest.mark.parametrize(
    "rule",
    [
        eq("gender", "male") & is_true("is_active"),
        gt("age", 30) & le("salary", 1000),
        gt("age", 30) & le("salary", 1000) & eq("gender", "male") & is_true("is_active"),
        ~is_true("is_active") | (gt("age", 30) & le("salary", 1000) & eq("gender", "male")),
    ],
)
def test_is_true(employee: dict[str, Any], rule: Predicate[dict[str, Any], bool]) -> None:
    assert bool(rule(employee)) is True


@pytest.mark.parametrize(
    "rule_dict",
    [
        {"eq": ["gender", "male"], "is_true": ["is_active"]},
        {"gt": ["age", 30], "le": ["salary", 1000]},
        {
            "gt": ["age", 30],
            "le": ["salary", 1000],
            "eq": ["gender", "male"],
            "is_true": ["is_active"],
        },
        {
            "operator": "or",
            "expressions": [
                {
                    "-is_true": ["is_active"],
                },
                {
                    "operator": "and",
                    "expressions": [
                        {
                            "gt": ["age", 30],
                        },
                        {
                            "le": ["salary", 1000],
                        },
                        {
                            "eq": ["gender", "male"],
                        },
                    ],
                },
            ],
        },
    ],
)
def test_rule_dict_is_true(
    employee: dict[str, Any],
    predicate_getter: Callable[[dict[str, Any]], Predicate[Any, Any]],
    rule_dict: dict[str, Any],
) -> None:
    predicate = predicate_getter(rule_dict)
    assert bool(predicate(employee)) is True
