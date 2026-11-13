#!/usr/bin/env python3
"""Contract tests; run from the repository root with python3 tests/test_contract.py."""

import sys
import unittest

sys.path.insert(0,"src")
import candidate


class ClampContractTests(unittest.TestCase):
    def test_below_lower_bound(self):
        for x in (-100, 0, 2):
            with self.subTest(x=x):
                self.assertEqual(candidate.clamp(x, 3, 9), 3)

    def test_above_upper_bound(self):
        for x in (10, 11, 100):
            with self.subTest(x=x):
                self.assertEqual(candidate.clamp(x, 3, 9), 9)

    def test_inclusive_boundaries(self):
        for x in (3, 9):
            with self.subTest(x=x):
                self.assertEqual(candidate.clamp(x, 3, 9), x)

    def test_representative_interiors(self):
        for x in (4, 6, 8):
            with self.subTest(x=x):
                self.assertEqual(candidate.clamp(x, 3, 9), x)

    def test_negative_range(self):
        for x, expected in ((-20, -10), (-10, -10), (-7, -7), (-3, -3), (-1, -3)):
            with self.subTest(x=x):
                self.assertEqual(candidate.clamp(x, -10, -3), expected)

    def test_range_crossing_zero(self):
        for x, expected in ((-9, -5), (-5, -5), (-2, -2), (0, 0), (2, 2), (5, 5), (9, 5)):
            with self.subTest(x=x):
                self.assertEqual(candidate.clamp(x, -5, 5), expected)

    def test_equal_bounds(self):
        for bound in (-4, 0, 7):
            for x in (bound - 1, bound, bound + 1):
                with self.subTest(bound=bound, x=x):
                    self.assertEqual(candidate.clamp(x, bound, bound), bound)

    def test_invalid_bounds_raise_value_error_for_every_x_position(self):
        for lo, hi in ((9, 3), (-3, -10), (1, -1)):
            for x in (hi - 1, hi, (lo + hi) // 2, lo, lo + 1):
                with self.subTest(lo=lo, hi=hi, x=x):
                    with self.assertRaises(ValueError):
                        candidate.clamp(x, lo, hi)

    def test_arbitrary_precision_integers(self):
        limit = 10 ** 100
        for x, expected in ((-limit - 1, -limit), (-limit, -limit), (1, 1), (limit, limit), (limit + 1, limit)):
            with self.subTest(x=x):
                self.assertEqual(candidate.clamp(x, -limit, limit), expected)


if __name__ == "__main__":
    unittest.main()
