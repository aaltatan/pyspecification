from dataclasses import dataclass

import pytest
from pyspecification import Predicate


@dataclass
class User:
    name: str
    age: int
    is_admin: bool = True


def _is_admin(user: User) -> bool:
    return user.is_admin is True


def _name__istartswith_admin(user: User) -> bool:
    return user.name.lower().startswith("admin")


def _age__between_18_and_30(user: User) -> bool:
    return user.age >= 18 and user.age <= 30


is_admin: Predicate[User, bool] = Predicate(_is_admin, operator="logical")
name__istartswith_admin: Predicate[User, bool] = Predicate(
    _name__istartswith_admin, operator="logical"
)
age__between_18_and_30: Predicate[User, bool] = Predicate(
    _age__between_18_and_30, operator="logical"
)


rule = is_admin | (name__istartswith_admin & age__between_18_and_30 & ~is_admin)


def test_predicate_repr() -> None:
    assert (
        repr(rule)
        == "Predicate((_is_admin OR ((_name__istartswith_admin AND _age__between_18_and_30) AND NOT _is_admin)))"  # noqa: E501
    )


@pytest.mark.parametrize(
    "user, expected",
    [
        (User(name="Abdullah", age=18, is_admin=True), True),
        (User(name="Abdullah", age=18, is_admin=False), False),
        (User(name="Abdullah", age=19, is_admin=False), False),
        (User(name="admin", age=25, is_admin=False), True),
    ],
)
def test_is_admin_rule(user: User, expected: bool) -> None:  # noqa: FBT001
    assert rule(user) == expected
