from dataclasses import dataclass
from typing import Any

import pytest
from pyspecification import ExpressionSchema, Predicate, PredicateCompiler, object_rule


@dataclass
class User:
    name: str
    age: int
    is_admin: bool = True


@object_rule
def is_admin(user: User) -> bool:
    return user.is_admin


@object_rule
def name__istartswith(user: User, value: str) -> bool:
    return user.name.lower().startswith(value.lower())


@object_rule
def age__between(user: User, min_age: int, max_age: int) -> bool:
    return user.age >= min_age and user.age <= max_age


@pytest.fixture
def compiler() -> PredicateCompiler:
    return PredicateCompiler(
        rules={
            "is_admin": is_admin,
            "name__istartswith": name__istartswith,
            "age__between": age__between,
        },
        initial_predicate_factory=lambda schema: Predicate(
            lambda _: schema["operator"] == "and",
        ),
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
    compiler: PredicateCompiler,
) -> None:
    compiled_predicate = compiler.compile(ExpressionSchema(**rule_dict).model_dump())
    assert all(compiled_predicate(user) for user in users) == all(predicate(user) for user in users)
