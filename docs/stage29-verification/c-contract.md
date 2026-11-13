Public contract: src/candidate.py exports def clamp(x, lo, hi) for integers.
If lo > hi, raise ValueError. Otherwise return lo if x < lo, hi if x > hi,
and x for lo <= x <= hi. Standard library only. No I/O. No other behavior required.
