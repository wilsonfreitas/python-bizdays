from typing import Any

import numpy as np
import numpy.typing as npt


class DateOutOfRange(ValueError):
    pass


def isstr(d: object) -> bool:
    return isinstance(d, str)


def match(x: npt.NDArray[np.int_], table: npt.NDArray[np.int_]) -> npt.NDArray[np.int_]:
    pos_dict: dict[np.int_, int] = dict(zip(table, range(len(table))))
    return np.array([pos_dict.get(val, -1) for val in x])


def isseq(seq: Any) -> bool:
    if isstr(seq):
        return False
    try:
        iter(seq)
    except TypeError:
        return False
    else:
        return True


def broadcast_pair(
    a: npt.NDArray[Any], b: npt.NDArray[Any], name_a: str, name_b: str
) -> tuple[npt.NDArray[Any], npt.NDArray[Any]]:
    """Pair two 1-D arrays by NumPy broadcasting; other lengths raise ``ValueError``."""
    if len(a) != len(b) and 1 not in (len(a), len(b)):
        raise ValueError(
            f"{name_a} has length {len(a)} and {name_b} has length {len(b)}; "
            "lengths must be equal, or one of them must be 1"
        )
    a_out, b_out = np.broadcast_arrays(a, b)
    return a_out, b_out
