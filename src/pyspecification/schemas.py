from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, Field, RootModel, field_validator

from .validators import validate_python_vars_fn_naming_convention


class PredicateSchema(BaseModel):
    """A schema for a predicate."""

    type: Annotated[Literal["predicate"], Field(exclude=True)] = "predicate"

    name: Annotated[str, AfterValidator(validate_python_vars_fn_naming_convention)]
    inverse: bool
    args: list[Any]
    kwargs: dict[str, Any]

    @field_validator("kwargs", mode="after")
    @classmethod
    def _validate_kwargs(cls, v: dict[str, Any]) -> dict[str, Any]:
        for key in v:
            validate_python_vars_fn_naming_convention(key)

        return v


class ExpressionsWrapperSchema(BaseModel):
    """A schema for an expression."""

    type: Annotated[Literal["wrapper"], Field(exclude=True)] = "wrapper"

    operator: Literal["all", "any"]
    inverse: bool
    expressions: list["ExpressionType"] = Field(min_length=1)


ExpressionType = Annotated[
    ExpressionsWrapperSchema | PredicateSchema, Field(union_mode="left_to_right")
]


class RuleSchema(RootModel[ExpressionType]):
    """A schema for a rule."""
