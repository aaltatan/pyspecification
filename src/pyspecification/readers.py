from typing import Any

from .schemas import ConditionExpressionSchema, PredicateSchema


def read_expression(rule_dict: dict[str, Any]) -> ConditionExpressionSchema | PredicateSchema:
    if "expressions" in rule_dict:
        return ConditionExpressionSchema(**rule_dict)

    if "name" in rule_dict:
        return PredicateSchema(**rule_dict)

    if len(rule_dict.keys()) > 1:
        return ConditionExpressionSchema(
            expressions=[
                PredicateSchema.from_simple_form(root={key: value})
                for key, value in rule_dict.items()
            ]
        )

    return PredicateSchema.from_simple_form(root=rule_dict)
