from typing import Annotated, Any, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    RootModel,
    computed_field,
    field_validator,
    model_validator,
)

from pyspecification.validators import validate_python_vars_fn_naming_convention


class SimplePredicateSchema(RootModel[dict[str, Any]]):
    @property
    def is_multiple(self) -> bool:
        return len(self.root) > 1

    @computed_field
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

    def get_condition_expression(self) -> "ConditionExpressionSchema":
        return ConditionExpressionSchema(
            expressions=[SimplePredicateSchema({key: value}) for key, value in self.root.items()],
        )

    @model_validator(mode="after")
    def validate_naming_convention(self) -> Self:
        validate_python_vars_fn_naming_convention(self.name)
        [validate_python_vars_fn_naming_convention(value) for value in self.kwargs]
        return self

    @property
    def _name(self) -> str:
        return next(iter(self.root.keys()))

    @property
    def _value(self) -> Any:
        return self.root[self._name]


class PredicateSchema(BaseModel):
    type: Literal["predicate"] = "predicate"

    name: Annotated[str, AfterValidator(validate_python_vars_fn_naming_convention)]
    inverse: bool = False
    args: list[Any] = Field(default_factory=list)
    kwargs: dict[str, Any] = Field(default_factory=dict)

    @field_validator("kwargs", mode="after")
    @classmethod
    def _validate_kwargs(cls, v: dict[str, Any]) -> dict[str, Any]:
        [validate_python_vars_fn_naming_convention(name) for name in v]
        return v


class ConditionExpressionSchema(BaseModel):
    type: Literal["condition"] = "condition"

    operator: Literal["and", "or"] = "and"
    inverse: bool = False
    expressions: list["ExpressionType"] = Field(min_length=1)


ExpressionType = ConditionExpressionSchema | PredicateSchema | SimplePredicateSchema


class ExpressionSchema(RootModel[ExpressionType]):
    pass
