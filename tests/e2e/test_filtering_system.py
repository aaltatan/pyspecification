# ruff: noqa: DTZ001, DTZ007
from datetime import datetime
from typing import Any

import pytest
from pyspecification import (
    MissingArgumentError,
    PredicateCompiler,
    ProcessArgumentError,
    RuleDoesNotExistError,
    RuleSchema,
    SubscriptableRulesRegistry,
    TooManyArgumentsError,
    UnexpectedKeywordArgumentError,
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

    @rules.rule()
    def string__istartswith(obj: dict[str, Any], key: str, *, value: str) -> bool: ...
    @rules.rule()
    def string__icontains(obj: dict[str, Any], key: str, value: str) -> bool: ...

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


@pytest.mark.parametrize(
    "filter_rule_data, exception_class",
    [
        # def string__istartswith(obj: dict[str, Any], key: str, *, value: str) -> bool:
        ({"string__istartswith": []}, MissingArgumentError),
        ({"string__istartswith": ["name"]}, MissingArgumentError),
        ({"string__istartswith": ["name", "a"]}, TooManyArgumentsError),
        ({"string__istartswith": ["name", "a", "xxx"]}, TooManyArgumentsError),
        ({"string__istartswith": {}}, MissingArgumentError),
        ({"string__istartswith": {"key": "name"}}, MissingArgumentError),
        ({"string__istartswith": {"value", "ssss"}}, MissingArgumentError),
        (
            {"string__istartswith": {"key": "name", "value_not_exists": "sss"}},
            UnexpectedKeywordArgumentError,
        ),
        (
            {"string__istartswith": {"key": "name", "value": "a", "value_not_exists": "sss"}},
            UnexpectedKeywordArgumentError,
        ),
        # def string__icontains(obj: dict[str, Any], key: str, value: str) -> bool:
        ({"string__icontains": []}, MissingArgumentError),
        ({"string__icontains": ["name"]}, MissingArgumentError),
        ({"string__icontains": ["name", "a", "xxx"]}, TooManyArgumentsError),
        ({"string__icontains": {}}, MissingArgumentError),
        ({"string__icontains": {"key": "name"}}, MissingArgumentError),
        ({"string__icontains": {"value", "ssss"}}, MissingArgumentError),
        (
            {"string__icontains": {"key": "name", "value_not_exists": "sss"}},
            UnexpectedKeywordArgumentError,
        ),
        (
            {"string__icontains": {"key": "name", "value": "a", "value_not_exists": "sss"}},
            UnexpectedKeywordArgumentError,
        ),
    ],
)
def test_filtering_system_with_invalid_inputs(
    filter_rule_data: dict[str, Any],
    exception_class: type[Exception],
    compiler: PredicateCompiler[dict[str, Any], bool],
) -> None:
    with pytest.raises(exception_class):
        predicate = compiler.compile(RuleSchema(**filter_rule_data).model_dump())
        predicate({"name": "Abdullah", "age": 18, "is_admin": True})


def test_filtering_system_with_invalid_rule_name(
    compiler: PredicateCompiler[dict[str, Any], bool],
) -> None:
    with pytest.raises(RuleDoesNotExistError, match="Rule 'invalid_rule' does not exist"):
        compiler.compile(
            RuleSchema(
                **{"invalid_rule": ["birthdate", "06-01-2001"]}  # type: ignore  # noqa: PGH003, PIE804
            ).model_dump()
        )


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
