from typing import Any

from pyspecification import SubscriptablePredicateRegistry

predicates = SubscriptablePredicateRegistry[dict[str, Any], str, bool]()


@predicates.rule()
def eq(employee: dict[str, Any], key: str, value: Any) -> bool:
    return employee[key] == value


@predicates.rule()
def le(employee: dict[str, Any], key: str, value: int) -> bool:
    return employee[key] <= value


@predicates.rule()
def ge(employee: dict[str, Any], key: str, value: int) -> bool:
    return employee[key] >= value


@predicates.rule()
def lt(employee: dict[str, Any], key: str, value: int) -> bool:
    return employee[key] < value


@predicates.rule()
def gt(employee: dict[str, Any], key: str, value: int) -> bool:
    return employee[key] > value


@predicates.rule()
def is_true(employee: dict[str, Any], key: str) -> bool:
    return employee[key] is True


@predicates.rule()
def is_false(employee: dict[str, Any], key: str) -> bool:
    return employee[key] is False
