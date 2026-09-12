# ruff: noqa: DTZ001, DTZ007
from datetime import datetime
from typing import Any

import pytest
from pyspecification import (
    MissingArgumentError,
    PredicateCompiler,
    ProcessArgumentError,
    RuleDoesNotExistError,
    SubscriptableRulesRegistry,
    TooManyArgumentsError,
    UnexpectedKeywordArgumentError,
)
from pyspecification.exceptions import PositionalOnlyArgumentError

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
    def string__startswith(obj: dict[str, Any], key: str, value: str, /) -> bool: ...
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
                "operator": "all",
                "expressions": [
                    {
                        "name": "string__iendswith",
                        "inverse": False,
                        "args": ["name", "altatan"],
                        "kwargs": {},
                    },
                    {
                        "name": "string__ieq",
                        "inverse": False,
                        "args": ["gender", "male"],
                        "kwargs": {},
                    },
                ],
            },
            ("Abdullah Altatan", "Bob Altatan"),
        ),
        (
            {
                "operator": "all",
                "expressions": [
                    {
                        "name": "number__le",
                        "inverse": False,
                        "args": ["rank", 10],
                        "kwargs": {},
                    },
                    {
                        "name": "string__ieq",
                        "inverse": False,
                        "args": ["gender", "female"],
                        "kwargs": {},
                    },
                    {
                        "name": "is_true",
                        "inverse": True,
                        "args": ["is_admin"],
                        "kwargs": {},
                    },
                ],
            },
            ("Rama Alsan",),
        ),
        (
            {
                "name": "datetime__gt",
                "inverse": False,
                "args": [],
                "kwargs": {"key": "birthdate", "value": "2001-06-01"},
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
    predicate = compiler.compile(filter_rule_data)  # type: ignore  # noqa: PGH003
    filtered_data = [item for item in data if predicate(item)]

    assert all(item["name"] in expected_names for item in filtered_data)
    assert len(filtered_data) == len(expected_names)


@pytest.mark.parametrize(
    "filter_rule_data, exception_class",
    [
        # def string__startswith(obj: dict[str, Any], key: str, value: str, /) -> bool:
        (
            {"name": "string__startswith", "args": [], "kwargs": {}, "inverse": False},
            MissingArgumentError,
        ),
        (
            {"name": "string__startswith", "args": ["name"], "kwargs": {}, "inverse": False},
            MissingArgumentError,
        ),
        (
            {
                "name": "string__startswith",
                "args": ["name", "a", "xxx"],
                "kwargs": {},
                "inverse": False,
            },
            TooManyArgumentsError,
        ),
        (
            {"name": "string__startswith", "args": [], "kwargs": {}, "inverse": False},
            MissingArgumentError,
        ),
        (
            {"name": "string__startswith", "args": [], "kwargs": {"key": "name"}, "inverse": False},
            MissingArgumentError,
        ),
        (
            {
                "name": "string__startswith",
                "args": [],
                "kwargs": {"key": "name", "value_not_exists": "sss"},
                "inverse": False,
            },
            UnexpectedKeywordArgumentError,
        ),
        (
            {
                "name": "string__startswith",
                "args": [],
                "kwargs": {"key": "name", "value": "a"},
                "inverse": False,
            },
            PositionalOnlyArgumentError,
        ),
        (
            {
                "name": "string__startswith",
                "args": [],
                "kwargs": {"key": "name", "value": "a", "value_not_exists": "sss"},
                "inverse": False,
            },
            PositionalOnlyArgumentError,
        ),
        # def string__istartswith(obj: dict[str, Any], key: str, *, value: str) -> bool:
        (
            {"name": "string__istartswith", "args": [], "kwargs": {}, "inverse": False},
            MissingArgumentError,
        ),
        (
            {"name": "string__istartswith", "args": ["name"], "kwargs": {}, "inverse": False},
            MissingArgumentError,
        ),
        (
            {"name": "string__istartswith", "args": ["name", "a"], "kwargs": {}, "inverse": False},
            TooManyArgumentsError,
        ),
        (
            {
                "name": "string__istartswith",
                "args": ["name", "a", "xxx"],
                "kwargs": {},
                "inverse": False,
            },
            TooManyArgumentsError,
        ),
        (
            {
                "name": "string__istartswith",
                "args": [],
                "kwargs": {},
                "inverse": False,
            },
            MissingArgumentError,
        ),
        (
            {
                "name": "string__istartswith",
                "args": [],
                "kwargs": {"key": "name"},
                "inverse": False,
            },
            MissingArgumentError,
        ),
        (
            {
                "name": "string__istartswith",
                "args": [],
                "kwargs": {"key": "name", "value_not_exists": "sss"},
                "inverse": False,
            },
            UnexpectedKeywordArgumentError,
        ),
        (
            {
                "name": "string__istartswith",
                "args": [],
                "kwargs": {"key": "name", "value": "a", "value_not_exists": "sss"},
                "inverse": False,
            },
            UnexpectedKeywordArgumentError,
        ),
        # def string__icontains(obj: dict[str, Any], key: str, value: str) -> bool:
        (
            {
                "name": "string__icontains",
                "args": [],
                "kwargs": {},
                "inverse": False,
            },
            MissingArgumentError,
        ),
        (
            {
                "name": "string__icontains",
                "args": ["name"],
                "kwargs": {},
                "inverse": False,
            },
            MissingArgumentError,
        ),
        (
            {
                "name": "string__icontains",
                "args": ["name", "a", "xxx"],
                "kwargs": {},
                "inverse": False,
            },
            TooManyArgumentsError,
        ),
        (
            {"name": "string__icontains", "args": [], "kwargs": {}, "inverse": False},
            MissingArgumentError,
        ),
        (
            {"name": "string__icontains", "args": [], "kwargs": {"key": "name"}, "inverse": False},
            MissingArgumentError,
        ),
        (
            {
                "name": "string__icontains",
                "args": [],
                "kwargs": {"key": "name", "value_not_exists": "sss"},
                "inverse": False,
            },
            UnexpectedKeywordArgumentError,
        ),
        (
            {
                "name": "string__icontains",
                "args": [],
                "kwargs": {"key": "name", "value": "a", "value_not_exists": "sss"},
                "inverse": False,
            },
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
        predicate = compiler.compile(filter_rule_data)  # type: ignore  # noqa: PGH003
        predicate({"name": "Abdullah", "age": 18, "is_admin": True})


def test_filtering_system_with_invalid_rule_name(
    compiler: PredicateCompiler[dict[str, Any], bool],
) -> None:
    with pytest.raises(RuleDoesNotExistError, match="Rule 'invalid_rule' does not exist"):
        compiler.compile(
            {
                "name": "invalid_rule",
                "args": ["birthdate", "06-01-2001"],
                "kwargs": {},
                "inverse": False,
            }
        )


def test_filtering_system_with_invalid_datetime_format_arg(
    compiler: PredicateCompiler[dict[str, Any], bool],
) -> None:
    with pytest.raises(ProcessArgumentError, match="Argument '06-01-2001' failed to process"):
        compiler.compile(
            {
                "name": "datetime__gt",
                "args": ["birthdate", "06-01-2001"],
                "kwargs": {},
                "inverse": False,
            }
        )


def test_filtering_system_with_invalid_datetime_format_kwarg(
    compiler: PredicateCompiler[dict[str, Any], bool],
) -> None:
    with pytest.raises(
        ProcessArgumentError,
        match="Keyword argument 'value' with value '06-01-2001' failed to process",
    ):
        compiler.compile(
            {
                "name": "datetime__gt",
                "inverse": False,
                "args": [],
                "kwargs": {"key": "birthdate", "value": "06-01-2001"},
            }
        )


def test_filtering_system_without_processing_datetime(
    compiler: PredicateCompiler[dict[str, Any], bool],
) -> None:
    with pytest.raises(TypeError):
        compiler.compile(
            {
                "name": "datetime__ge",
                "args": ["birthdate", "2001-06-01"],
                "kwargs": {},
                "inverse": False,
            }
        )({"birthdate": datetime(2005, 1, 1)})
