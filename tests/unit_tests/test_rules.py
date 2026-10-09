from dataclasses import dataclass
from typing import Any

import pytest
from pyspecification import (
    ArgumentError,
    MissingArgumentError,
    MultipleValuesArgumentError,
    PositionalOnlyArgumentError,
    Predicate,
    RuleKeyDoesNotExistError,
    TooManyArgumentsError,
    UnexpectedKeywordArgumentError,
    object_rule,
    subscriptable_rule,
)

# -----------------------
# obj rule
# -----------------------


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


admin_rule_v1 = is_admin() | (name__istartswith("admin") & age__between(18, 30))


@pytest.mark.parametrize(
    "rule1, rule2",
    [
        (
            is_admin() | name__istartswith("admin"),
            ~(~is_admin() and ~name__istartswith("admin")),
        ),
        (
            is_admin() & name__istartswith("admin"),
            ~(~is_admin() | ~name__istartswith("admin")),
        ),
        (
            ~(is_admin() | name__istartswith("admin")),
            ~is_admin() & ~name__istartswith("admin"),
        ),
        (
            ~(is_admin() & name__istartswith("admin")),
            ~is_admin() | ~name__istartswith("admin"),
        ),
    ],
)
def test_rule_and_rule(rule1: Predicate[User, bool], rule2: Predicate[User, bool]) -> None:
    user = User(name="admin", age=18, is_admin=True)
    assert rule1(user) == rule2(user)


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


def test_raising_error_when_comparing_wrong_types() -> None:
    with pytest.raises(TypeError):
        rule = age__between("2", "3")  # type: ignore  # noqa: PGH003
        rule(User(name="Abdullah", age=18, is_admin=True))


# -----------------------
# dict rule
# -----------------------


@subscriptable_rule()
def is_true(obj: dict[str, Any], key: str) -> bool:
    return obj[key] is True


@subscriptable_rule(check_key_existence=True)
def istartswith(obj: dict[str, Any], key: str, value: str) -> bool:
    return obj[key].lower().startswith(value.lower())


@subscriptable_rule()
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


def test_raising_error_when_using_key_does_not_exists_in_dict() -> None:
    rule = istartswith("does_not_exists", "some value")

    with pytest.raises(
        RuleKeyDoesNotExistError,
        match="Key 'does_not_exists' does not exist in the object of rule 'istartswith'",
    ):
        rule({"name": "Abdullah", "age": 18, "is_admin": True})


@pytest.mark.parametrize("falsy_value", [False, 0, None, "", 0.0])
def test_check_key_existence_distinguishes_falsy_value_from_missing_key(
    falsy_value: Any,
) -> None:
    """check_key_existence must use membership, not truthiness, to detect a missing key."""

    @subscriptable_rule(check_key_existence=True)
    def is_true(obj: dict[str, Any], key: str) -> bool:
        return obj[key] is True

    rule = is_true("flag")

    assert rule({"flag": falsy_value}) is False


def test_raising_error_when_using_one_key_of_forbidden_keys() -> None:

    @subscriptable_rule(forbidden_keys=("some_value",))
    def some_rule(obj: dict[str, Any], key: str, value: str) -> bool: ...

    rule = some_rule("some_value", "some value")

    with pytest.raises(
        RuleKeyDoesNotExistError,
        match="Key 'some_value' does not exist in the object of rule 'some_rule'",
    ):
        rule({"name": "Abdullah", "age": 18, "is_admin": True})


# -----------------------
# list rule
# -----------------------


@subscriptable_rule()
def seq_is_true(obj: list[Any], idx: int) -> bool:
    return obj[idx] is True


@subscriptable_rule(check_key_existence=True)
def seq_istartswith(obj: list[Any], idx: int, value: str) -> bool:
    return obj[idx].lower().startswith(value.lower())


@subscriptable_rule()
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


def test_raising_error_when_using_idx_does_not_exists_in_list() -> None:
    rule = seq_istartswith(3, "admin")

    with pytest.raises(
        RuleKeyDoesNotExistError,
        match="Key '3' does not exist in the object of rule 'seq_istartswith'",
    ):
        rule(["Abdullah", 18, True])


def test_negative_idx_within_bounds_is_valid_with_check_key_existence() -> None:
    rule = seq_istartswith(-1, "admin")
    assert rule(["Abdullah", 18, "Admin"]) is True


def test_negative_idx_out_of_bounds_raises_with_check_key_existence() -> None:
    rule = seq_istartswith(-1, "admin")

    with pytest.raises(
        RuleKeyDoesNotExistError,
        match=r"Key '-1' does not exist in the object of rule 'seq_istartswith'",
    ):
        rule([])


def test_negative_idx_beyond_bounds_raises_with_check_key_existence() -> None:
    rule = seq_istartswith(-4, "admin")

    with pytest.raises(
        RuleKeyDoesNotExistError,
        match=r"Key '-4' does not exist in the object of rule 'seq_istartswith'",
    ):
        rule(["Abdullah", 18, "Admin"])


def test_raising_error_when_using_one_idx_of_forbidden_keys() -> None:

    @subscriptable_rule(forbidden_keys=(3,))
    def some_rule(obj: list[Any], key: int, value: str) -> bool: ...

    rule = some_rule(3, "some value")

    with pytest.raises(
        RuleKeyDoesNotExistError,
        match="Key '3' does not exist in the object of rule 'some_rule'",
    ):
        rule(["Abdullah", 18, True])


# -----------------------
# argument errors
# -----------------------


def test_argument_errors_are_raised_when_the_rule_is_built_not_when_it_runs() -> None:
    with pytest.raises(MissingArgumentError, match="rule 'age__between'"):
        age__between(18)

    with pytest.raises(TooManyArgumentsError):
        age__between(1, 2, 3)

    with pytest.raises(UnexpectedKeywordArgumentError):
        age__between(1, 2, other=3)

    with pytest.raises(MultipleValuesArgumentError):
        age__between(1, min_age=2)


def test_unexpected_keyword_is_reported_before_missing_argument() -> None:
    with pytest.raises(UnexpectedKeywordArgumentError, match="'max_agee'"):
        age__between(min_age=1, max_agee=2)


def test_positional_only_argument_passed_by_keyword() -> None:
    @subscriptable_rule()
    def string__startswith(obj: dict[str, Any], key: str, value: str, /) -> bool:
        return obj[key].startswith(value)

    with pytest.raises(PositionalOnlyArgumentError, match="rule 'string__startswith'"):
        string__startswith("name", value="a")

    @object_rule()
    def named(obj: object, value: str, /, **extras: str) -> bool:
        return True

    assert named("a", value="kept in extras")(object()) is True


def test_type_error_raised_inside_the_rule_body_is_not_reclassified() -> None:
    @object_rule()
    def explode(user: User) -> bool:
        return "text" + 1  # type: ignore[operator]

    with pytest.raises(TypeError) as error:
        explode()(User(name="x", age=1, is_admin=True))

    assert not isinstance(error.value, ArgumentError)


def test_subscriptable_rule_binds_the_key_by_its_declared_name() -> None:
    @subscriptable_rule()
    def has_value(obj: dict[str, Any], field: str, value: Any) -> bool:
        return obj[field] == value

    assert has_value(field="a", value=1)({"a": 1}) is True
    assert has_value("a", 1)({"a": 1}) is True

    with pytest.raises(UnexpectedKeywordArgumentError):
        has_value(key="a", value=1)


def test_subscriptable_rule_reports_forbidden_key_given_by_keyword() -> None:
    @subscriptable_rule(forbidden_keys=("secret",))
    def has_value(obj: dict[str, Any], field: str, value: Any) -> bool:
        return obj[field] == value

    with pytest.raises(RuleKeyDoesNotExistError, match="Key 'secret'"):
        has_value(field="secret", value=1)({"secret": 1})


def test_rule_name_in_errors_prefers_the_predicate_name() -> None:
    @object_rule(predicate_name="custom_name")
    def older_than(user: User, age: int) -> bool:
        return user.age > age

    with pytest.raises(MissingArgumentError, match="rule 'custom_name'"):
        older_than()
