# JSON Schema

pyspecification generates [JSON Schema](https://json-schema.org/) (draft 2020-12) straight
from your rule signatures. The schemas describe **exactly** what
[`PredicateCompiler.compile`](compiling.md) accepts, so you can hand them to:

- a front-end **rule editor** that builds forms from the schema,
- a **validator** that rejects bad payloads before they reach the compiler,
- an **LLM** that writes rules as JSON from a sentence like "customers in Aleppo who
  ordered more than 5 times",
- your **API docs** (OpenAPI uses JSON Schema).

There are three functions:

| Function | Describes |
| --- | --- |
| `get_expression_json_schema(rules, *, labels=None)` | everything the compiler accepts: any rule, nested in `all`/`any` wrappers |
| `get_rule_json_schema(name, rule, *, label=None)` | one predicate dictionary |
| `get_json_schema(annotation)` | one Python type |

## A whole expression

Example: a SaaS company lets account managers build rules over its customer accounts.

```python
from typing import Annotated

from pyvocabulary import Choices, Label

from pyspecification import ObjectRulesRegistry, get_expression_json_schema, get_rule_json_schema

accounts = ObjectRulesRegistry[dict[str, object], bool](operator="logical")

Plan = Annotated[str, Choices({"free": {"en": "Free", "ar": "مجاني"}, "pro": "Pro", "enterprise": "Enterprise"})]


@accounts.rule(label={"en": "Plan is", "ar": "الخطة هي"})
def plan__eq(account: dict[str, object], value: Plan) -> bool:
    """The subscription plan equals the value."""
    return account["plan"] == value


@accounts.rule(label="Seats at least")
def seats__ge(
    account: dict[str, object],
    minimum: Annotated[int, Label("Minimum seats", description="Paid seats only")],
    *,
    include_trial: bool = False,
) -> bool:
    seats = account["seats"] + (account["trial_seats"] if include_trial else 0)
    return seats >= minimum


@accounts.rule(hidden=True)
def is_internal(account: dict[str, object]) -> bool:
    return account["domain"] == "ourcompany.com"


schema = get_expression_json_schema(accounts.rules, labels=accounts.labels)
```

The root is a `$ref` to an `expression`, which is `oneOf` the rule schemas plus a
recursive `wrapper`:

```python
assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
assert schema["$ref"] == "#/$defs/expression"
assert schema["x-kind"] == "predicate"

choices = schema["$defs"]["expression"]["oneOf"]

assert [c.get("properties", {}).get("name") for c in choices] == [
    {"const": "plan__eq"},
    {"const": "seats__ge"},
    None,  # the wrapper reference
]
assert choices[-1] == {"$ref": "#/$defs/wrapper"}
assert schema["$defs"]["wrapper"]["properties"]["operator"] == {"enum": ["all", "any"], "type": "string"}
```

The hidden rule `is_internal` is not in the schema, because it is not in
`accounts.rules`.

## One rule

Each rule's schema is an object with exactly `name`, `args`, `kwargs` and `inverse`:

```python
seats = get_rule_json_schema("seats__ge", seats__ge)

assert seats["required"] == ["name", "args", "kwargs", "inverse"]
assert seats["additionalProperties"] is False
assert seats["properties"]["inverse"] == {"type": "boolean"}
```

- **`args`** lists the parameters that can be passed positionally, in order, with
  `prefixItems`; `"items": false` forbids extra items.
- **`kwargs`** lists every parameter that can be passed by name, including keyword-only
  ones. Its `required` is empty because a required parameter may come through `args`
  instead; the compiler still reports a missing one.
- Defaults that are plain JSON values are included as `default`.
- The object under test is never in the schema. For subscriptable rules, the key is the
  first item of `args`.

```python
assert seats["properties"]["args"] == {
    "type": "array",
    "prefixItems": [{"type": "integer", "x-label": "Minimum seats", "x-description": "Paid seats only"}],
    "items": False,
}
assert seats["properties"]["kwargs"]["properties"]["include_trial"] == {"type": "boolean", "default": False}
assert seats["properties"]["kwargs"]["required"] == []
```

The description comes from the rule's `description=` or docstring:

```python
assert get_rule_json_schema("plan__eq", plan__eq)["description"] == "The subscription plan equals the value."
```

## Labels for editors

People should see "Plan is", not `plan__eq`. pyspecification adds a few `x-` keywords
(JSON Schema ignores unknown keywords, so validators are unaffected):

| Keyword | Where | From |
| --- | --- | --- |
| `x-kind: "predicate"` | schema root | always; tells an editor what kind of expression this is |
| `x-label` | a rule | `label=` on `rule()` / `register_rule()`, passed via `labels=registry.labels` |
| `x-field`, `x-operator` | a rule | its name split at the **last** `__`: `plan__eq` → `plan`, `eq` |
| `x-label`, `x-description` | an argument | `Annotated[T, Label("...", description="...")]` |
| `enum`, `x-choices` | an argument | `Annotated[T, Choices({value: label, ...})]` |

A label is one string or one string per language:

```python
plan = choices[0]

assert plan["x-label"] == {"en": "Plan is", "ar": "الخطة هي"}
assert (plan["x-field"], plan["x-operator"]) == ("plan", "eq")
assert plan["properties"]["args"]["prefixItems"][0] == {
    "type": "string",
    "enum": ["free", "pro", "enterprise"],
    "x-choices": [
        {"value": "free", "label": {"en": "Free", "ar": "مجاني"}},
        {"value": "pro", "label": "Pro"},
        {"value": "enterprise", "label": "Enterprise"},
    ],
}
```

With `x-field` and `x-operator` an editor can show a field picker ("Plan", "Seats"),
then the operators available for it ("is", "at least"), then the argument inputs.

`Label` and `Choices` come from [pyvocabulary](https://pypi.org/project/pyvocabulary/),
installed with pyspecification. A label for a rule that is not in `rules` is a mistake:

```python
try:
    get_expression_json_schema(accounts.rules, labels={"plan__equals": "Plan is"})
except ValueError as error:
    assert str(error) == "Labels for unknown rules: plan__equals"
```

## Validating payloads

Any JSON Schema validator works. With the
[`jsonschema`](https://pypi.org/project/jsonschema/) package:

```py
from jsonschema import Draft202012Validator

validator = Draft202012Validator(schema)

errors = [e.message for e in validator.iter_errors(payload_from_the_browser)]

if not errors:
    rule = compiler.compile(payload_from_the_browser)
```

## Letting an LLM write rules

The expression schema is a ready-made tool input schema. With the Anthropic SDK:

```py
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-opus-5-5",
    max_tokens=1024,
    tools=[
        {
            "name": "filter_accounts",
            "description": "Filter customer accounts with a rule.",
            "input_schema": {
                "type": "object",
                "properties": {"rule": schema},
                "required": ["rule"],
            },
        }
    ],
    tool_choice={"type": "tool", "name": "filter_accounts"},
    messages=[{"role": "user", "content": "Pro accounts with at least 50 seats"}],
)

rule = compiler.compile(response.content[0].input["rule"])
```

Rule docstrings become schema descriptions, so a good docstring is also a good prompt.
Always compile what the model returns inside a `try`: compiling is where bad names and
arguments are caught.

## Supported types

`get_json_schema(annotation)` maps Python annotations. Unknown or unannotated types map to
`{}`, which accepts any value.

| Python annotation | JSON Schema |
| --- | --- |
| `str`, `int`, `float`, `bool`, `None` | `string`, `integer`, `number`, `boolean`, `null` |
| `Decimal` | `number` |
| `datetime`, `date`, `time`, `UUID` | `string` with format `date-time`, `date`, `time`, `uuid` |
| `list[T]`, `set[T]`, `frozenset[T]`, `tuple[T, ...]` | `array` of `T` |
| `dict[K, V]` | `object` with `V` as `additionalProperties` |
| `Literal[...]`, `Enum` subclasses | `enum` of the values, plus `"type": "string"` when all are strings |
| `A \| B`, `Optional[A]` | `anyOf` |
| `TypedDict` | `object` with `properties` and `required` (`Required` / `NotRequired` honoured) |
| `Annotated[T, ...]`, `type` aliases | the schema of `T` |

```python
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Literal, NotRequired, TypedDict

from pyspecification import get_json_schema


class Status(Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class Address(TypedDict):
    city: str
    postcode: NotRequired[str]


assert get_json_schema(Decimal) == {"type": "number"}
assert get_json_schema(date) == {"type": "string", "format": "date"}
assert get_json_schema(dict[str, int]) == {"type": "object", "additionalProperties": {"type": "integer"}}
assert get_json_schema(Status) == {"enum": ["active", "suspended"], "type": "string"}
assert get_json_schema(Literal["asc", "desc"]) == {"enum": ["asc", "desc"], "type": "string"}
assert get_json_schema(int | None) == {"anyOf": [{"type": "integer"}, {"type": "null"}]}
assert get_json_schema(Address) == {
    "type": "object",
    "properties": {"city": {"type": "string"}, "postcode": {"type": "string"}},
    "required": ["city"],
}
```

Limits worth knowing:

- A fixed-size tuple such as `tuple[int, str]` is described by its first member only
  (`array` of `integer`).
- String annotations are evaluated when possible and fall back to `{}` otherwise.

### Processed arguments

A parameter with a [`Process`](arguments.md) marker is described by what the **processor
accepts**, because that is what the JSON has to send:

```python
from pathlib import Path

from pyspecification import Process, object_rule


def load_names(path: str) -> frozenset[str]:
    return frozenset(Path(path).read_text("utf-8").split())


@object_rule()
def email__in_file(account: dict[str, str], names: Annotated[frozenset[str], Process(load_names)]) -> bool:
    return account["email"] in names


args = get_rule_json_schema("email__in_file", email__in_file)["properties"]["args"]

assert args["prefixItems"] == [{"type": "string"}]  # a path, not a set
```

A processor without a parameter annotation (such as `int` or `str.strip`) falls back to
the annotated type: `Annotated[int, Process(int)]` is `integer`.
