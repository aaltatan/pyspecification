from dataclasses import dataclass
from typing import Any

import pytest
from pyspecification import (
    ObjectRulesRegistry,
    RuleAlreadyRegisteredError,
    RuleDoesNotExistError,
    SubscriptableRulesRegistry,
)
from pyspecification.exceptions import RuleKeyDoesNotExistError

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
    with pytest.raises(RuleDoesNotExistError) as exc:
        _ = obj_registry["non_existent"]

    assert "Rule 'non_existent' does not exist" in str(exc.value)


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


def test_raising_error_when_using_hidden_rule(
    obj_registry: ObjectRulesRegistry[User, bool],
) -> None:
    @obj_registry.rule(hidden=True)
    def some_rule(user: User) -> bool: ...

    assert "some_rule" not in obj_registry.rules

    with pytest.raises(RuleDoesNotExistError, match="Rule 'some_rule' does not exist"):
        obj_registry["some_rule"]


def test_description_obj(
    obj_registry: ObjectRulesRegistry[User, bool],
) -> None:
    @obj_registry.rule(description="This is overridden description")
    def some_rule(_: User) -> bool:  # type: ignore  # noqa: PGH003
        """Do Some Work."""

    @obj_registry.rule()
    def some_rule_2(_: User) -> bool:  # type: ignore  # noqa: PGH003
        """Do Some Work."""

    @obj_registry.rule()
    def some_rule_3(_: User) -> bool: ...

    @obj_registry.rule(description="This is overridden description 2")
    def some_rule_4(_: User) -> bool:  # type: ignore  # noqa: PGH003
        """Do Some Work."""

    assert some_rule.__doc__ == "This is overridden description"
    assert some_rule_2.__doc__ == "Do Some Work."
    assert some_rule_3.__doc__ is None
    assert some_rule_4.__doc__ == "This is overridden description 2"


def test_obj_registry_repr(obj_registry: ObjectRulesRegistry[User, bool]) -> None:
    @obj_registry.rule()
    def name__startswith(user: User, value: str) -> bool: ...

    def name__endswith_fn(user: User, value: str) -> bool: ...

    name__endswith = obj_registry.register_rule(name__endswith_fn)

    name__contains = obj_registry.register_rule(lambda _: True, name="name__contains")

    rule = name__startswith("Abdullah") | (name__endswith("Abdullah") & name__contains())

    assert repr(rule) == "Predicate((name__startswith OR (name__endswith_fn AND name__contains)))"


def test_obj_registry_with_lambda(obj_registry: ObjectRulesRegistry[User, bool]) -> None:
    with pytest.raises(ValueError, match="You must provide a name for the rule"):
        obj_registry.register_rule(lambda _: True)


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
    with pytest.raises(RuleDoesNotExistError) as exc:
        _ = sub_registry["non_existent"]

    assert "Rule 'non_existent' does not exist" in str(exc.value)


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


def test_raising_error_when_using_one_key_of_forbidden_keys(
    sub_registry: SubscriptableRulesRegistry[dict[str, Any], str, bool],
) -> None:

    @sub_registry.rule(forbidden_keys=("some_value",))
    def some_rule(obj: dict[str, Any], key: str, value: str) -> bool: ...

    rule = some_rule("some_value", "some value")

    with pytest.raises(
        RuleKeyDoesNotExistError,
        match="Key 'some_value' does not exist in the object of rule 'some_rule'",
    ):
        rule({"name": "Abdullah", "age": 18, "is_admin": True})


def test_raising_error_when_using_hidden_rule_2(
    sub_registry: SubscriptableRulesRegistry[dict[str, Any], str, bool],
) -> None:
    @sub_registry.rule(hidden=True)
    def some_rule(obj: dict[str, Any], key: str, value: str) -> bool: ...

    assert "some_rule" not in sub_registry.rules

    with pytest.raises(RuleDoesNotExistError, match="Rule 'some_rule' does not exist"):
        sub_registry["some_rule"]


def test_description(
    sub_registry: SubscriptableRulesRegistry[dict[str, Any], str, bool],
) -> None:
    @sub_registry.rule(description="This is overridden description")
    def some_rule(_: dict[str, Any], __: str, ___: str) -> bool:  # type: ignore  # noqa: PGH003
        """Do Some Work."""

    @sub_registry.rule()
    def some_rule_2(_: dict[str, Any], __: str, ___: str) -> bool:  # type: ignore  # noqa: PGH003
        """Do Some Work."""

    @sub_registry.rule()
    def some_rule_3(obj: dict[str, Any], key: str, value: str) -> bool: ...

    @sub_registry.rule(description="This is overridden description 2")
    def some_rule_4(obj: dict[str, Any], key: str, value: str) -> bool: ...

    assert some_rule.__doc__ == "This is overridden description"
    assert some_rule_2.__doc__ == "Do Some Work."
    assert some_rule_3.__doc__ is None
    assert some_rule_4.__doc__ == "This is overridden description 2"
