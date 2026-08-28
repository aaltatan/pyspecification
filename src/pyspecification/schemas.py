from typing import Annotated, Any, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    RootModel,
    computed_field,
    field_validator,
    model_serializer,
    model_validator,
)

from .constants import RESERVED_WORDS
from .validators import validate_python_vars_fn_naming_convention


class SimplePredicateSchema(RootModel[dict[str, Any]]):
    @computed_field(exclude_if=lambda _: True)
    @property
    def type(self) -> Literal["simple"]:
        return "simple"

    @computed_field
    @property
    def name(self) -> str:
        return self._name.removeprefix("-")

    @computed_field
    @property
    def inverse(self) -> bool:
        return self._name.startswith("-")

    @computed_field
    @property
    def args(self) -> list[Any]:
        if isinstance(self._value, list):
            return self._value

        if self._value is None or isinstance(self._value, dict):
            return []

        return [self._value]

    @computed_field
    @property
    def kwargs(self) -> dict[str, Any]:
        return self._value if isinstance(self._value, dict) else {}

    @model_validator(mode="after")
    def validate_naming_convention(self) -> Self:
        if len(self.root) > 1:
            msg = "Simple predicates can only have one key"
            raise ValueError(msg)

        validate_python_vars_fn_naming_convention(self.name)

        for key in self.kwargs:
            validate_python_vars_fn_naming_convention(key)

        return self

    @model_serializer(when_used="always")
    def serialize(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "inverse": self.inverse,
            "args": self.args,
            "kwargs": self.kwargs,
        }

    @property
    def _name(self) -> str:
        return next(iter(self.root.keys()))

    @property
    def _value(self) -> Any:
        return self.root[self._name]


class PredicateSchema(BaseModel):
    type: Annotated[Literal["predicate"], Field(exclude=True)] = "predicate"

    name: Annotated[str, AfterValidator(validate_python_vars_fn_naming_convention)]
    inverse: bool = False
    args: list[Any] = Field(default_factory=list)
    kwargs: dict[str, Any] = Field(default_factory=dict)

    @field_validator("kwargs", mode="after")
    @classmethod
    def _validate_kwargs(cls, v: dict[str, Any]) -> dict[str, Any]:
        for key in v:
            validate_python_vars_fn_naming_convention(key)

        return v


class ExpressionsWrapperSchema(BaseModel):
    type: Annotated[Literal["wrapper"], Field(exclude=True)] = "wrapper"

    operator: Literal["and", "or"] = "and"
    inverse: bool = False
    expressions: list["ExpressionType"] = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def parse_simple_multiple_keys_predicate(cls, data: dict[str, Any]) -> dict[str, Any]:
        if (
            isinstance(data, dict)
            and not any(key in RESERVED_WORDS for key in data)
            and len(data) > 1
        ):
            return {
                "operator": "and",
                "inverse": False,
                "expressions": [{key: value} for key, value in data.items()],
            }

        return data


ExpressionType = Annotated[
    ExpressionsWrapperSchema | PredicateSchema | SimplePredicateSchema,
    Field(union_mode="left_to_right"),
]


class RuleSchema(RootModel[ExpressionType]):
    pass
