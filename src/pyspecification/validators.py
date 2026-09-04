import re


def validate_python_vars_fn_naming_convention(value: str) -> str:
    pattern = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

    if not pattern.match(value):
        msg = (
            f"Invalid name: {value}, "
            "you should follow the python variable naming convention: "
            "name must start with a letter and can only contain letters, numbers and underscores"
        )
        raise ValueError(msg)

    return value
