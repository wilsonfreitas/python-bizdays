from typing import Any

import numpy as np
import numpy.typing as npt


class DateOutOfRange(ValueError):
    """A date, input or result, lies outside the calendar range.

    ``positions`` is a sorted 1-D ``int64`` array with the index of every bad
    element, counted in the result of the call.
    """

    def __init__(self, message: str, positions: npt.ArrayLike = (0,)) -> None:
        super().__init__(message)
        self.positions: npt.NDArray[np.int64] = np.unique(np.asarray(positions, dtype=np.int64))

    def __reduce__(self) -> tuple[Any, ...]:
        return (type(self), (str(self), self.positions))


def isstr(d: object) -> bool:
    return isinstance(d, str)


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
