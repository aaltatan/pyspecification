# Upgrading

## From 3.x to 4.x

**`processors=` is gone.** Annotate the parameters with `Process` instead.

=== "3.x"

    ```py
    @registry.rule(processors=int)
    def age__ge(user, value): ...


    @registry.rule(processors={"age": int})
    def age__between(user, age, other): ...
    ```

=== "4.x"

    ```py
    from typing import Annotated

    from pyspecification import Process


    @registry.rule()
    def age__ge(user, value: Annotated[int, Process(int)]): ...


    @registry.rule()
    def age__between(user, age: Annotated[int, Process(int)], other): ...
    ```

Other changes:

- `ProcessArgumentError` and `InvalidProcessorError` now come from pyargprocessors (still
  re-exported) and derive from `PyargprocessorsError`, **not** `PySpecificationError`.
  Catch both bases where you caught `PySpecificationError` before.
- Argument errors are raised when a rule is **built**, not when its predicate is called.
- A keyword-passed positional-only parameter (such as `key=` for a rule declared
  `key, value, /`) is now a `PositionalOnlyArgumentError`.

## From 2.x to 3.x

- `get_rule_json_schema(rule)` used to return a flat `{parameter: schema, "return": schema}`
  mapping. It now takes the rule name first, `get_rule_json_schema(name, rule)`, and
  returns the schema of the whole predicate dictionary
  (see [JSON Schema](../guide/json-schema.md#one-rule)).
- `get_json_schema` is exported from the package root.
