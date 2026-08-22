from collections.abc import Callable
from inspect import get_annotations
from typing import Any

from pydantic import TypeAdapter


def get_json_schema(
    rule: Callable[..., Any],
    *,
    include_first_argument: bool = False,
) -> dict[str, Any]:
    if include_first_argument:
        return {arg: TypeAdapter(typ).json_schema() for arg, typ in get_annotations(rule).items()}

    return {
        arg: TypeAdapter(typ).json_schema()
        for idx, (arg, typ) in enumerate(get_annotations(rule).items())
        if idx > 0
    }
