from hashlib import md5
from typing import Any


def generate_unique_id(*args: Any) -> str:
    """
    Generate a shortened hex digest from a list of arguments.

    Any non-string arguments are cast to a string.
    """
    hash = md5()
    for arg in args:
        if not isinstance(arg, str):
            arg = str(arg)
        hash.update(arg.encode())
        hash.update(b"\x00")
    return hash.hexdigest()[:10]
