import re


def strip_margin(text: str) -> str:
    return re.sub("\n[ \t]*\\|", "\n", text).strip()


def clean_name(name: str) -> str:
    return re.sub(r"[\W_]+", "-", name).strip("-")


def is_mlflow_enabled() -> bool:
    try:
        import kedro_mlflow  # NOQA
        import mlflow  # NOQA

        return True
    except ImportError:
        return False
