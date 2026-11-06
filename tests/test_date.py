import unittest
from datetime import date, datetime

from bizdays.date import Date


class TestDate(unittest.TestCase):
    def test_init_from_str(self):
        d = Date("2023-01-02")
        self.assertEqual(d.date, date(2023, 1, 2))

    def test_init_from_date(self):
        d = Date(date(2022, 5, 6))
        self.assertEqual(d.date, date(2022, 5, 6))

    def test_init_from_datetime(self):
        d = Date(datetime(2021, 7, 8, 12, 0))
        self.assertEqual(d.date, date(2021, 7, 8))

    def test_init_from_Date(self):
        d1 = Date("2020-01-01")
        d2 = Date(d1)
        self.assertEqual(d2.date, date(2020, 1, 1))

    def test_init_from_none(self):
        d = Date(None)
        self.assertIsNone(d.date)

    def test_format(self):
        d = Date("2023-03-04")
        self.assertEqual(d.format(), "2023-03-04")
        self.assertEqual(d.format("%d/%m/%Y"), "04/03/2023")

    def test_format_none(self):
        d = Date(None)
        with self.assertRaises(ValueError):
            d.format()

    def test_comparisons(self):
        d1 = Date("2022-01-01")
        d2 = Date("2022-01-02")
        self.assertTrue(d2 > d1)
        self.assertTrue(d2 >= d1)
        self.assertTrue(d1 < d2)
        self.assertTrue(d1 <= d2)
        self.assertTrue(d1 == Date("2022-01-01"))
        with self.assertRaises(ValueError):
            _ = d1 == "2022-01-01"

    def test_comparisons_with_none(self):
        d1 = Date("2022-01-01")
        d2 = Date(None)
        with self.assertRaises(ValueError):
            _ = d1 > d2
        with self.assertRaises(ValueError):
            _ = d1 >= d2
        with self.assertRaises(ValueError):
            _ = d1 < d2
        with self.assertRaises(ValueError):
            _ = d1 <= d2

    def test_str_and_repr(self):
        d = Date("2022-12-31")
        self.assertEqual(str(d), "2022-12-31")
        self.assertEqual(repr(d), "2022-12-31")


if __name__ == "__main__":
    unittest.main()
