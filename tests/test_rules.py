from dataclasses import dataclass
from typing import Any

import pytest
from pyspecification.rules import object_rule, subscriptable_rule

# -----------------------
# obj rule
# -----------------------


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


admin_rule_v1 = is_admin() | (name__istartswith("admin") & age__between(18, 30))


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
    assert admin_rule_v1(user) == expected


# -----------------------
# dict rule
# -----------------------


@subscriptable_rule
def is_true(obj: dict[str, Any], key: str) -> bool:
    return obj[key] is True


@subscriptable_rule
def istartswith(obj: dict[str, Any], key: str, value: str) -> bool:
    return obj[key].lower().startswith(value.lower())


@subscriptable_rule
def between(obj: dict[str, Any], key: str, min_value: int, max_value: int) -> bool:
    return obj[key] >= min_value and obj[key] <= max_value


admin_rule_v2 = is_true("is_admin") | (istartswith("name", "admin") & between("age", 18, 30))


@pytest.mark.parametrize(
    "user, expected",
    [
        ({"name": "Abdullah", "age": 18, "is_admin": True}, True),
        ({"name": "Abdullah", "age": 18, "is_admin": False}, False),
        ({"name": "Abdullah", "age": 19, "is_admin": False}, False),
        ({"name": "admin", "age": 25, "is_admin": False}, True),
    ],
)
def test_is_admin_dict_rule(user: dict[str, Any], expected: bool) -> None:  # noqa: FBT001
    assert admin_rule_v2(user) == expected


# -----------------------
# list rule
# -----------------------


@subscriptable_rule
def seq_is_true(obj: list[Any], idx: int) -> bool:
    return obj[idx] is True


@subscriptable_rule
def seq_istartswith(obj: list[Any], idx: int, value: str) -> bool:
    return obj[idx].lower().startswith(value.lower())


@subscriptable_rule
def seq_between(obj: list[Any], idx: int, min_value: int, max_value: int) -> bool:
    return obj[idx] >= min_value and obj[idx] <= max_value


admin_rule_v3 = seq_is_true(-1) | (seq_istartswith(0, "admin") & seq_between(1, 18, 30))


@pytest.mark.parametrize(
    "user, expected",
    [
        (["Abdullah", 18, True], True),
        (["Abdullah", 18, False], False),
        (["Abdullah", 19, False], False),
        (["admin", 25, False], True),
    ],
)
def test_is_admin_seq_rule(user: list[Any], expected: bool) -> None:  # noqa: FBT001
    assert admin_rule_v3(user) == expected
