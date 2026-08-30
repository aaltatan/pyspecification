# ruff: noqa: DTZ001, DTZ007
from datetime import datetime
from typing import Any

import pytest
from pyspecification import PredicateCompiler, RuleSchema, SubscriptableRulesRegistry

from tests.models import CompilerGetter

DATA = [
    {
        "name": "Abdullah Altatan",
        "rank": 18,
        "is_admin": True,
        "gender": "Male",
        "birthdate": datetime(1995, 1, 1),
    },
    {
        "name": "Bob Altatan",
        "rank": 6,
        "is_admin": True,
        "gender": "Male",
        "birthdate": datetime(2000, 1, 1),
    },
    {
        "name": "Charlie Alsan",
        "rank": 3,
        "is_admin": False,
        "gender": "Male",
        "birthdate": datetime(1998, 1, 1),
    },
    {
        "name": "David Alsan",
        "rank": 12,
        "is_admin": False,
        "gender": "Male",
        "birthdate": datetime(2001, 1, 1),
    },
    {
        "name": "Eve Alsan",
        "rank": 8,
        "is_admin": True,
        "gender": "Female",
        "birthdate": datetime(2010, 1, 1),
    },
    {
        "name": "Rama Alsan",
        "rank": 3,
        "is_admin": False,
        "gender": "Female",
        "birthdate": datetime(2002, 1, 1),
    },
]


rules = SubscriptableRulesRegistry[dict[str, Any], str, bool](operator="logical")


@rules.rule()
def string__ieq(obj: dict[str, Any], key: str, value: str) -> bool:
    return obj[key].lower() == value.lower()


@rules.rule()
def string__iendswith(obj: dict[str, Any], key: str, value: str) -> bool:
    return obj[key].lower().endswith(value.lower())


@rules.rule()
def number__le(obj: dict[str, Any], key: str, value: int) -> bool:
    return obj[key] <= value


@rules.rule()
def is_true(obj: dict[str, Any], key: str) -> bool:
    return obj[key] is True


@rules.rule(processors=(lambda value: datetime.strptime(value, "%Y-%m-%d"), {}))
def datetime__gt(obj: dict[str, Any], key: str, value: datetime) -> bool:
    return obj[key] > value


@pytest.fixture
def compiler(logical_compiler_getter: CompilerGetter) -> PredicateCompiler:
    return logical_compiler_getter(rules.rules)


@pytest.mark.parametrize(
    "filter_rule_data, expected_names",
    [
        (
            {
                "string__iendswith": ["name", "altatan"],
                "string__ieq": ["gender", "male"],
            },
            ("Abdullah Altatan", "Bob Altatan"),
        ),
        (
            {
                "number__le": ["rank", 10],
                "string__ieq": ["gender", "female"],
                "-is_true": ["is_admin"],
            },
            ("Rama Alsan",),
        ),
        (
            {
                "datetime__gt": ["birthdate", "2001-06-01"],
            },
            ("Eve Alsan", "Rama Alsan"),
        ),
    ],
)
def test_filtering_system(
    compiler: PredicateCompiler,
    filter_rule_data: dict[str, Any],
    expected_names: tuple[str, ...],
) -> None:
    predicate = compiler.compile(RuleSchema(**filter_rule_data).model_dump())
    filtered_data = [item for item in DATA if predicate(item)]

    assert all(item["name"] in expected_names for item in filtered_data)
    assert len(filtered_data) == len(expected_names)
