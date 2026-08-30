from dataclasses import dataclass
from typing import Any

import pytest
from pyspecification import (
    ObjectRulesRegistry,
    RuleAlreadyRegisteredError,
    RuleNotFoundError,
    SubscriptableRulesRegistry,
)

# -----------------------
# fixtures
# -----------------------


@dataclass
class User:
    name: str
    age: int


@pytest.fixture
def obj_registry() -> ObjectRulesRegistry[User, bool]:
    return ObjectRulesRegistry[User, bool](operator="logical")


@pytest.fixture
def sub_registry() -> SubscriptableRulesRegistry[dict[str, Any], str, bool]:
    return SubscriptableRulesRegistry[dict[str, Any], str, bool](
        operator="logical",
        check_key_existence=False,
    )


# -----------------------
# object tests
# -----------------------


def test_obj_registry_register_and_get(obj_registry: ObjectRulesRegistry[User, bool]) -> None:
    def is_adult(user: User) -> bool:
        return user.age >= 18

    obj_registry.register_rule(is_adult)
    rule_fn = obj_registry["is_adult"]
    predicate = rule_fn()

    assert predicate(User(name="Test", age=20)) is True
    assert predicate(User(name="Test", age=16)) is False


def test_obj_registry_rule_decorator(obj_registry: ObjectRulesRegistry[User, bool]) -> None:
    @obj_registry.rule()
    def has_name(user: User, name: str) -> bool:
        return user.name == name

    rule_fn = obj_registry["has_name"]
    predicate = rule_fn("Test")

    assert predicate(User(name="Test", age=20)) is True
    assert predicate(User(name="Wrong", age=20)) is False


def test_obj_registry_custom_name(obj_registry: ObjectRulesRegistry[User, bool]) -> None:
    @obj_registry.rule(name="custom_is_adult")
    def is_adult(user: User) -> bool: ...

    assert "custom_is_adult" in obj_registry.rules
    assert "is_adult" not in obj_registry.rules


def test_obj_registry_already_registered(obj_registry: ObjectRulesRegistry[User, bool]) -> None:
    def rule1(_: User) -> bool: ...
    def rule2(_: User) -> bool: ...

    obj_registry.register_rule(rule1, name="same_name")

    with pytest.raises(RuleAlreadyRegisteredError) as exc:
        obj_registry.register_rule(rule2, name="same_name")

    assert "Rule 'same_name' is already registered" in str(exc.value)


def test_obj_registry_not_registered(obj_registry: ObjectRulesRegistry[User, bool]) -> None:
    with pytest.raises(RuleNotFoundError) as exc:
        _ = obj_registry["non_existent"]

    assert "Rule 'non_existent' is not registered" in str(exc.value)


def test_obj_registry_reserved_word(obj_registry: ObjectRulesRegistry[User, bool]) -> None:
    def reserved_rule(_: User) -> bool: ...

    with pytest.raises(ValueError) as exc:
        obj_registry.register_rule(reserved_rule, name="name")

    assert "Rule name 'name' is reserved" in str(exc.value)


def test_obj_registry_invalid_name(obj_registry: ObjectRulesRegistry[User, bool]) -> None:
    def invalid_name_rule(_: User) -> bool: ...

    with pytest.raises(ValueError):
        obj_registry.register_rule(invalid_name_rule, name="123_invalid")


def test_obj_registry_processors(obj_registry: ObjectRulesRegistry[User, bool]) -> None:
    def is_age(user: User, age: int) -> bool:
        return user.age == age

    obj_registry.register_rule(is_age, processors=(int, {"s": str}))
    rule_fn = obj_registry["is_age"]

    predicate = rule_fn("20")
    assert predicate(User(name="Test", age=20)) is True

    predicate = rule_fn(age="20")
    assert predicate(User(name="Test", age=20)) is True


# -----------------------
# dict tests
# -----------------------


def test_sub_registry_register_and_get(
    sub_registry: SubscriptableRulesRegistry[dict[str, Any], str, bool],
) -> None:
    def is_true(obj: dict[str, Any], key: str) -> bool:
        return obj[key] is True

    sub_registry.register_rule(is_true)
    rule_fn = sub_registry["is_true"]

    predicate = rule_fn("is_admin")

    assert predicate({"is_admin": True}) is True
    assert predicate({"is_admin": False}) is False


def test_sub_registry_rule_decorator(
    sub_registry: SubscriptableRulesRegistry[dict[str, Any], str, bool],
) -> None:
    @sub_registry.rule()
    def has_value(obj: dict[str, Any], key: str, value: Any) -> bool:
        return obj[key] == value

    rule_fn = sub_registry["has_value"]
    predicate = rule_fn("name", "Test")

    assert predicate({"name": "Test"}) is True
    assert predicate({"name": "Wrong"}) is False


def test_sub_registry_custom_name(
    sub_registry: SubscriptableRulesRegistry[dict[str, Any], str, bool],
) -> None:
    @sub_registry.rule(name="custom_is_true")
    def is_true(obj: dict[str, Any], key: str) -> bool: ...

    assert "custom_is_true" in sub_registry.rules
    assert "is_true" not in sub_registry.rules


def test_sub_registry_already_registered(
    sub_registry: SubscriptableRulesRegistry[dict[str, Any], str, bool],
) -> None:
    def rule1(_: dict[str, Any], __: str) -> bool: ...
    def rule2(_: dict[str, Any], __: str) -> bool: ...

    sub_registry.register_rule(rule1, name="same_name")

    with pytest.raises(RuleAlreadyRegisteredError) as exc:
        sub_registry.register_rule(rule2, name="same_name")

    assert "Rule 'same_name' is already registered" in str(exc.value)


def test_sub_registry_not_registered(
    sub_registry: SubscriptableRulesRegistry[dict[str, Any], str, bool],
) -> None:
    with pytest.raises(RuleNotFoundError) as exc:
        _ = sub_registry["non_existent"]

    assert "Rule 'non_existent' is not registered" in str(exc.value)


def test_sub_registry_reserved_word(
    sub_registry: SubscriptableRulesRegistry[dict[str, Any], str, bool],
) -> None:
    def reserved_rule(_: dict[str, Any], __: str) -> bool: ...

    with pytest.raises(ValueError) as exc:
        sub_registry.register_rule(reserved_rule, name="name")

    assert "Rule name 'name' is reserved" in str(exc.value)


def test_sub_registry_invalid_name(
    sub_registry: SubscriptableRulesRegistry[dict[str, Any], str, bool],
) -> None:
    def invalid_name_rule(_: dict[str, Any], __: str) -> bool: ...

    with pytest.raises(ValueError):
        sub_registry.register_rule(invalid_name_rule, name="123_invalid")


def test_sub_registry_processors(
    sub_registry: SubscriptableRulesRegistry[dict[str, Any], str, bool],
) -> None:
    def is_age(obj: dict[str, Any], key: str, age: int) -> bool:
        return obj[key] == age

    sub_registry.register_rule(is_age, processors=(int, {"s": str}))
    rule_fn = sub_registry["is_age"]

    predicate = rule_fn("age", "20")
    assert predicate({"age": 20}) is True

    predicate = rule_fn("age", age="20")
    assert predicate({"age": 20}) is True
