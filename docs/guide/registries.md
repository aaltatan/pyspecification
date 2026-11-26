# Registries

A registry is a **named vocabulary of rules**. It gives you:

- lookup by name: `registry["age__ge"]`,
- one shared operator mode for all its rules,
- the `rules` mapping a [compiler](compiling.md) and the [JSON Schema](json-schema.md) need,
- metadata: custom names, descriptions, failure messages, labels, hidden rules,
- protection against registering two rules under the same name.

There is one registry per kind of rule:

```py
ObjectRulesRegistry[T, R](operator)
SubscriptableRulesRegistry[T, K, R](*, operator, check_key_existence=False, forbidden_keys=())
```

`T` is the type of the object under test, `K` the key type (subscriptable only) and `R`
the result type (`bool`, a SQLAlchemy expression, a Django `Q`...).

## Example: HR leave eligibility

An HR system decides who may take which kind of leave. The rules live in one module and
the rest of the code uses them by name.

```python
from dataclasses import dataclass
from datetime import date

from pyspecification import ObjectRulesRegistry


@dataclass
class Employee:
    name: str
    hired_on: date
    leave_balance: int
    contract: str
    on_probation: bool = False


TODAY = date(2026, 11, 26)

leave_rules = ObjectRulesRegistry[Employee, bool](operator="logical")


@leave_rules.rule(message="You need at least one year of service")
def service_years__ge(employee: Employee, years: int) -> bool:
    """Whether the employee has worked here for at least `years` years."""
    return (TODAY - employee.hired_on).days >= years * 365


@leave_rules.rule(message="Not enough leave days left")
def balance__ge(employee: Employee, days: int) -> bool:
    return employee.leave_balance >= days


@leave_rules.rule()
def contract__in(employee: Employee, contracts: list[str]) -> bool:
    return employee.contract in contracts


@leave_rules.rule(description="Whether the employee is still on probation.")
def on_probation(employee: Employee) -> bool:
    return employee.on_probation


annual_leave = (
    leave_rules["service_years__ge"](1)
    & leave_rules["balance__ge"](10)
    & leave_rules["contract__in"](["permanent", "fixed_term"])
    & ~leave_rules["on_probation"]()
)

staff = [
    Employee("Ahmad", date(2019, 3, 1), leave_balance=21, contract="permanent"),
    Employee("Dana", date(2026, 6, 1), leave_balance=12, contract="permanent", on_probation=True),
    Employee("Yazan", date(2022, 1, 15), leave_balance=4, contract="fixed_term"),
    Employee("Reem", date(2021, 9, 1), leave_balance=30, contract="freelance"),
]

assert [e.name for e in staff if annual_leave(e)] == ["Ahmad"]
```

The decorator also **returns** the rule factory, so `balance__ge(10)` and
`leave_rules["balance__ge"](10)` are the same thing. Use the name lookup when the name
comes from data (a form, a config file, JSON).

## What a registry gives you

```python
assert list(leave_rules.rules) == ["service_years__ge", "balance__ge", "contract__in", "on_probation"]
assert leave_rules["on_probation"].__doc__ == "Whether the employee is still on probation."
```

| Member | Returns |
| --- | --- |
| `registry[name]` | the rule factory; `RuleDoesNotExistError` if unknown or hidden |
| `registry.rules` | a new `dict` of visible rule names to factories |
| `registry.labels` | a `dict` of visible rule names to their [labels](json-schema.md#labels-for-editors) |
| `registry.rule(...)` | a decorator that registers a function |
| `registry.register_rule(fn, ...)` | registers an existing function |

## Registration options

Both `rule()` and `register_rule()` take the same keyword-only options:

| Option | Effect |
| --- | --- |
| `name` | the lookup key and predicate name, instead of the function name |
| `description` | replaces the docstring: it becomes the factory's `__doc__`, the schema `description` and the fallback failure message |
| `message` | the user-facing [failure message](failures.md#messages) |
| `hidden` | keep the rule out of lookups, `rules`, `labels` and schemas |
| `label` | a human name for [editors](json-schema.md#labels-for-editors), one text or one per language |

`SubscriptableRulesRegistry.rule()` and `register_rule()` also take `check_key_existence`
and `forbidden_keys` (see [subscriptable rules](subscriptable-rules.md)).

### Registering functions you did not write

`register_rule()` registers an existing function, from a helper module or a third-party
package, without decorating it at its definition:

```python
def is_manager(employee: Employee) -> bool:
    return employee.contract == "permanent" and employee.leave_balance > 20


leave_rules.register_rule(
    is_manager,
    name="manager",
    description="Whether the employee is a manager.",
)

assert leave_rules["manager"]()(staff[0])
assert str(leave_rules["manager"]()) == "manager"
```

A lambda has no usable name, so it must be given one:

```python
leave_rules.register_rule(lambda e: e.contract == "freelance", name="is_freelancer")

try:
    leave_rules.register_rule(lambda e: True)
except ValueError as error:
    assert str(error) == "You must provide a name for the rule when using a lambda function"
```

### Valid names

Rule names must be valid Python identifiers: a letter first, then letters, digits and
underscores. Anything else is a `ValueError` at registration:

```python
try:
    leave_rules.register_rule(is_manager, name="is-manager")
except ValueError as error:
    assert str(error).startswith("Invalid name: is-manager")
```

### One rule per name

Registering a second rule under a taken name raises `RuleAlreadyRegisteredError`, so one
module cannot silently replace another's rule:

```python
from pyspecification import RuleAlreadyRegisteredError

try:

    @leave_rules.rule()
    def balance__ge(employee: Employee, days: int) -> bool:
        return True

except RuleAlreadyRegisteredError as error:
    assert str(error) == "Rule 'balance__ge' is already registered"
```

### Unknown names

Looking up an unknown name lists what is available, which makes typos in config files
easy to fix:

```python
from pyspecification import RuleDoesNotExistError

try:
    leave_rules["balance_ge"]
except RuleDoesNotExistError as error:
    assert str(error).startswith("Rule 'balance_ge' does not exist. Available rules: service_years__ge, balance__ge")
```

## Hidden rules

A hidden rule is registered (its name is taken) but invisible: not in `registry.rules`,
not in `registry.labels`, not in the JSON Schema, and `registry[name]` does not find it.
The factory returned by the decorator still works in your own code.

Use it for rules that are fine internally but must not be offered to the people who
write rules as JSON:

```python
@leave_rules.rule(hidden=True)
def is_test_account(employee: Employee) -> bool:
    return employee.name.startswith("test_")


assert "is_test_account" not in leave_rules.rules

# still usable from code
real_staff = [e for e in staff if (~is_test_account())(e)]

assert len(real_staff) == 4

try:
    leave_rules["is_test_account"]
except RuleDoesNotExistError:
    pass
```

Because the compiler only knows `registry.rules`, a JSON definition can never reach a
hidden rule.

## Subscriptable registries

`SubscriptableRulesRegistry` works the same way for [subscriptable rules](subscriptable-rules.md).
Note that its `operator` is keyword-only. `check_key_existence` and `forbidden_keys` given
to the registry are the defaults of every rule, and a rule can override them:

```python
from pyspecification import RuleKeyDoesNotExistError, SubscriptableRulesRegistry

record_rules = SubscriptableRulesRegistry[dict[str, object], str, bool](
    operator="logical",
    check_key_existence=True,
)


@record_rules.rule()
def field__eq(record: dict[str, object], key: str, value: object) -> bool:
    return record[key] == value


@record_rules.rule(check_key_existence=False)
def field__missing_or_empty(record: dict[str, object], key: str) -> bool:
    return not record.get(key)


record = {"status": "active"}

assert record_rules["field__missing_or_empty"]("email")(record)

try:
    record_rules["field__eq"]("email", "a@b.c")(record)
except RuleKeyDoesNotExistError:
    pass
```

Registry-wide `forbidden_keys` keep sensitive fields out of every rule at once. A rule's
own `forbidden_keys` **replace** the registry's, they are not added to them:

```python
staff_rules = SubscriptableRulesRegistry[dict[str, object], str, bool](
    operator="logical",
    forbidden_keys=("salary", "national_id"),
)


@staff_rules.rule()
def staff__eq(record: dict[str, object], key: str, value: object) -> bool:
    return record[key] == value


employee = {"name": "Huda", "salary": 2_400}

assert staff_rules["staff__eq"]("name", "Huda")(employee)

try:
    staff_rules["staff__eq"]("salary", 2_400)(employee)
except RuleKeyDoesNotExistError as error:
    assert "Key 'salary'" in str(error)
```

!!! note
    Up to version 4.2.0, registry-wide `forbidden_keys` were ignored. With those
    versions, pass them to each rule.

## One vocabulary, several registries

A registry is just an object, so nothing stops you from keeping two registries with the
**same rule names**: one `"logical"` for checking objects in memory, one `"bitwise"` for
building database queries. A single JSON definition then works in both places. See the
[recipe](../recipes.md#same-rules-in-memory-and-in-the-database).
