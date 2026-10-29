"""Pure-Python port of MINPACK's hybrd (Powell's hybrid method).

This is the solver behind scipy.optimize.root(fun, x0) (method 'hybr'), which
the VPP uses. Porting it keeps the browser version free of scipy while giving
the same iterations: same finite-difference Jacobian, QR factorisation,
dogleg step, Broyden rank-one updates and stopping rules, with scipy's default
options (xtol=1.49012e-08, maxfev=200*(n+1), factor=100, automatic scaling).

Reference: J. J. More, B. S. Garbow, K. E. Hillstrom, MINPACK-1 (1980).
"""
import math

EPSMCH = 2.220446049250313e-16
GIANT = 1.7976931348623157e308
RDWARF = 3.834e-20
RGIANT = 1.304e19


class RootResult:
    def __init__(self, x, fun, success, status, nfev):
        self.x = x
        self.fun = fun
        self.success = success
        self.status = status
        self.nfev = nfev


def enorm(x):
    n = len(x)
    s1 = s2 = s3 = 0.0
    x1max = x3max = 0.0
    agiant = RGIANT / n
    for xi in x:
        xabs = abs(xi)
        if RDWARF < xabs < agiant:
            s2 += xabs * xabs
        elif xabs <= RDWARF:
            if xabs > x3max:
                s3 = 1.0 + s3 * (x3max / xabs) ** 2
                x3max = xabs
            elif xabs != 0.0:
                s3 += (xabs / x3max) ** 2
        else:
            if xabs > x1max:
                s1 = 1.0 + s1 * (x1max / xabs) ** 2
                x1max = xabs
            else:
                s1 += (xabs / x1max) ** 2
    if s1 != 0.0:
        return x1max * math.sqrt(s1 + (s2 / x1max) / x1max)
    if s2 != 0.0:
        if s2 >= x3max:
            return math.sqrt(s2 * (1.0 + (x3max / s2) * (x3max * s3)))
        return math.sqrt(x3max * ((s2 / x3max) + (x3max * s3)))
    return x3max * math.sqrt(s3)


def _fdjac1(fcn, n, x, fvec, epsfcn):
    """Forward-difference Jacobian; fjac[i][j] = d f_i / d x_j."""
    eps = math.sqrt(max(epsfcn, EPSMCH))
    fjac = [[0.0] * n for _ in range(n)]
    for j in range(n):
        temp = x[j]
        h = eps * abs(temp)
        if h == 0.0:
            h = eps
        x[j] = temp + h
        wa1 = fcn(x)
        x[j] = temp
        for i in range(n):
            fjac[i][j] = (wa1[i] - fvec[i]) / h
    return fjac


def _qrfac(n, a):
    """Householder QR without pivoting (in place). Returns rdiag, acnorm."""
    acnorm = [enorm([a[i][j] for i in range(n)]) for j in range(n)]
    rdiag = acnorm[:]
    for j in range(n):
        ajnorm = enorm([a[i][j] for i in range(j, n)])
        if ajnorm != 0.0:
            if a[j][j] < 0.0:
                ajnorm = -ajnorm
            for i in range(j, n):
                a[i][j] = a[i][j] / ajnorm
            a[j][j] = a[j][j] + 1.0
            for k in range(j + 1, n):
                s = 0.0
                for i in range(j, n):
                    s = s + a[i][j] * a[i][k]
                temp = s / a[j][j]
                for i in range(j, n):
                    a[i][k] = a[i][k] - temp * a[i][j]
        rdiag[j] = -ajnorm
    return rdiag, acnorm


def _qform(n, q):
    """Accumulate the orthogonal matrix Q from its factored form (in place)."""
    for j in range(1, n):
        for i in range(j):
            q[i][j] = 0.0
    wa = [0.0] * n
    for l in range(n):
        k = n - l - 1
        for i in range(k, n):
            wa[i] = q[i][k]
            q[i][k] = 0.0
        q[k][k] = 1.0
        if wa[k] != 0.0:
            for j in range(k, n):
                s = 0.0
                for i in range(k, n):
                    s = s + q[i][j] * wa[i]
                temp = s / wa[k]
                for i in range(k, n):
                    q[i][j] = q[i][j] - temp * wa[i]


def _dogleg(n, r, diag, qtb, delta):
    # r is the upper triangle packed by rows (0-based)
    x = [0.0] * n
    jj = (n * (n + 1)) // 2 + 1  # 1-based pointer as in MINPACK
    for k in range(1, n + 1):
        j = n - k + 1
        jj = jj - k
        l = jj + 1
        s = 0.0
        for i in range(j + 1, n + 1):
            s = s + r[l - 1] * x[i - 1]
            l += 1
        temp = r[jj - 1]
        if temp == 0.0:
            l = j
            for i in range(1, j + 1):
                temp = max(temp, abs(r[l - 1]))
                l = l + n - i
            temp = EPSMCH * temp
            if temp == 0.0:
                temp = EPSMCH
        x[j - 1] = (qtb[j - 1] - s) / temp

    wa1 = [0.0] * n
    wa2 = [diag[j] * x[j] for j in range(n)]
    qnorm = enorm(wa2)
    if qnorm <= delta:
        return x

    l = 0
    for j in range(n):
        temp = qtb[j]
        for i in range(j, n):
            wa1[i] = wa1[i] + r[l] * temp
            l += 1
        wa1[j] = wa1[j] / diag[j]

    gnorm = enorm(wa1)
    sgnorm = 0.0
    alpha = delta / qnorm
    if gnorm != 0.0:
        for j in range(n):
            wa1[j] = (wa1[j] / gnorm) / diag[j]
        l = 0
        for j in range(n):
            s = 0.0
            for i in range(j, n):
                s = s + r[l] * wa1[i]
                l += 1
            wa2[j] = s
        temp = enorm(wa2)
        sgnorm = (gnorm / temp) / temp
        alpha = 0.0
        if sgnorm < delta:
            bnorm = enorm(qtb)
            temp = (bnorm / gnorm) * (bnorm / qnorm) * (sgnorm / delta)
            temp = temp - (delta / qnorm) * (sgnorm / delta) ** 2 + math.sqrt(
                (temp - (delta / qnorm)) ** 2 + (1.0 - (delta / qnorm) ** 2) * (1.0 - (sgnorm / delta) ** 2))
            alpha = ((delta / qnorm) * (1.0 - (sgnorm / delta) ** 2)) / temp
    temp = (1.0 - alpha) * min(sgnorm, delta)
    return [temp * wa1[j] + alpha * x[j] for j in range(n)]


def _r1updt(m, n, s, u, v, w):
    """Update the packed upper-triangular s after a rank-one change (in place)."""
    jj = (n * (2 * m - n + 1)) // 2 - (m - n)  # 1-based
    l = jj
    for i in range(n, m + 1):
        w[i - 1] = s[l - 1]
        l += 1
    nm1 = n - 1
    for nmj in range(1, nm1 + 1):
        j = n - nmj
        jj = jj - (m - j + 1)
        w[j - 1] = 0.0
        if v[j - 1] != 0.0:
            if abs(v[n - 1]) < abs(v[j - 1]):
                cotan = v[n - 1] / v[j - 1]
                sin = 0.5 / math.sqrt(0.25 + 0.25 * cotan ** 2)
                cos = sin * cotan
                tau = 1.0
                if abs(cos) * GIANT > 1.0:
                    tau = 1.0 / cos
            else:
                tan = v[j - 1] / v[n - 1]
                cos = 0.5 / math.sqrt(0.25 + 0.25 * tan ** 2)
                sin = cos * tan
                tau = sin
            v[n - 1] = sin * v[j - 1] + cos * v[n - 1]
            v[j - 1] = tau
            l = jj
            for i in range(j, m + 1):
                temp = cos * s[l - 1] - sin * w[i - 1]
                w[i - 1] = sin * s[l - 1] + cos * w[i - 1]
                s[l - 1] = temp
                l += 1
    for i in range(1, m + 1):
        w[i - 1] = w[i - 1] + v[n - 1] * u[i - 1]
    sing = False
    for j in range(1, nm1 + 1):
        if w[j - 1] != 0.0:
            if abs(s[jj - 1]) < abs(w[j - 1]):
                cotan = s[jj - 1] / w[j - 1]
                sin = 0.5 / math.sqrt(0.25 + 0.25 * cotan ** 2)
                cos = sin * cotan
                tau = 1.0
                if abs(cos) * GIANT > 1.0:
                    tau = 1.0 / cos
            else:
                tan = w[j - 1] / s[jj - 1]
                cos = 0.5 / math.sqrt(0.25 + 0.25 * tan ** 2)
                sin = cos * tan
                tau = sin
            l = jj
            for i in range(j, m + 1):
                temp = cos * s[l - 1] + sin * w[i - 1]
                w[i - 1] = -sin * s[l - 1] + cos * w[i - 1]
                s[l - 1] = temp
                l += 1
            w[j - 1] = tau
        if s[jj - 1] == 0.0:
            sing = True
        jj = jj + (m - j + 1)
    l = jj
    for i in range(n, m + 1):
        s[l - 1] = w[i - 1]
        l += 1
    if s[jj - 1] == 0.0:
        sing = True
    return sing


def _r1mpyq(m, n, a, v, w):
    """Apply the Givens rotations stored in v and w to the m x n matrix a."""
    nm1 = n - 1
    for nmj in range(1, nm1 + 1):
        j = n - nmj
        if abs(v[j - 1]) > 1.0:
            cos = 1.0 / v[j - 1]
            sin = math.sqrt(1.0 - cos ** 2)
        else:
            sin = v[j - 1]
            cos = math.sqrt(1.0 - sin ** 2)
        for i in range(m):
            temp = cos * a[i][j - 1] - sin * a[i][n - 1]
            a[i][n - 1] = sin * a[i][j - 1] + cos * a[i][n - 1]
            a[i][j - 1] = temp
    for j in range(1, nm1 + 1):
        if abs(w[j - 1]) > 1.0:
            cos = 1.0 / w[j - 1]
            sin = math.sqrt(1.0 - cos ** 2)
        else:
            sin = w[j - 1]
            cos = math.sqrt(1.0 - sin ** 2)
        for i in range(m):
            temp = cos * a[i][j - 1] + sin * a[i][n - 1]
            a[i][n - 1] = -sin * a[i][j - 1] + cos * a[i][n - 1]
            a[i][j - 1] = temp


def root(fun, x0, xtol=1.49012e-08, maxfev=0, epsfcn=None, factor=100.0):
    """Solve fun(x) = 0 like scipy.optimize.root(fun, x0) (method 'hybr')."""
    p1, p5, p001, p0001 = 0.1, 0.5, 0.001, 0.0001
    x = [float(v) for v in x0]
    n = len(x)
    if maxfev <= 0:
        maxfev = 200 * (n + 1)
    if epsfcn is None:
        epsfcn = EPSMCH

    def fcn(xx):
        return [float(v) for v in fun(list(xx))]

    fvec = fcn(x)
    nfev = 1
    fnorm = enorm(fvec)
    msum = n
    it = 1
    ncsuc = ncfail = nslow1 = nslow2 = 0
    info = 0
    diag = [0.0] * n
    delta = xnorm = 0.0

    while info == 0:
        jeval = True
        fjac = _fdjac1(fcn, n, x, fvec, epsfcn)
        nfev += msum
        wa1, wa2 = _qrfac(n, fjac)
        if it == 1:
            for j in range(n):
                diag[j] = wa2[j] if wa2[j] != 0.0 else 1.0
            xnorm = enorm([diag[j] * x[j] for j in range(n)])
            delta = factor * xnorm
            if delta == 0.0:
                delta = factor
        # Q^T fvec
        qtf = fvec[:]
        for j in range(n):
            if fjac[j][j] != 0.0:
                s = 0.0
                for i in range(j, n):
                    s = s + fjac[i][j] * qtf[i]
                temp = -s / fjac[j][j]
                for i in range(j, n):
                    qtf[i] = qtf[i] + fjac[i][j] * temp
        # copy the triangular factor (packed by rows)
        r = [0.0] * (n * (n + 1) // 2)
        sing = False
        for j in range(1, n + 1):
            l = j
            for i in range(1, j):
                r[l - 1] = fjac[i - 1][j - 1]
                l = l + n - i
            r[l - 1] = wa1[j - 1]
            if wa1[j - 1] == 0.0:
                sing = True
        _qform(n, fjac)
        for j in range(n):
            diag[j] = max(diag[j], wa2[j])

        while True:
            step = _dogleg(n, r, diag, qtf, delta)
            wa1 = [-v for v in step]
            wa2 = [x[j] + wa1[j] for j in range(n)]
            wa3 = [diag[j] * wa1[j] for j in range(n)]
            pnorm = enorm(wa3)
            if it == 1:
                delta = min(delta, pnorm)
            wa4 = fcn(wa2)
            nfev += 1
            fnorm1 = enorm(wa4)
            actred = -1.0
            if fnorm1 < fnorm:
                actred = 1.0 - (fnorm1 / fnorm) ** 2
            l = 0
            for i in range(n):
                s = 0.0
                for j in range(i, n):
                    s = s + r[l] * wa1[j]
                    l += 1
                wa3[i] = qtf[i] + s
            temp = enorm(wa3)
            prered = 0.0
            if temp < fnorm:
                prered = 1.0 - (temp / fnorm) ** 2
            ratio = 0.0
            if prered > 0.0:
                ratio = actred / prered
            if ratio < p1:
                ncsuc = 0
                ncfail += 1
                delta = p5 * delta
            else:
                ncfail = 0
                ncsuc += 1
                if ratio >= p5 or ncsuc > 1:
                    delta = max(delta, pnorm / p5)
                if abs(ratio - 1.0) <= p1:
                    delta = pnorm / p5
            if ratio >= p0001:
                x = wa2
                wa2 = [diag[j] * x[j] for j in range(n)]
                fvec = wa4
                xnorm = enorm(wa2)
                fnorm = fnorm1
                it += 1
            nslow1 += 1
            if actred >= p001:
                nslow1 = 0
            if jeval:
                nslow2 += 1
            if actred >= p1:
                nslow2 = 0
            if delta <= xtol * xnorm or fnorm == 0.0:
                info = 1
            if info != 0:
                break
            if nfev >= maxfev:
                info = 2
            if p1 * max(p1 * delta, pnorm) <= EPSMCH * xnorm:
                info = 3
            if nslow2 == 5:
                info = 4
            if nslow1 == 10:
                info = 5
            if info != 0:
                break
            if ncfail == 2:
                break  # recompute the Jacobian
            # rank-one update of the Jacobian and of qtf
            for j in range(n):
                s = 0.0
                for i in range(n):
                    s = s + fjac[i][j] * wa4[i]
                wa2[j] = (s - wa3[j]) / pnorm
                wa1[j] = diag[j] * ((diag[j] * wa1[j]) / pnorm)
                if ratio >= p0001:
                    qtf[j] = s
            sing = _r1updt(n, n, r, wa1, wa2, wa3)
            _r1mpyq(n, n, fjac, wa2, wa3)
            qtf_m = [qtf[:]]
            _r1mpyq(1, n, qtf_m, wa2, wa3)
            qtf = qtf_m[0]
            jeval = False

    return RootResult(x, fvec, info == 1, info, nfev)
