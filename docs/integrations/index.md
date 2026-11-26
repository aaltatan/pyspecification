# Integrations

pyspecification does not import any ORM. It works with them because a rule may return
**anything that supports `&`, `|` and `~`**, and a `"bitwise"` predicate combines results
with exactly those operators.

So a rule that returns a SQLAlchemy condition or a Django `Q` object composes into a
bigger condition, which the ORM turns into a SQL `WHERE` clause. The filtering then
happens in the database, not in Python.

| ORM | The object under test | A rule returns | Neutral elements for the compiler |
| --- | --- | --- | --- |
| [SQLAlchemy](sqlalchemy.md) | the model class | `ColumnElement[bool]` | `true()` for `all`, `false()` for `any` |
| [Django](django.md) | ignored (`_`) | `Q` | `Q()` for both |

The same rule **names** can have an in-memory (`"logical"`) and a database (`"bitwise"`)
implementation, so one stored JSON rule can both filter a table and explain to a user why
their row does not match. See the
[recipe](../recipes.md#same-rules-in-memory-and-in-the-database).
