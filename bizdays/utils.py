import numpy as np
import numpy.typing as npt


class DateOutOfRange(Exception):
    pass


def isstr(d: object) -> bool:
    return isinstance(d, str)


def match(x: npt.NDArray[np.int_], table: npt.NDArray[np.int_]) -> npt.NDArray[np.int_]:
    pos_dict: dict[np.int_, int] = {val: i for i, val in enumerate(table)}
    return np.array([pos_dict.get(val, -1) if val in pos_dict else -1 for val in x])
