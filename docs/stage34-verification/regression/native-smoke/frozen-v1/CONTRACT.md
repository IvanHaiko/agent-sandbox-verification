src/candidate.py exports clamp(x, lo, hi) for integers.
If lo > hi raise ValueError. Otherwise return lo below the range, hi above it,
and x within it. Inclusive bounds, equal bounds and negative integers supported.
Standard library only, no I/O. src/helper.py is authorized implementation scope.
