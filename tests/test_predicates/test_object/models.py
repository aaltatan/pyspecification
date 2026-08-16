from dataclasses import dataclass
from typing import Literal


@dataclass(kw_only=True, frozen=True)
class Employee:
    name: str
    age: int
    salary: float
    is_active: bool = True
    gender: Literal["male", "female"]
