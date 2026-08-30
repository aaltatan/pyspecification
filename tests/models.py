from collections.abc import Callable
from typing import Any

from pyspecification import Predicate, PredicateCompiler

type RulesDict = dict[str, Callable[..., Predicate[Any, Any]]]
type CompilerGetter = Callable[[RulesDict], PredicateCompiler]
