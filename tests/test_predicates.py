from collections.abc import Callable
from typing import Any

import pytest
from pyspecification import Predicate, PredicateCompiler, read_expression

from .models import Employee
from .predicates import age__gt, gender__is_male, is_active, predicates, salary__le

# -----------------------
# fixtures
# -----------------------


@pytest.fixture
def employee() -> Employee:
    return Employee(name="Abdullah", age=31, salary=1000, gender="male", is_active=True)


@pytest.fixture
def compiler() -> PredicateCompiler:
    return PredicateCompiler(
        predicates=predicates,
        initial_predicate_factory=lambda schema: Predicate(
            lambda _: schema.operator == "and",
        ),
    )


@pytest.fixture
def predicate_getter(
    compiler: PredicateCompiler,
) -> Callable[[dict[str, Any]], Predicate[Any, Any]]:
    def inner(rule_dict: dict[str, Any]) -> Predicate[Any, Any]:
        expression = read_expression(rule_dict)
        return compiler.compile(expression)

    return inner


# -----------------------
# test cases
# -----------------------


@pytest.mark.parametrize(
    "rule",
    [
        gender__is_male() & is_active(),
        age__gt(30) & salary__le(1000),
        age__gt(30) & salary__le(1000) & gender__is_male() & is_active(),
        ~is_active() | (age__gt(30) & salary__le(1000) & gender__is_male()),
    ],
)
def test_is_true(employee: Employee, rule: Predicate[Employee, bool]) -> None:
    assert bool(rule(employee)) is True


@pytest.mark.parametrize(
    "rule_dict",
    [
        {"gender__is_male": [], "is_active": []},
        {"age__gt": 30, "salary__le": 100},
        {"age__gt": 30, "salary__le": 100, "gender__is_male": [], "is_active": []},
    ],
)
def test_rule_dict_is_true(
    employee: Employee,
    predicate_getter: Callable[[dict[str, Any]], Predicate[Any, Any]],
    rule_dict: dict[str, Any],
) -> None:
    predicate = predicate_getter(rule_dict)
    assert bool(predicate(employee)) is True
