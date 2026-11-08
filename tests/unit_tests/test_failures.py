from dataclasses import dataclass
from typing import Any

import pytest

from pyspecification import (
    Failure,
    ObjectRulesRegistry,
    Predicate,
    PredicateCompiler,
    SubscriptableRulesRegistry,
    object_rule,
)


@dataclass
class User:
    name: str
    age: int
    email: str
    is_admin: bool = False


@object_rule()
def is_admin(user: User) -> bool:
    return user.is_admin


@object_rule()
def age__between(user: User, minimum: int, maximum: int = 120) -> bool:
    return minimum <= user.age <= maximum


@object_rule()
def email__endswith(user: User, domain: str) -> bool:
    return user.email.endswith(domain)


ADULT = User("Sara", 30, "sara@company.com")
TEEN = User("Omar", 16, "omar@gmail.com", is_admin=True)


def rules_of(failures: tuple[Failure, ...]) -> list[str]:
    return [str(failure) for failure in failures]


class TestLeaf:
    def test_passing_rule_has_no_failures(self):
        assert age__between(18).failures(ADULT) == ()

    def test_failing_rule_reports_its_name_and_arguments(self):
        assert age__between(18).failures(TEEN) == (Failure("age__between", (18,)),)

    def test_arguments_are_reported_as_bound(self):
        # The same rule gives the same failure however its arguments were passed.
        assert age__between(18, maximum=65).failures(TEEN) == age__between(
            18, 65
        ).failures(TEEN)
        assert age__between(18, maximum=65).failures(TEEN)[0].args == (18, 65)

    def test_keyword_only_arguments_are_reported_as_kwargs(self):
        @object_rule()
        def name__eq(user: User, *, name: str) -> bool:
            return user.name == name

        assert name__eq(name="Ali").failures(ADULT) == (
            Failure("name__eq", (), {"name": "Ali"}),
        )

    def test_failure_str_reads_like_a_call(self):
        assert (
            str(Failure("age__between", (18,), {"maximum": 65}))
            == "age__between(18, maximum=65)"
        )
        assert str(Failure("is_admin")) == "is_admin"
        assert str(Failure("is_admin", negated=True)) == "NOT is_admin"

    def test_processed_arguments_are_reported(self):
        @object_rule()
        def name__eq(user: User, name: str) -> bool:
            return user.name == name

        assert name__eq("Ali").failures(ADULT)[0].args == ("Ali",)

    def test_plain_predicate_reports_its_function_name(self):
        def is_named(user: User) -> bool:
            return bool(user.name == "nobody")

        assert rules_of(Predicate(is_named, operator="logical").failures(ADULT)) == [
            "is_named"
        ]

    def test_lambda_predicate_is_not_reported(self):
        assert Predicate(lambda _: False, operator="logical").failures(ADULT) == ()


class TestComposition:
    def test_and_lists_every_failing_side(self):
        rule = age__between(18) & email__endswith("@company.com") & is_admin()
        assert rules_of(rule.failures(TEEN)) == [
            "age__between(18)",
            "email__endswith('@company.com')",
        ]

    def test_and_passing_has_no_failures(self):
        assert (age__between(18) & email__endswith("@company.com")).failures(
            ADULT
        ) == ()

    def test_or_passing_on_one_side_has_no_failures(self):
        assert (is_admin() | age__between(18)).failures(ADULT) == ()

    def test_or_failing_lists_both_sides(self):
        rule = is_admin() | email__endswith("@company.com")
        assert rules_of(rule.failures(User("Ali", 40, "ali@gmail.com"))) == [
            "is_admin",
            "email__endswith('@company.com')",
        ]

    def test_not_reports_the_rule_that_passed_as_negated(self):
        assert (~is_admin()).failures(TEEN) == (Failure("is_admin", negated=True),)

    def test_not_passing_has_no_failures(self):
        assert (~is_admin()).failures(ADULT) == ()

    def test_double_negation_is_not_negated(self):
        assert (~~is_admin()).failures(ADULT) == (Failure("is_admin"),)

    def test_negated_group_is_reported_by_name(self):
        rule = ~(age__between(18) & email__endswith("@company.com"))
        assert rules_of(rule.failures(ADULT)) == [
            "NOT (age__between AND email__endswith)"
        ]

    def test_nested_groups(self):
        rule = is_admin() | (age__between(18) & email__endswith("@company.com"))
        assert rules_of(rule.failures(User("Ali", 16, "ali@company.com"))) == [
            "is_admin",
            "age__between(18)",
        ]

    def test_failures_matches_the_predicate_result(self):
        rule = (is_admin() | age__between(18)) & ~email__endswith("@gmail.com")
        for user in (ADULT, TEEN, User("Ali", 16, "ali@company.com")):
            assert bool(rule.failures(user)) is (not rule(user))


class TestCompilerAndRegistries:
    def test_compiled_any_group_does_not_report_the_initial_predicate(self):
        compiler = PredicateCompiler[User, bool](
            {"is_admin": is_admin, "email__endswith": email__endswith},
            lambda wrapper: Predicate(
                lambda _: wrapper["operator"] == "all", operator="logical"
            ),
        )
        rule = compiler.compile(
            {
                "operator": "any",
                "expressions": [
                    {"name": "is_admin", "args": [], "kwargs": {}, "inverse": False},
                    {
                        "name": "email__endswith",
                        "args": ["@company.com"],
                        "kwargs": {},
                        "inverse": False,
                    },
                ],
            }
        )

        assert rules_of(rule.failures(User("Ali", 40, "ali@gmail.com"))) == [
            "is_admin",
            "email__endswith('@company.com')",
        ]

    def test_registry_name_is_reported(self):
        registry = ObjectRulesRegistry[User, bool](operator="logical")

        @registry.rule(name="is_staff")
        def staff(user: User) -> bool:
            return user.email.endswith("@company.com")

        assert registry["is_staff"]().failures(TEEN) == (Failure("is_staff"),)

    def test_subscriptable_rule_reports_the_key(self):
        registry = SubscriptableRulesRegistry[dict[str, Any], str, bool](
            operator="logical"
        )

        @registry.rule()
        def int__ge(data: dict[str, Any], key: str, value: int) -> bool:
            return data[key] >= value

        assert registry["int__ge"]("age", 18).failures({"age": 3}) == (
            Failure("int__ge", ("age", 18)),
        )


class TestBitwise:
    def test_bitwise_predicates_cannot_explain(self):
        rule = Predicate(lambda _: True, operator="bitwise", name="is_admin")
        with pytest.raises(TypeError, match="failures\\(\\) needs a logical predicate"):
            rule.failures(ADULT)
