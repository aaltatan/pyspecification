from dataclasses import dataclass
from typing import Any

import pytest
from pyspecification import CompilationError, Predicate, PredicateCompiler, RuleSchema, object_rule

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
            {"is_admin": []},
            is_admin(),
        ),
        (
            [User(name="Abdullah", age=18, is_admin=False)],
            {"-is_admin": []},
            ~is_admin(),
        ),
        (
            [User(name="admin", age=18, is_admin=True)],
            {
                "name__istartswith": ["admin"],
                "age__between": [18, 30],
            },
            name__istartswith("admin") & age__between(18, 30),
        ),
        (
            [
                User(name="Abdullah", age=16, is_admin=True),
                User(name="admin", age=20, is_admin=False),
            ],
            {
                "operator": "or",
                "expressions": [
                    {"is_admin": []},
                    {
                        "name__istartswith": ["admin"],
                        "age__between": [18, 30],
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
                "operator": "or",
                "inverse": True,
                "expressions": [
                    {"is_admin": []},
                    {
                        "name__istartswith": ["admin"],
                        "age__between": [18, 30],
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
    compiled_predicate = compiler.compile(RuleSchema(**rule_dict).model_dump())
    assert all(compiled_predicate(user) for user in users) == all(predicate(user) for user in users)


@pytest.mark.parametrize(
    "rule_dict",
    [
        {"rule_not_exists": 20},
        {
            "expressions": [
                {"name__istartswith": ["admin"]},
                {"age__between": [18, 30]},
                {
                    "operator": "or",
                    "expressions": [
                        {"is_admin": []},
                        {
                            "name__istartswith": ["admin"],
                            "rule_not_exists": [18, 30],  # this should raise an error
                        },
                    ],
                },
            ]
        },
    ],
)
def test_compiler_with_invalid_rule_name(
    compiler: PredicateCompiler[User, bool],
    rule_dict: dict[str, Any],
) -> None:
    with pytest.raises(CompilationError, match="Rule 'rule_not_exists' is not found"):
        compiler.compile(RuleSchema(**rule_dict).model_dump())


def test_compiler_with_invalid_rule_dict(compiler: PredicateCompiler) -> None:
    with pytest.raises(CompilationError, match="Invalid expression type"):
        compiler.compile(
            {
                "name__istartswith": "dasdads",
                "rule_not_exists": [],  # type: ignore  # noqa: PGH003
            },
        )
