from dataclasses import dataclass

import pytest
from pyspecification import Predicate


@dataclass
class User:
    name: str
    age: int
    is_admin: bool = True


is_admin: Predicate[User, bool] = Predicate(lambda user: user.is_admin is True)
name__istartswith_admin: Predicate[User, bool] = Predicate(
    lambda user: user.name.lower().startswith("admin")
)
age__between_18_and_30: Predicate[User, bool] = Predicate(
    lambda user: user.age >= 18 and user.age <= 30
)


rule = is_admin | (name__istartswith_admin & age__between_18_and_30)


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
