import re


def strip_margin(text: str) -> str:
    return re.sub("\n[ \t]*\\|", "\n", text).strip()


def is_mlflow_enabled() -> bool:
    try:
        from kedro_mlflow.framework.context import get_mlflow_config  # NOQA
        import mlflow  # NOQA

        return True
    except ImportError:
        return False
