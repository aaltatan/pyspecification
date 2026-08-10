from typing import Any, Literal

from pydantic import BaseModel, Field, RootModel, computed_field


class SimplePredicateSchema[T](RootModel[dict[str, list[T] | T]]):
    @property
    def _name(self) -> str:
        return next(iter(self.root.keys()))

    @computed_field
    @property
    def name(self) -> str:
        return self._name if not self.inverse else self._name[1:]

    @computed_field
    @property
    def args(self) -> list[T]:
        result = self.root[self._name]

        if not isinstance(result, list):
            return [result]

        return result

    @computed_field
    @property
    def kwargs(self) -> dict[str, T]:
        return {}

    @computed_field
    @property
    def inverse(self) -> bool:
        return self._name.startswith("-")


class PredicateSchema(BaseModel):
    name: str
    inverse: bool = False
    args: list[Any] = Field(default_factory=list)
    kwargs: dict[str, Any] = Field(default_factory=dict)


class ConditionExpressionSchema(BaseModel):
    operator: Literal["and", "or"] = "and"
    inverse: bool = False
    expressions: list["Expression"] = Field(default_factory=list, min_length=1)


Expression = ConditionExpressionSchema | SimplePredicateSchema | PredicateSchema
