from dataclasses import dataclass
from typing import Any

import pytest
from pyspecification import (
    Predicate,
    PredicateCompiler,
    RuleDoesNotExistError,
    RuleSchema,
    object_rule,
)

from tests.models import CompilerGetter


@dataclass
class User:
    name: str
    age: int
    is_admin: bool = True


@object_rule()
def is_admin(user: User) -> bool:
    return user.is_admin


@object_rule()
def name__istartswith(user: User, value: str) -> bool:
    return user.name.lower().startswith(value.lower())


@object_rule()
def age__between(user: User, min_age: int, max_age: int) -> bool:
    return user.age >= min_age and user.age <= max_age


@pytest.fixture
def compiler(logical_compiler_getter: CompilerGetter) -> PredicateCompiler[User, bool]:
    return logical_compiler_getter(
        {
            "is_admin": is_admin,
            "name__istartswith": name__istartswith,
            "age__between": age__between,
        }
    )


@pytest.mark.parametrize(
    "users, rule_dict, predicate",
    [
        (
            [User(name="Abdullah", age=18, is_admin=True)],
            {"name": "is_admin", "args": [], "kwargs": {}, "inverse": False},
            is_admin(),
        ),
        (
            [User(name="Abdullah", age=18, is_admin=False)],
            {"name": "is_admin", "args": [], "kwargs": {}, "inverse": True},
            ~is_admin(),
        ),
        (
            [User(name="admin", age=18, is_admin=True)],
            {
                "operator": "all",
                "expressions": [
                    {
                        "name": "name__istartswith",
                        "args": ["admin"],
                        "kwargs": {},
                        "inverse": False,
                    },
                    {
                        "name": "age__between",
                        "args": [18, 30],
                        "kwargs": {},
                        "inverse": False,
                    },
                ],
            },
            name__istartswith("admin") & age__between(18, 30),
        ),
        (
            [
                User(name="Abdullah", age=16, is_admin=True),
                User(name="admin", age=20, is_admin=False),
            ],
            {
                "operator": "any",
                "expressions": [
                    {
                        "name": "is_admin",
                        "args": [],
                        "kwargs": {},
                        "inverse": False,
                    },
                    {
                        "operator": "all",
                        "expressions": [
                            {
                                "name": "name__istartswith",
                                "args": ["admin"],
                                "kwargs": {},
                                "inverse": False,
                            },
                            {
                                "name": "age__between",
                                "args": [18, 30],
                                "kwargs": {},
                                "inverse": False,
                            },
                        ],
                    },
                ],
            },
            is_admin() | (name__istartswith("admin") & age__between(18, 30)),
        ),
        (
            [
                User(name="Abdullah", age=16, is_admin=True),
                User(name="admin", age=20, is_admin=False),
            ],
            {
                "operator": "all",
                "expressions": [
                    {
                        "name": "is_admin",
                        "args": [],
                        "kwargs": {},
                        "inverse": True,
                    },
                    {
                        "operator": "any",
                        "expressions": [
                            {
                                "name": "name__istartswith",
                                "args": ["admin"],
                                "kwargs": {},
                                "inverse": True,
                            },
                            {
                                "name": "age__between",
                                "args": [18, 30],
                                "kwargs": {},
                                "inverse": True,
                            },
                        ],
                    },
                ],
            },
            ~(is_admin() | (name__istartswith("admin") & age__between(18, 30))),
        ),
    ],
)
def test_compiler(
    users: list[User],
    rule_dict: dict[str, Any],
    predicate: Predicate[Any, Any],
    compiler: PredicateCompiler[User, bool],
) -> None:
    compiled_predicate = compiler.compile(
        RuleSchema(**rule_dict).model_dump(),  # type: ignore  # noqa: PGH003
    )
    assert all(compiled_predicate(user) for user in users) == all(predicate(user) for user in users)


@pytest.mark.parametrize(
    "rule_dict",
    [
        {"name": "rule_not_exists", "args": [20], "kwargs": {}, "inverse": False},
        {
            "operator": "all",
            "expressions": [
                {
                    "name": "name__istartswith",
                    "args": ["admin"],
                    "kwargs": {},
                    "inverse": False,
                },
                {
                    "name": "age__between",
                    "args": [18, 30],
                    "kwargs": {},
                    "inverse": False,
                },
                {
                    "operator": "any",
                    "expressions": [
                        {
                            "name": "is_admin",
                            "args": [],
                            "kwargs": {},
                            "inverse": False,
                        },
                        {
                            "operator": "all",
                            "expressions": [
                                {
                                    "name": "name__istartswith",
                                    "args": ["admin"],
                                    "kwargs": {},
                                    "inverse": False,
                                },
                                {
                                    "name": "rule_not_exists",
                                    "args": [18, 30],
                                    "kwargs": {},
                                    "inverse": False,
                                },
                            ],
                        },
                    ],
                },
            ],
        },
    ],
)
def test_compiler_with_invalid_rule_name(
    compiler: PredicateCompiler[User, bool],
    rule_dict: dict[str, Any],
) -> None:
    with pytest.raises(RuleDoesNotExistError, match="Rule 'rule_not_exists' does not exist"):
        compiler.compile(
            RuleSchema(**rule_dict).model_dump(),  # type: ignore  # noqa: PGH003
        )


def test_compiler_with_invalid_rule_dict(compiler: PredicateCompiler) -> None:
    with pytest.raises(TypeError) as error:
        compiler.compile(
            {
                "operator": "all",
                "expressionsx": [
                    {
                        "name": "name__istartswith",
                        "args": ["dasdads"],
                        "kwargs": {},
                        "inverse": False,
                    },
                    {
                        "name": "rule_not_exists",
                        "args": [],
                        "kwargs": {},
                        "inverse": False,
                    },
                ],
            }  # type: ignore  # noqa: PGH003
        )

    message = str(error.value)
    assert "Invalid expression at $." in message
    assert "Predicate:" in message
    assert "Expression wrapper:" in message
    assert "Received:" in message


def test_compiler_reports_nested_invalid_expression_path(
    compiler: PredicateCompiler,
) -> None:
    with pytest.raises(TypeError, match=r"Invalid expression at \$\.expressions\[1\]"):
        compiler.compile(
            {
                "operator": "all",
                "expressions": [
                    {"name": "is_admin", "args": [], "kwargs": {}, "inverse": False},
                    {"unexpected": True, "another": False},
                ],
            },  # type: ignore  # noqa: PGH003
        )


@pytest.mark.parametrize("expression", [None, "invalid", 42])
def test_compiler_reports_invalid_non_dict_expression(
    compiler: PredicateCompiler,
    expression: Any,
) -> None:
    with pytest.raises(TypeError, match=r"Invalid expression at \$\."):
        compiler.compile(expression)  # type: ignore[arg-type]
