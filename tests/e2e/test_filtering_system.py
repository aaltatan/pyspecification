# ruff: noqa: DTZ001, DTZ007
from datetime import datetime
from typing import Any

import pytest
from pyspecification import (
    PredicateCompiler,
    ProcessArgumentError,
    RuleSchema,
    SubscriptableRulesRegistry,
)

from tests.models import CompilerGetter


@pytest.fixture
def data() -> list[dict[str, Any]]:
    return [
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


@pytest.fixture()
def rules() -> SubscriptableRulesRegistry[dict[str, Any], str, bool]:
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

    @rules.rule()
    def datetime__ge(obj: dict[str, Any], key: str, value: datetime) -> bool:
        return obj[key] >= value

    return rules


@pytest.fixture
def compiler(
    rules: SubscriptableRulesRegistry[dict[str, Any], str, bool],
    logical_compiler_getter: CompilerGetter,
) -> PredicateCompiler[dict[str, Any], bool]:
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
    data: list[dict[str, Any]],
    compiler: PredicateCompiler[dict[str, Any], bool],
    filter_rule_data: dict[str, Any],
    expected_names: tuple[str, ...],
) -> None:
    predicate = compiler.compile(RuleSchema(**filter_rule_data).model_dump())
    filtered_data = [item for item in data if predicate(item)]

    assert all(item["name"] in expected_names for item in filtered_data)
    assert len(filtered_data) == len(expected_names)


def test_filtering_system_with_invalid_datetime_format_arg(
    compiler: PredicateCompiler[dict[str, Any], bool],
) -> None:
    with pytest.raises(ProcessArgumentError, match="Argument '06-01-2001' failed to process"):
        compiler.compile(
            RuleSchema(
                **{"datetime__gt": ["birthdate", "06-01-2001"]}  # type: ignore  # noqa: PGH003, PIE804
            ).model_dump()
        )


def test_filtering_system_with_invalid_datetime_format_kwarg(
    compiler: PredicateCompiler[dict[str, Any], bool],
) -> None:
    with pytest.raises(
        ProcessArgumentError,
        match="Keyword argument 'value' with value '06-01-2001' failed to process",
    ):
        compiler.compile(
            RuleSchema(
                **{  # noqa: PIE804
                    "datetime__gt": {
                        "key": "birthdate",
                        "value": "06-01-2001",
                    }
                }  # type: ignore  # noqa: PGH003
            ).model_dump()
        )


def test_filtering_system_without_processing_datetime(
    compiler: PredicateCompiler[dict[str, Any], bool],
) -> None:
    with pytest.raises(TypeError):
        compiler.compile(
            RuleSchema(
                **{"datetime__ge": ["birthdate", "2001-06-01"]}  # type: ignore  # noqa: PGH003, PIE804
            ).model_dump()
        )({"birthdate": datetime(2005, 1, 1)})
