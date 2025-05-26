from typing import Any

import numpy as np
import numpy.typing as npt


class DateOutOfRange(Exception):
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


def recycle_arrays(a: npt.NDArray[Any], b: npt.NDArray[Any]) -> tuple[npt.NDArray[Any], npt.NDArray[Any]]:
    len_a = len(a)
    len_b = len(b)

    max_len = max(len_a, len_b)

    def recycle(arr: npt.NDArray[Any], target_len: int) -> npt.NDArray[Any]:
        return np.resize(arr, target_len)

    a_recycled = recycle(a, max_len)
    b_recycled = recycle(b, max_len)

    return a_recycled, b_recycled
