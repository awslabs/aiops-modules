from hashlib import md5
from typing import Any


def generate_unique_id(*args: Any) -> str:
    """
    Generate a shortened hex digest from a list of arguments.
    """
    return md5(b"\x00".join(str(arg).encode() for arg in args)).hexdigest()[:10]
