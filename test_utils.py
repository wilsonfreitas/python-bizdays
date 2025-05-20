import numpy as np

from utils import isstr, match


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
