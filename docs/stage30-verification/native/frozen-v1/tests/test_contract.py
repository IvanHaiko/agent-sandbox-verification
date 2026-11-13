"""Contract tests for candidate.clamp; run from the repository root."""

import sys
import unittest

sys.path.insert(0,"src")
import candidate


class ClampContractTests(unittest.TestCase):
    def test_below_range_returns_lower_bound(self):
        for x in (-100, 0, 2):
            with self.subTest(x=x):
                self.assertEqual(candidate.clamp(x, 3, 9), 3)

    def test_above_range_returns_upper_bound(self):
        for x in (10, 20, 100):
            with self.subTest(x=x):
                self.assertEqual(candidate.clamp(x, 3, 9), 9)

    def test_lower_boundary_is_inclusive(self):
        self.assertEqual(candidate.clamp(3, 3, 9), 3)

    def test_upper_boundary_is_inclusive(self):
        self.assertEqual(candidate.clamp(9, 3, 9), 9)

    def test_representative_interiors_are_unchanged(self):
        for x in (4, 6, 8):
            with self.subTest(x=x):
                self.assertEqual(candidate.clamp(x, 3, 9), x)

    def test_equal_bounds(self):
        for bound in (-7, 0, 7):
            for x in (bound - 1, bound, bound + 1):
                with self.subTest(bound=bound, x=x):
                    self.assertEqual(candidate.clamp(x, bound, bound), bound)

    def test_negative_range(self):
        for x, expected in ((-20, -10), (-10, -10), (-7, -7),
                            (-3, -3), (-2, -3), (0, -3)):
            with self.subTest(x=x):
                self.assertEqual(candidate.clamp(x, -10, -3), expected)

    def test_range_crossing_zero(self):
        for x, expected in ((-9, -5), (-5, -5), (-2, -2), (0, 0),
                            (2, 2), (5, 5), (9, 5)):
            with self.subTest(x=x):
                self.assertEqual(candidate.clamp(x, -5, 5), expected)

    def test_reversed_bounds_raise_value_error(self):
        for lo, hi in ((9, 3), (-3, -10), (1, -1)):
            for x in (hi - 1, hi, (lo + hi) // 2, lo, lo + 1):
                with self.subTest(x=x, lo=lo, hi=hi):
                    with self.assertRaises(ValueError):
                        candidate.clamp(x, lo, hi)


if __name__ == "__main__":
    unittest.main()
