# API

Type parameters used below: `T` is the object under test, `K` the key of a subscriptable
rule, `R` the result of a rule (`bool`, a SQLAlchemy expression, a Django `Q`...), `P`
the rule's own parameters.

## Predicates

### `Predicate[T, R]`

```py
Predicate(
    fn: Callable[[T], R],
    /,
    *,
    operator: OperatorType,
    name: str | None = None,
    failure: Failure | None = None,
)
```

A callable wrapper around `fn` that composes with other predicates. `failure` is what
`failures()` reports when this predicate (built by hand, not by a rule decorator) fails;
without it, a `Failure` named after the predicate is reported (none for an unnamed lambda).

| Member | Description |
| --- | --- |
| `predicate(obj) -> R` | evaluate `fn(obj)` |
| `a & b`, `a \| b`, `~a` | new composed predicate; `ValueError` if the operator modes differ |
| `failures(obj) -> tuple[Failure, ...]` | the rules that make it fail for `obj`, `()` when it passes; `TypeError` for bitwise predicates |
| `str(predicate)` | its name, e.g. `(is_admin OR age__ge)`; `anonymous` for an unnamed lambda |
| `repr(predicate)` | `Predicate(<name>)` |

Guide: [Predicates](../guide/predicates.md), [Why a rule failed](../guide/failures.md).

### `OperatorType`

```py
type OperatorType = Literal["bitwise", "logical"]
```

`"logical"` combines results with `and`/`or`/`not`; `"bitwise"` with `&`/`|`/`~`.

### `Failure`

```py
@dataclass(frozen=True, slots=True)
class Failure:
    rule: str
    args: tuple[Any, ...] = ()
    kwargs: Mapping[str, Any] = {}
    negated: bool = False
    message: str | None = None
```

One reason a predicate failed. `str(failure)` renders `rule`, `rule(1, key='x')` or
`NOT rule(...)`.

## Rule decorators

### `object_rule`

```py
object_rule(
    *,
    operator: OperatorType = "logical",
    predicate_name: str | None = None,
    message: str | None = None,
) -> Callable[[Callable[Concatenate[T, P], R]], Callable[P, Predicate[T, R]]]
```

Turns `fn(obj, *args, **kwargs) -> R` into a factory `(*args, **kwargs) -> Predicate[T, R]`.
Raises `InvalidRuleError` or `InvalidProcessorError` at decoration; the factory raises
`ArgumentError` subclasses and `ProcessArgumentError` when called.

Guide: [Object rules](../guide/object-rules.md).

### `subscriptable_rule`

```py
subscriptable_rule(
    *,
    operator: OperatorType = "logical",
    predicate_name: str | None = None,
    message: str | None = None,
    check_key_existence: bool = False,
    forbidden_keys: tuple[str, ...] | tuple[int, ...] = (),
) -> Callable[[Callable[Concatenate[T, K, P], R]], Callable[Concatenate[K, P], Predicate[T, R]]]
```

Turns `fn(obj, key, *args, **kwargs) -> R` into a factory `(key, *args, **kwargs) -> Predicate[T, R]`.
The predicate raises `RuleKeyDoesNotExistError` for a forbidden key, or a missing one
when `check_key_existence` is on.

Guide: [Subscriptable rules](../guide/subscriptable-rules.md).

## Registries

### `ObjectRulesRegistry[T, R]`

```py
ObjectRulesRegistry(operator: OperatorType)
```

| Member | Description |
| --- | --- |
| `rule(*, name=None, description=None, message=None, hidden=False, label=None)` | decorator registering an object rule; returns the factory |
| `register_rule(fn, /, *, name=None, description=None, message=None, hidden=False, label=None)` | registers an existing function; returns the factory |
| `registry[name]` | the factory; `RuleDoesNotExistError` if unknown or hidden |
| `rules -> dict[str, factory]` | visible rules, a new dict on every access |
| `labels -> dict[str, Text]` | labels of visible rules that have one |

Registration raises `RuleAlreadyRegisteredError` for a taken name (hidden ones included)
and `ValueError` for an invalid name or an unnamed lambda.

### `SubscriptableRulesRegistry[T, K, R]`

```py
SubscriptableRulesRegistry(
    *,
    operator: OperatorType,
    check_key_existence: bool = False,
    forbidden_keys: tuple[str, ...] | tuple[int, ...] = (),
)
```

Same members as `ObjectRulesRegistry`; `rule()` and `register_rule()` also take
`check_key_existence: bool | None = None` and
`forbidden_keys: tuple[str, ...] | tuple[int, ...] | None = None`, where `None` uses the
registry's value.

Guide: [Registries](../guide/registries.md).

`Text` is pyvocabulary's label type: a `str`, or a `dict[str, str]` of language code to text.

## Compiler

### `PredicateCompiler[T, R]`

```py
PredicateCompiler(
    rules: dict[str, Callable[..., Predicate[T, R]]],
    initial_predicate_factory: Callable[[ExpressionWrapperDict], Predicate[T, R]],
)
```

| Member | Description |
| --- | --- |
| `compile(expression: PredicateDict \| ExpressionWrapperDict) -> Predicate[T, R]` | build the predicate; errors carry a JSON-path note such as `at $.expressions[1]` |

Raises `RuleDoesNotExistError`, `ArgumentError` subclasses, `ProcessArgumentError`, and
`TypeError` for a dictionary of the wrong shape.

### `PredicateDict`

```py
class PredicateDict(TypedDict):
    name: str
    args: list[Any]
    kwargs: dict[str, Any]
    inverse: bool
```

### `ExpressionWrapperDict`

```py
class ExpressionWrapperDict(TypedDict):
    operator: Literal["all", "any"]
    expressions: list[ExpressionWrapperDict | PredicateDict]
```

Guide: [Compiling rules from JSON](../guide/compiling.md).

## JSON Schema

| Function | Returns |
| --- | --- |
| `get_expression_json_schema(rules: Mapping[str, Callable], *, labels: Mapping[str, Text] \| None = None) -> dict` | the draft 2020-12 schema of everything `compile` accepts; `ValueError` if `labels` names an unknown rule |
| `get_rule_json_schema(name: str, rule: Callable, *, label: Text \| None = None) -> dict` | the schema of one predicate dictionary |
| `get_json_schema(annotation: Any) -> dict` | the schema of one Python type |

Guide: [JSON Schema](../guide/json-schema.md).

## Processing

### `Process`

```py
Process(fn: Callable[[Any], Any])
```

An `Annotated` marker from pyargprocessors, re-exported. `Annotated[T, Process(fn)]` on a
rule parameter applies `fn` to its value when the rule is built.

Guide: [Arguments and processing](../guide/arguments.md).

## Exceptions

See [Exceptions](exceptions.md).
