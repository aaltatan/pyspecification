import pytest
from pyspecification import Predicate, PredicateCompiler

from .models import CompilerGetter, RulesDict


@pytest.fixture
def logical_compiler_getter() -> CompilerGetter:
    def inner(rules: RulesDict) -> PredicateCompiler:
        return PredicateCompiler(
            rules=rules,
            initial_predicate_factory=lambda schema: Predicate(
                lambda _: schema["operator"] == "all",
                operator="logical",
            ),
        )

    return inner
