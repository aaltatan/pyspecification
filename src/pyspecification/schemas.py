from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, Field, field_validator

from pyspecification.validators import validate_python_vars_fn_naming_convention


class PredicateSchema(BaseModel):
    name: Annotated[str, AfterValidator(validate_python_vars_fn_naming_convention)]
    inverse: bool = False
    args: list[Any] = Field(default_factory=list)
    kwargs: dict[str, Any] = Field(default_factory=dict)

    @field_validator("kwargs", mode="after")
    @classmethod
    def _validate_kwargs(cls, v: dict[str, Any]) -> dict[str, Any]:
        [validate_python_vars_fn_naming_convention(name) for name in v]
        return v

    @classmethod
    def from_simple_form[T](cls, root: dict[str, list[T] | T]) -> "PredicateSchema":
        inputted_name = next(iter(root.keys()))
        arguments = root[inputted_name]

        name = inputted_name.removeprefix("-")
        inverse = inputted_name.startswith("-")

        if arguments is None:
            return cls(name=name, args=[], kwargs={}, inverse=inverse)

        if isinstance(arguments, dict):
            return cls(name=name, args=[], kwargs=arguments, inverse=inverse)

        if not isinstance(arguments, list):
            return cls(name=name, args=[arguments], kwargs={}, inverse=inverse)

        return cls(name=name, args=arguments, kwargs={}, inverse=inverse)


class ConditionExpressionSchema(BaseModel):
    operator: Literal["and", "or"] = "and"
    inverse: bool = False
    expressions: list["ConditionExpressionSchema | PredicateSchema"] = Field(min_length=1)
