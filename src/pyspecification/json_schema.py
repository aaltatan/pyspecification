from collections.abc import Callable
from inspect import get_annotations
from typing import Any

from pydantic import TypeAdapter


def get_json_schema(rule: Callable[..., Any]) -> dict[str, Any]:
    schema = {
        arg: TypeAdapter(typ).json_schema()
        for idx, (arg, typ) in enumerate(get_annotations(rule).items())
        if idx > 0
    }

    return_dict = schema.pop("return", {})

    return {
        "arguments": schema,
        "return": return_dict,
        "description": rule.__doc__ or "",
    }
