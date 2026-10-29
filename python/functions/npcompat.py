"""Pure-Python stand-ins for the few numpy / scipy calls used by the physics.

The web version runs Python in the browser (Pyodide) without numpy and scipy,
which keeps the page download small. Only scalar maths is needed here, so these
helpers reproduce numpy's behaviour for scalars:

* log() returns nan/-inf instead of raising for values <= 0, like numpy.
* round() rounds half to even, like numpy (and Python's round).
* interpolate.interp1d(x, y)(x_new) is linear interpolation with the same
  formula as scipy and the same error for points outside the data range.
"""
import math

pi = math.pi


def zeros(n):
    if isinstance(n, tuple):
        return Grid(*n)
    return [0.0] * int(n)


def log(x):
    if x > 0:
        return math.log(x)
    if x == 0:
        return float('-inf')
    return float('nan')


def radians(x):
    if isinstance(x, (list, tuple)):
        return [math.radians(v) for v in x]
    return math.radians(x)


def degrees(x):
    return math.degrees(x)


def sin(x):
    return math.sin(x)


def cos(x):
    return math.cos(x)


def tan(x):
    return math.tan(x)


def round(x, decimals=0):  # noqa: A001 - mirrors numpy.round
    import builtins
    return builtins.round(x, decimals)


class _Linear:
    def __init__(self, x, y):
        pairs = sorted(zip((float(v) for v in x), (float(v) for v in y)))
        self.x = [p[0] for p in pairs]
        self.y = [p[1] for p in pairs]

    def __call__(self, x_new):
        x, y = self.x, self.y
        if x_new < x[0] or x_new > x[-1]:
            raise ValueError("A value in x_new is outside the interpolation range.")
        # same search and formula as scipy.interpolate.interp1d(kind='linear')
        i = 1
        while i < len(x) - 1 and x[i] < x_new:
            i += 1
        x_lo, x_hi, y_lo, y_hi = x[i - 1], x[i], y[i - 1], y[i]
        slope = (y_hi - y_lo) / (x_hi - x_lo)
        return slope * (x_new - x_lo) + y_lo


class interpolate:  # noqa: N801 - used as `interpolate.interp1d`, like scipy
    interp1d = _Linear


# ---- extra stand-ins used by vpp.py ---------------------------------------

def arctan2(y, x):
    return math.atan2(y, x)


def sign(x):
    if x > 0:
        return 1.0
    if x < 0:
        return -1.0
    return 0.0 if x == 0 else float('nan')


def interp(x, xp, fp):
    """numpy.interp: piecewise linear, clamped at both ends."""
    if x <= xp[0]:
        return float(fp[0])
    if x >= xp[-1]:
        return float(fp[-1])
    i = 1
    while xp[i] < x:
        i += 1
    x0, x1, y0, y1 = xp[i - 1], xp[i], fp[i - 1], fp[i]
    if x1 == x0:
        return float(y1)
    return y0 + (x - x0) * (y1 - y0) / (x1 - x0)


def arange(start, stop, step):
    # same values as numpy.arange (which steps by (start + step) - start)
    n = max(0, math.ceil((stop - start) / step))
    if n == 0:
        return []
    delta = (start + step) - start
    return [start + i * delta for i in range(n)]


def size(a):
    return len(a)


def mean(a):
    values = a.values() if isinstance(a, Grid) else list(a)
    return sum(values) / len(values)


class Vec(list):
    """1-D array: element-wise + and -, reshape(-1, 1) gives a column matrix."""

    def __add__(self, other):
        return Vec(a + b for a, b in zip(self, other))

    def __sub__(self, other):
        return Vec(a - b for a, b in zip(self, other))

    def reshape(self, rows, cols):
        return Matrix([[v] for v in self])


def array(values):
    return Vec(float(v) for v in values)


def cross(a, b):
    return Vec([a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]])


class Matrix:
    """The bit of numpy.matrix the VPP uses: products of 3x3 rotation matrices
    and 3x1 vectors, sums, and reading an element of a column vector."""

    def __init__(self, rows):
        self.rows = [[float(v) for v in r] for r in rows]

    def __mul__(self, other):
        cols = list(zip(*other.rows))
        return Matrix([[sum(a * b for a, b in zip(row, col)) for col in cols] for row in self.rows])

    def __add__(self, other):
        return Matrix([[a + b for a, b in zip(r1, r2)] for r1, r2 in zip(self.rows, other.rows)])

    def __sub__(self, other):
        return Matrix([[a - b for a, b in zip(r1, r2)] for r1, r2 in zip(self.rows, other.rows)])

    def __neg__(self):
        return Matrix([[-a for a in r] for r in self.rows])

    def __getitem__(self, i):
        row = self.rows[i]
        return row[0] if len(row) == 1 else row


def matrix(rows):
    return Matrix(rows)


class Grid:
    """2-D array indexed as g[i, j] (np.zeros((rows, cols)))."""

    def __init__(self, rows, cols):
        self.data = [[0.0] * cols for _ in range(rows)]

    def __getitem__(self, ij):
        i, j = ij
        return self.data[i][j]

    def __setitem__(self, ij, value):
        i, j = ij
        self.data[i][j] = float(value)

    def values(self):
        return [v for row in self.data for v in row]

    def tolist(self):
        return [row[:] for row in self.data]
