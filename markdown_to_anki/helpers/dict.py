from typing import Any


def safe_get(d: dict, k: str, default_val: Any = None) -> Any:
    if not d:
        return default_val

    if d.get(k):
        return d[k]

    keys = k.split(sep=".", maxsplit=1)
    if len(keys) == 2:
        return safe_get(d.get(keys[0]), keys[1], default_val)

    return default_val
