from collections.abc import Callable
from inspect import get_annotations
from typing import Any

from pydantic import TypeAdapter


def get_rules_schema(
    rules: dict[str, Callable[..., Any]], *, sort_by_name: bool = True
) -> dict[str, Any]:
    schema = {
        name: {**_get_annotations(fn), "description": fn.__doc__ or ""}
        for name, fn in rules.items()
    }

    if sort_by_name:
        schema = dict(sorted(schema.items(), key=lambda item: item[0]))

    return schema


def _get_annotations(fn: Callable[..., Any]) -> dict[str, Any]:
    return {
        arg: TypeAdapter(typ).json_schema()
        for arg, typ in get_annotations(fn).items()
        if arg not in ("return", "obj")
    }
