from collections.abc import Callable
from dataclasses import dataclass

import pytest
from pyspecification import OperatorType, Predicate

type RulesCreatorFn = Callable[[OperatorType], dict[str, Predicate[User, bool]]]


@dataclass
class User:
    name: str
    age: int
    is_admin: bool = True


@pytest.fixture
def rules_creator() -> RulesCreatorFn:
    def is_admin(user: User) -> bool:
        return user.is_admin is True

    def name_istartswith_admin(user: User) -> bool:
        return user.name.lower().startswith("admin")

    def is_adult(user: User) -> bool:
        return user.age >= 18 and user.age <= 30

    def inner(operator: OperatorType) -> dict[str, Predicate[User, bool]]:
        return {
            "is_admin": Predicate(is_admin, operator=operator),
            "name_istartswith_admin": Predicate(name_istartswith_admin, operator=operator),
            "is_adult": Predicate(is_adult, operator=operator),
        }

    return inner


@pytest.fixture
def logical_rules(rules_creator: RulesCreatorFn) -> dict[str, Predicate[User, bool]]:
    return rules_creator("logical")


@pytest.fixture
def bitwise_rules(rules_creator: RulesCreatorFn) -> dict[str, Predicate[User, bool]]:
    return rules_creator("bitwise")


@pytest.fixture
def logical_rule(logical_rules: dict[str, Predicate[User, bool]]) -> Predicate[User, bool]:
    return logical_rules["is_admin"] | (
        logical_rules["name_istartswith_admin"]
        & logical_rules["is_adult"]
        & ~logical_rules["is_admin"]
    )


@pytest.fixture
def bitwise_rule(bitwise_rules: dict[str, Predicate[User, bool]]) -> Predicate[User, bool]:
    return bitwise_rules["is_admin"] | (
        bitwise_rules["name_istartswith_admin"]
        & bitwise_rules["is_adult"]
        & ~bitwise_rules["is_admin"]
    )


def test_repr(
    logical_rule: Predicate[User, bool],
    bitwise_rule: Predicate[User, bool],
) -> None:
    assert (
        repr(logical_rule)
        == "Predicate((is_admin OR ((name_istartswith_admin AND is_adult) AND NOT is_admin)))"
    )
    assert (
        repr(bitwise_rule)
        == "Predicate((is_admin | ((name_istartswith_admin & is_adult) & ~is_admin)))"
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
def test_predicate(
    logical_rule: Predicate[User, bool],
    bitwise_rule: Predicate[User, bool],
    user: User,
    expected: bool,  # noqa: FBT001
) -> None:
    assert logical_rule(user) == expected
    assert bitwise_rule(user) == expected


def test_raising_error_when_combine_bitwise_and_logical() -> None:
    with pytest.raises(ValueError) as exc:
        _ = Predicate(lambda _: True, operator="bitwise") | Predicate(
            lambda _: True, operator="logical"
        )

    assert "Cannot combine predicates with different operators" in str(exc.value)
