from dataclasses import dataclass
from typing import Annotated, Any

import pytest
from pyspecification import (
    ObjectRulesRegistry,
    SubscriptableRulesRegistry,
    get_expression_json_schema,
    get_rule_json_schema,
)
from pyvocabulary import Choices, Label

AGE_GE = {"en": "Age at least", "ar": "العمر لا يقل عن"}
TIER = Annotated[str, Choices({"gold": {"en": "Gold", "ar": "ذهبي"}, "silver": "Silver"})]


@dataclass
class Customer:
    age: int
    tier: str
    is_vip: bool


@pytest.fixture
def registry() -> ObjectRulesRegistry[Customer, bool]:
    registry = ObjectRulesRegistry[Customer, bool]("logical")

    @registry.rule(label=AGE_GE)
    def age__ge(customer: Customer, minimum: Annotated[int, Label("Minimum")]) -> bool:
        return customer.age >= minimum

    @registry.rule(label="Tier is")
    def tier__eq(customer: Customer, value: TIER) -> bool:
        return customer.tier == value

    @registry.rule()
    def is_vip(customer: Customer) -> bool:
        return customer.is_vip

    @registry.rule(hidden=True, label="Secret")
    def secret(customer: Customer) -> bool:
        return customer.is_vip

    return registry


class TestRegistryLabels:
    def test_object_registry_keeps_labels_of_visible_rules(self, registry: Any) -> None:
        assert registry.labels == {"age__ge": AGE_GE, "tier__eq": "Tier is"}

    def test_subscriptable_registry_keeps_labels(self) -> None:
        registry = SubscriptableRulesRegistry[dict[str, Any], str, bool](operator="logical")

        @registry.rule(label="At least")
        def int__ge(row: dict[str, Any], key: str, value: int) -> bool:
            return row[key] >= value

        registry.register_rule(lambda row, key: bool(row[key]), name="is_set", label="Is set")

        assert registry.labels == {"int__ge": "At least", "is_set": "Is set"}

    def test_register_rule_takes_a_label(self) -> None:
        registry = ObjectRulesRegistry[Customer, bool]("logical")

        registry.register_rule(lambda customer: customer.is_vip, name="is_vip", label="VIP")

        assert registry.labels == {"is_vip": "VIP"}

    def test_invalid_label_is_rejected(self) -> None:
        registry = ObjectRulesRegistry[Customer, bool]("logical")

        with pytest.raises(TypeError, match="label"):
            registry.register_rule(lambda customer: customer.is_vip, name="is_vip", label="")


class TestRuleSchema:
    def test_field_and_operator_come_from_the_name(self, registry: Any) -> None:
        schema = get_rule_json_schema("age__ge", registry["age__ge"])

        assert (schema["x-field"], schema["x-operator"]) == ("age", "ge")

    def test_the_last_double_underscore_splits(self, registry: Any) -> None:
        schema = get_rule_json_schema("employee__age__ge", registry["age__ge"])

        assert (schema["x-field"], schema["x-operator"]) == ("employee__age", "ge")

    def test_a_name_without_double_underscore_has_no_split(self, registry: Any) -> None:
        schema = get_rule_json_schema("is_vip", registry["is_vip"])

        assert "x-field" not in schema
        assert "x-operator" not in schema

    def test_label_and_argument_markers(self, registry: Any) -> None:
        schema = get_rule_json_schema("age__ge", registry["age__ge"], label=AGE_GE)

        assert schema["x-label"] == AGE_GE
        assert schema["properties"]["args"]["prefixItems"] == [
            {"type": "integer", "x-label": "Minimum"}
        ]

    def test_choices_are_written_inline(self, registry: Any) -> None:
        schema = get_rule_json_schema("tier__eq", registry["tier__eq"])

        assert schema["properties"]["args"]["prefixItems"] == [
            {
                "type": "string",
                "enum": ["gold", "silver"],
                "x-choices": [
                    {"value": "gold", "label": {"en": "Gold", "ar": "ذهبي"}},
                    {"value": "silver", "label": "Silver"},
                ],
            }
        ]


class TestExpressionSchema:
    def test_root_is_a_predicate(self, registry: Any) -> None:
        assert get_expression_json_schema(registry.rules)["x-kind"] == "predicate"

    def test_rules_carry_their_labels(self, registry: Any) -> None:
        schema = get_expression_json_schema(registry.rules, labels=registry.labels)
        labels = {
            rule["properties"]["name"]["const"]: rule.get("x-label")
            for rule in schema["$defs"]["expression"]["oneOf"]
            if "properties" in rule
        }

        assert labels == {"age__ge": AGE_GE, "tier__eq": "Tier is", "is_vip": None}

    def test_label_for_an_unknown_rule_is_rejected(self, registry: Any) -> None:
        with pytest.raises(ValueError, match="Labels for unknown rules: age__lt"):
            get_expression_json_schema(registry.rules, labels={"age__lt": "Younger than"})
