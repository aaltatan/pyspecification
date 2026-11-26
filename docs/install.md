# Installation

pyspecification needs **Python 3.12 or newer**.

=== "uv"

    ```bash
    uv add pyspecification
    ```

=== "pip"

    ```bash
    pip install pyspecification
    ```

It installs two small dependencies by the same author:

| Package | What pyspecification uses it for |
| --- | --- |
| [pyargprocessors](https://github.com/aaltatan/pyargprocessors) | the `Process` marker that converts raw arguments (re-exported as `pyspecification.Process`) |
| [pyvocabulary](https://pypi.org/project/pyvocabulary/) | the rule registry, JSON Schema generation, `Label` and `Choices` |

SQLAlchemy and Django are **not** dependencies. Rules simply return whatever your rule
functions return, so the integrations work with whichever version you already use.

## Check it works

```python
from pyspecification import object_rule


@object_rule()
def is_even(number: int) -> bool:
    return number % 2 == 0


assert is_even()(4)
assert not is_even()(5)
```
