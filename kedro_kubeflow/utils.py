import re


def strip_margin(text: str) -> str:
    return re.sub("\n[ \t]*\\|", "\n", text).strip()
