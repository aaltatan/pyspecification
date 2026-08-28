import re


def validate_python_vars_fn_naming_convention(value: str) -> str:
    """Validate the naming convention for function names.

    Args:
        value (str): The name to validate.

    Raises:
        ValueError: If the name does not follow the naming convention.

    Returns:
        str: The validated name.

    Example:
    ```python
    from pyspecification.validators import validate_python_vars_fn_naming_convention


    def main() -> None:
        assert validate_python_vars_fn_naming_convention("is_admin") == "is_admin"
        assert validate_python_vars_fn_naming_convention("isAdmin") == "is_admin"
        assert validate_python_vars_fn_naming_convention("is_1admin") == "is_1admin"
        assert validate_python_vars_fn_naming_convention("is 1admin") == "is_1admin"
        assert validate_python_vars_fn_naming_convention("is admin") == "is_admin"


    if __name__ == "__main__":
        main()
    ```

    """
    pattern = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

    if not pattern.match(value):
        msg = (
            f"Invalid name: {value}"
            "name must start with a letter and can only contain letters, numbers and underscores"
        )
        raise ValueError(msg)

    return value
