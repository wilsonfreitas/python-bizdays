import numpy as np

from bizdays.utils import isseq, isstr, match, recycle_arrays


def test_match():
    x = np.array([1, 2, 3, 4, 5])
    table = np.array([2, 4, 6])
    expected = np.array([-1, 0, -1, 1, -1])
    result = match(x, table)
    assert np.array_equal(result, expected), f"Expected {expected}, but got {result}"


def test_match_not_found():
    x = np.array([1, 2, 3, 4, 5])
    table = np.array([6, 7, 8])
    expected = np.array([-1, -1, -1, -1, -1])
    result = match(x, table)
    assert np.array_equal(result, expected), f"Expected {expected}, but got {result}"


def test_match_empty():
    x = np.array([])
    table = np.array([1, 2, 3])
    expected = np.array([])
    result = match(x, table)
    assert np.array_equal(result, expected), f"Expected {expected}, but got {result}"


def test_match_table_empty():
    x = np.array([1, 2, 3])
    table = np.array([])
    expected = np.array([-1, -1, -1])
    result = match(x, table)
    assert np.array_equal(result, expected), f"Expected {expected}, but got {result}"


def test_match_both_empty():
    x = np.array([])
    table = np.array([])
    expected = np.array([])
    result = match(x, table)
    assert np.array_equal(result, expected), f"Expected {expected}, but got {result}"


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


def test_recycle_arrays():
    a = np.array([1, 2, 3])
    b = np.array([4, 5])
    expected_a = np.array([1, 2, 3])
    expected_b = np.array([4, 5, 4])
    result_a, result_b = recycle_arrays(a, b)
    assert np.array_equal(result_a, expected_a), f"Expected {expected_a}, but got {result_a}"
    assert np.array_equal(result_b, expected_b), f"Expected {expected_b}, but got {result_b}"
