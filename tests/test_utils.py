import numpy as np
import pytest

from bizdays.utils import broadcast_pair, isseq, isstr


def test_isstr():
    assert isstr("test") == True, "Expected True for string input"
    assert isstr(123) == False, "Expected False for integer input"
    assert isstr(12.34) == False, "Expected False for float input"
    assert isstr([1, 2, 3]) == False, "Expected False for list input"
    assert isstr((1, 2, 3)) == False, "Expected False for tuple input"
    assert isstr({1: "a", 2: "b"}) == False, "Expected False for dict input"
    assert isstr(None) == False, "Expected False for None input"


def test_isseq():
    assert isseq([1, 2, 3]) == True, "Expected True for list input"
    assert isseq((1, 2, 3)) == True, "Expected True for tuple input"
    assert isseq("test") == False, "Expected False for string input"


@pytest.mark.parametrize("la, lb", [(3, 2), (2, 4), (0, 2), (2, 0)])
def test_broadcast_pair_rejects_other_lengths(la, lb):
    with pytest.raises(ValueError, match=f"a has length {la} and b has length {lb}"):
        broadcast_pair(np.arange(la), np.arange(lb), "a", "b")


def test_broadcast_pair_length_one():
    a, b = broadcast_pair(np.array([1, 2, 3]), np.array([4]), "a", "b")
    assert a.tolist() == [1, 2, 3]
    assert b.tolist() == [4, 4, 4]
    a, b = broadcast_pair(np.array([4]), np.array([1, 2, 3]), "a", "b")
    assert a.tolist() == [4, 4, 4]
    assert b.tolist() == [1, 2, 3]


def test_broadcast_pair_equal_lengths():
    a, b = broadcast_pair(np.array([1, 2]), np.array([3, 4]), "a", "b")
    assert a.tolist() == [1, 2]
    assert b.tolist() == [3, 4]


@pytest.mark.parametrize(
    "b_in, b_dtype",
    [(np.array([5]), np.dtype(np.int64)), (np.array([], dtype=np.float64), np.dtype(np.float64))],
)
def test_broadcast_pair_empty(b_in, b_dtype):
    a, b = broadcast_pair(np.array([], dtype="datetime64[D]"), b_in, "a", "b")
    assert a.shape == (0,) and b.shape == (0,)
    assert a.dtype == np.dtype("datetime64[D]")
    assert b.dtype == b_dtype
