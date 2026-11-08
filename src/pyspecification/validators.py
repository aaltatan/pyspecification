from pyvocabulary import validate_name


def validate_python_vars_fn_naming_convention(value: str) -> str:
    return validate_name(value, error=_invalid_name)


def _invalid_name(value: object) -> ValueError:
    return ValueError(
        f"Invalid name: {value}, "
        "you should follow the python variable naming convention: "
        "name must start with a letter and can only contain letters, numbers and underscores"
    )
