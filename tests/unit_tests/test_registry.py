from dataclasses import dataclass
from inspect import signature
from typing import Any

import pytest
from pyspecification import (
    InvalidProcessorsError,
    MissingArgumentError,
    ObjectRulesRegistry,
    ProcessArgumentError,
    RuleAlreadyRegisteredError,
    RuleDoesNotExistError,
    SubscriptableRulesRegistry,
    TooManyArgumentsError,
    UnexpectedKeywordArgumentError,
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

    obj_registry.register_rule(is_age, processors=int)
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


def test_obj_registry_duplicate_hidden_does_not_hide_existing_rule(
    obj_registry: ObjectRulesRegistry[User, bool],
) -> None:
    """A failed duplicate registration must not have side effects on the existing rule."""

    def original(_: User) -> bool:
        return True

    def conflicting(_: User) -> bool:
        return False

    obj_registry.register_rule(original, name="dup")

    with pytest.raises(RuleAlreadyRegisteredError):
        obj_registry.register_rule(conflicting, name="dup", hidden=True)

    assert "dup" in obj_registry.rules
    assert obj_registry["dup"] is not None


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


def test_obj_registry_empty_string_name_falls_back_to_function_name(
    obj_registry: ObjectRulesRegistry[User, bool],
) -> None:
    """An explicit empty-string name is falsy, so it silently falls back to fn.__name__."""

    def some_rule(user: User) -> bool: ...

    obj_registry.register_rule(some_rule, name="")

    assert "some_rule" in obj_registry.rules


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

    sub_registry.register_rule(is_age, processors=int)
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


def test_sub_registry_duplicate_hidden_does_not_hide_existing_rule(
    sub_registry: SubscriptableRulesRegistry[dict[str, Any], str, bool],
) -> None:
    """A failed duplicate registration must not have side effects on the existing rule."""

    def original(_: dict[str, Any], __: str) -> bool:
        return True

    def conflicting(_: dict[str, Any], __: str) -> bool:
        return False

    sub_registry.register_rule(original, name="dup")

    with pytest.raises(RuleAlreadyRegisteredError):
        sub_registry.register_rule(conflicting, name="dup", hidden=True)

    assert "dup" in sub_registry.rules
    assert sub_registry["dup"] is not None


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


# -----------------------
# processors
# -----------------------


def test_obj_registry_processors_mapping_applies_by_name_for_positional_and_keyword(
    obj_registry: ObjectRulesRegistry[User, bool],
) -> None:
    @obj_registry.rule(processors={"min_age": int, "max_age": int})
    def age__between(user: User, min_age: int, max_age: int) -> bool:
        return min_age <= user.age <= max_age

    user = User(name="Test", age=20)

    assert age__between("18", "30")(user) is True
    assert age__between("18", max_age="19")(user) is False
    assert age__between(min_age="21", max_age="30")(user) is False


def test_obj_registry_processors_ellipsis_covers_remaining_parameters(
    obj_registry: ObjectRulesRegistry[User, bool],
) -> None:
    @obj_registry.rule(processors={"age": int, ...: str.strip})
    def matches(user: User, name: str, age: int) -> bool:
        return user.name == name and user.age == age

    assert matches("  Test ", "20")(User(name="Test", age=20)) is True


def test_obj_registry_processors_leave_unnamed_parameters_untouched(
    obj_registry: ObjectRulesRegistry[User, bool],
) -> None:
    @obj_registry.rule(processors={"age": int})
    def matches(user: User, name: str, age: int) -> bool:
        return user.name == name and user.age == age

    assert matches(" Test", "20")(User(name="Test", age=20)) is False


def test_obj_registry_processors_apply_to_var_positional_and_var_keyword(
    obj_registry: ObjectRulesRegistry[User, bool],
) -> None:
    @obj_registry.rule(processors=int)
    def any_age_of(user: User, *ages: int, **named_ages: int) -> bool:
        return user.age in (*ages, *named_ages.values())

    assert any_age_of("1", "20")(User(name="Test", age=20)) is True
    assert any_age_of(a="20")(User(name="Test", age=20)) is True
    assert any_age_of("1", a="2")(User(name="Test", age=20)) is False


def test_obj_registry_processors_do_not_apply_to_defaults(
    obj_registry: ObjectRulesRegistry[User, bool],
) -> None:
    @obj_registry.rule(processors=int)
    def older_than(user: User, age: int = 5) -> bool:
        return user.age > age

    assert older_than()(User(name="Test", age=6)) is True


def test_obj_registry_processors_unknown_parameter_fails_at_registration(
    obj_registry: ObjectRulesRegistry[User, bool],
) -> None:
    def older_than(user: User, age: int) -> bool:
        return user.age > age

    with pytest.raises(InvalidProcessorsError, match=r"unknown parameters \['agee'\]"):
        obj_registry.register_rule(older_than, processors={"agee": int})

    assert "older_than" not in obj_registry.rules


def test_obj_registry_processors_naming_the_object_parameter_is_rejected(
    obj_registry: ObjectRulesRegistry[User, bool],
) -> None:
    def older_than(user: User, age: int) -> bool:
        return user.age > age

    with pytest.raises(InvalidProcessorsError, match="unknown parameters"):
        obj_registry.register_rule(older_than, processors={"user": int})


@pytest.mark.parametrize("processors", [5, "int", (int, {})])
def test_obj_registry_processors_of_wrong_type_fail_at_registration(
    obj_registry: ObjectRulesRegistry[User, bool],
    processors: Any,
) -> None:
    def older_than(user: User, age: int) -> bool:
        return user.age > age

    with pytest.raises(InvalidProcessorsError, match="must be a callable or a mapping"):
        obj_registry.register_rule(older_than, processors=processors)


def test_obj_registry_invalid_processors_do_not_hide_or_register_the_rule(
    obj_registry: ObjectRulesRegistry[User, bool],
) -> None:
    def older_than(user: User, age: int) -> bool:
        return user.age > age

    with pytest.raises(InvalidProcessorsError):
        obj_registry.register_rule(older_than, processors={"agee": int}, hidden=True)

    obj_registry.register_rule(older_than)

    assert "older_than" in obj_registry.rules


def test_obj_registry_processors_failure_raises_process_argument_error(
    obj_registry: ObjectRulesRegistry[User, bool],
) -> None:
    @obj_registry.rule(processors={"age": int})
    def older_than(user: User, age: int) -> bool:
        return user.age > age

    with pytest.raises(ProcessArgumentError, match="Argument 'age' with value 'abc'"):
        older_than("abc")


def test_obj_registry_processors_do_not_mask_arity_errors(
    obj_registry: ObjectRulesRegistry[User, bool],
) -> None:
    @obj_registry.rule(processors=int)
    def older_than(user: User, age: int) -> bool:
        return user.age > age

    with pytest.raises(MissingArgumentError):
        older_than()(User(name="Test", age=20))

    with pytest.raises(TooManyArgumentsError):
        older_than("1", "2")(User(name="Test", age=20))

    with pytest.raises(UnexpectedKeywordArgumentError):
        older_than(age="1", other="2")(User(name="Test", age=20))


def test_sub_registry_processors_never_process_the_key(
    sub_registry: SubscriptableRulesRegistry[dict[str, Any], str, bool],
) -> None:
    @sub_registry.rule(processors=int)
    def is_age(obj: dict[str, Any], key: str, age: int) -> bool:
        return obj[key] == age

    assert is_age("age", "20")({"age": 20}) is True
    assert is_age(key="age", age="20")({"age": 20}) is True


def test_sub_registry_processors_naming_the_key_is_rejected(
    sub_registry: SubscriptableRulesRegistry[dict[str, Any], str, bool],
) -> None:
    def is_age(obj: dict[str, Any], key: str, age: int) -> bool:
        return obj[key] == age

    with pytest.raises(InvalidProcessorsError, match="unknown parameters"):
        sub_registry.register_rule(is_age, processors={"key": str})


def test_registered_rule_signature_excludes_the_object_parameter(
    obj_registry: ObjectRulesRegistry[User, bool],
    sub_registry: SubscriptableRulesRegistry[dict[str, Any], str, bool],
) -> None:
    @obj_registry.rule()
    def older_than(user: User, age: int) -> bool: ...

    @sub_registry.rule()
    def is_age(obj: dict[str, Any], key: str, age: int) -> bool: ...

    assert list(signature(older_than).parameters) == ["age"]
    assert list(signature(is_age).parameters) == ["key", "age"]
