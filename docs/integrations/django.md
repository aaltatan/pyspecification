# Django

Rules return Django [`Q` objects](https://docs.djangoproject.com/en/stable/topics/db/queries/#complex-lookups-with-q-objects).
`Q` already supports `&`, `|` and `~`, so a `"bitwise"` registry composes them into one
lookup that `QuerySet.filter()` turns into SQL. pyspecification needs no Django adapter
and no settings.

The object under test is not needed (a `Q` describes a lookup, not a value), so rules
take it as `_`.

!!! note
    The examples on this page need a Django project, so unlike the rest of the docs they
    are not executed by the test suite.

## Example: a helpdesk ticket queue

Support agents filter the ticket queue with saved views such as "urgent tickets from
enterprise customers that nobody has picked up".

### `models.py`

```py
from django.db import models


class Ticket(models.Model):
    class Priority(models.TextChoices):
        LOW = "low"
        NORMAL = "normal"
        URGENT = "urgent"

    subject = models.CharField(max_length=200)
    priority = models.CharField(max_length=10, choices=Priority.choices)
    status = models.CharField(max_length=20, default="open")
    customer_plan = models.CharField(max_length=20)
    assignee = models.ForeignKey("auth.User", null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
```

### `rules.py`

```py
from datetime import timedelta
from typing import Annotated, Any

from django.db.models import Q
from django.utils import timezone
from pyvocabulary import Choices, Label

from pyspecification import ObjectRulesRegistry, Predicate, PredicateCompiler

from .models import Ticket

ticket_rules = ObjectRulesRegistry[Any, Q](operator="bitwise")

Priority = Annotated[str, Choices({value: label for value, label in Ticket.Priority.choices})]


@ticket_rules.rule(label="Priority is")
def priority__eq(_: Any, value: Priority) -> Q:
    """The ticket has this priority."""
    return Q(priority=value)


@ticket_rules.rule(label="Status is one of")
def status__in(_: Any, values: list[str]) -> Q:
    """The ticket status is one of the values."""
    return Q(status__in=values)


@ticket_rules.rule(label="Customer plan is")
def plan__eq(_: Any, value: str) -> Q:
    """The customer is on this plan."""
    return Q(customer_plan=value)


@ticket_rules.rule(label="Unassigned")
def unassigned(_: Any) -> Q:
    """Nobody has picked the ticket up."""
    return Q(assignee__isnull=True)


@ticket_rules.rule(label="Older than (hours)")
def age_hours__gt(_: Any, hours: Annotated[int, Label("Hours")]) -> Q:
    """The ticket was opened more than this many hours ago."""
    return Q(created_at__lt=timezone.now() - timedelta(hours=hours))


compiler = PredicateCompiler[Any, Q](
    ticket_rules.rules,
    lambda _: Predicate(lambda _: Q(), operator="bitwise"),
)
```

`Q()` is empty and disappears when combined (`Q() & Q(a=1)` is `Q(a=1)`), so it is the
neutral element for both `all` and `any`. Note that an **empty** `any` group therefore
matches everything, like an empty `all`.

!!! warning "Time-relative rules"
    `age_hours__gt` reads the clock when the rule is **built**. Compile saved views per
    request (as below), not once at import time, or "older than 4 hours" will be
    measured from the moment the server started.

### `managers` on the model

A small `QuerySet` method keeps views tidy:

```py
from typing import Any, Self

from django.db import models
from django.db.models import Q

from pyspecification import Predicate


class TicketQuerySet(models.QuerySet):
    def matching(self, rule: Predicate[Any, Q]) -> Self:
        return self.filter(rule(self.model))


class Ticket(models.Model):
    ...

    objects = TicketQuerySet.as_manager()
```

### `views.py`

The browser posts a rule as JSON. Errors from compiling are sent back with the JSON path
of the bad expression, so the rule editor can highlight it:

```py
import json

from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_POST

from pyargprocessors import PyargprocessorsError
from pyspecification import PySpecificationError

from .models import Ticket
from .rules import compiler


@require_POST
def search_tickets(request: HttpRequest) -> JsonResponse:
    try:
        rule = compiler.compile(json.loads(request.body))
    except (PySpecificationError, PyargprocessorsError) as error:
        return JsonResponse({"error": str(error), "at": getattr(error, "__notes__", [])}, status=400)
    except TypeError as error:  # not a predicate or wrapper at all
        return JsonResponse({"error": str(error)}, status=400)

    tickets = Ticket.objects.matching(rule).order_by("-created_at")[:50]

    return JsonResponse({"tickets": [{"id": t.id, "subject": t.subject} for t in tickets]})
```

A saved view "urgent enterprise tickets nobody picked up in 4 hours":

```json
{
  "operator": "all",
  "expressions": [
    {"name": "priority__eq", "args": ["urgent"], "kwargs": {}, "inverse": false},
    {"name": "plan__eq", "args": ["enterprise"], "kwargs": {}, "inverse": false},
    {"name": "unassigned", "args": [], "kwargs": {}, "inverse": false},
    {"name": "age_hours__gt", "args": [4], "kwargs": {}, "inverse": false},
    {"name": "status__in", "args": [["closed", "solved"]], "kwargs": {}, "inverse": true}
  ]
}
```

becomes

```py
Q(priority="urgent") & Q(customer_plan="enterprise") & Q(assignee__isnull=True)
& Q(created_at__lt=...) & ~Q(status__in=["closed", "solved"])
```

### Serving the schema to the rule editor

```py
from django.http import HttpRequest, JsonResponse

from pyspecification import get_expression_json_schema

from .rules import ticket_rules


def ticket_rule_schema(request: HttpRequest) -> JsonResponse:
    return JsonResponse(get_expression_json_schema(ticket_rules.rules, labels=ticket_rules.labels))
```

## Things to know

- `Q` lookups span relations (`Q(customer__country="SY")`), so a rule can filter on any
  related model.
- Rules may also return `Exists(...)` subqueries or other expressions that support `&`,
  `|` and `~`.
- `failures()` is not available on bitwise predicates. To tell an agent why one ticket is
  not in a view, keep a logical twin of the rules; see the
  [recipe](../recipes.md#same-rules-in-memory-and-in-the-database).
