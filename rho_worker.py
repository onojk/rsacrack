
import random, math
from math import gcd

# ---- gmpy2 acceleration (optional) -----------------------------------------
try:
    import gmpy2
    mpz = gmpy2.mpz
    HAVE_GMPY2 = True
    def is_square(x): return bool(gmpy2.is_square(x))
    def isqrt(x): return int(gmpy2.isqrt(x))
    def powmod(a,b,n): return int(gmpy2.powmod(a,b,n))
except Exception:
    mpz = int
    HAVE_GMPY2 = False
    def is_square(x):
        x = int(x)
        r = int(math.isqrt(x))
        return r*r == x
    def isqrt(x): return int(math.isqrt(int(x)))
    def powmod(a,b,n): return pow(int(a), int(b), int(n))

RAND = random.SystemRandom()

# ---- helpers ----------------------------------------------------------------
def _to_int(x):
    if isinstance(x, (bytes, bytearray)):
        x = x.decode()
    if isinstance(x, str):
        x = x.strip()
    return mpz(x)

def _small_trial(n, limit=10**6):
    n = mpz(n)
    if n % 2 == 0: return 2
    if n % 3 == 0: return 3
    i, step = 5, 2
    while i <= limit and i*i <= n:
        if n % i == 0:
            return int(i)
        i += step
        step = 6 - step
    return None

def _primes_upto(B):
    B = int(B)
    if B < 2: return []
    sieve = bytearray(b"\x01")*(B+1)
    sieve[:2] = b"\x00\x00"
    r = int(B**0.5)
    for p in range(2, r+1):
        if sieve[p]:
            step = p
            start = p*p
            sieve[start:B+1:step] = b"\x00"*(((B-start)//step)+1)
    return [i for i in range(2, B+1) if sieve[i]]

# ---- Pollard p-1 (stage 1) --------------------------------------------------
def _pminus1_stage1(n, B1=100_000, base=2):
    n = mpz(n)
    if n % 2 == 0: return 2
    a = mpz(base) % n
    for p in _primes_upto(B1):
        e = 1
        while p**(e+1) <= B1: e += 1
        a = powmod(a, p**e, n)
    g = gcd(int((a-1) % n), int(n))
    if 1 < g < n:
        return int(g)
    return None

# ---- Hart/Fermat near-square sweep ------------------------------------------
def _hart_olf(n, k_limit=20000):
    n = mpz(n)
    for k in range(1, int(k_limit)+1):
        kn = k*n
        a = isqrt(kn)
        if a*a < kn:
            a += 1
        b2 = a*a - kn
        if b2 >= 0 and is_square(b2):
            b = isqrt(b2)
            g = gcd(int(a-b), int(n))
            if 1 < g < n:
                return int(g)
    return None

# ---- SQUFOF (simple, good for ~30–40-bit factors) ---------------------------
def _squfof(n, iters=250000):
    n = mpz(n)
    if n % 2 == 0: return 2
    s = isqrt(n)
    if s*s == n: return int(s)
    P = s
    Q = n - P*P
    if Q == 0: return int(s)
    Pp, Qp = mpz(0), mpz(1)
    for i in range(1, int(iters)+1):
        b = (s + P) // Q
        Pn = b*Q - P
        Qn = (n - Pn*Pn) // Q
        P, Q, Pp = Pn, Qn, Q
        if (i & 1) == 0 and is_square(Q):
            r = isqrt(Q)
            # reverse cycle
            P2, Q2 = P, r
            P3 = P2
            Q3 = Q2
            while True:
                b = (s + P3) // Q3
                P4 = b*Q3 - P3
                Q4 = (n - P4*P4) // Q3
                if P4 == P2:
                    g = gcd(int(Q4), int(n))
                    if 1 < g < n:
                        return int(g)
                    break
                P3, Q3 = P4, Q4
    return None

# ---- Tiny ECM Stage-1 (Jacobian, few curves) --------------------------------
def _ecm_stage1_once(n, B1=50_000):
    n = mpz(n)
    # random curve y^2 = x^3 + a x + b  over Z/nZ with random point
    while True:
        x = mpz(RAND.randrange(2, int(n-2)))
        y = mpz(RAND.randrange(2, int(n-2)))
        a = mpz(RAND.randrange(1, 1<<32))
        b = (y*y - (x*x*x + a*x)) % n
        disc = (4*(a*a*a) + 27*(b*b)) % n
        g = gcd(int(disc), int(n))
        if g == 1:
            break
        if 1 < g < n:
            return int(g)
    X, Y, Z = x % n, y % n, mpz(1)

    def j_double(X1, Y1, Z1):
        if Y1 % n == 0: return (mpz(0), mpz(1), mpz(0))
        S  = (4 * X1 * (Y1*Y1 % n)) % n
        M  = (3*X1*X1 + a*Z1*Z1) % n
        X3 = (M*M - 2*S) % n
        Y3 = (M*(S - X3) - 8*(Y1*Y1 % n)*(Y1*Y1 % n)) % n
        Z3 = (2*Y1*Z1) % n
        return (X3, Y3, Z3)

    def j_add(X1,Y1,Z1, X2,Y2,Z2):
        if Z1 == 0: return (X2,Y2,Z2)
        if Z2 == 0: return (X1,Y1,Z1)
        Z1Z1 = (Z1*Z1) % n
        Z2Z2 = (Z2*Z2) % n
        U1 = (X1 * Z2Z2) % n
        U2 = (X2 * Z1Z1) % n
        S1 = (Y1 * Z2 * Z2Z2) % n
        S2 = (Y2 * Z1 * Z1Z1) % n
        if U1 == U2:
            if (S1 - S2) % n == 0:
                return j_double(X1,Y1,Z1)
            else:
                return (mpz(0), mpz(1), mpz(0))
        H  = (U2 - U1) % n
        R  = (S2 - S1) % n
        H2 = (H*H) % n
        H3 = (H2*H) % n
        U1H2 = (U1*H2) % n
        X3 = (R*R - H3 - 2*U1H2) % n
        Y3 = (R*(U1H2 - X3) - S1*H3) % n
        Z3 = (Z1 * Z2 * H) % n
        return (X3, Y3, Z3)

    def j_mul(k, P):
        Xk, Yk, Zk = mpz(0), mpz(1), mpz(0)
        X1, Y1, Z1 = P
        for bit in bin(int(k))[2:]:
            Xk, Yk, Zk = j_double(Xk, Yk, Zk)
            if bit == "1":
                Xk, Yk, Zk = j_add(Xk, Yk, Zk, X1, Y1, Z1)
            g = gcd(int(Zk), int(n))
            if 1 < g < n:
                return int(g), (Xk,Yk,Zk)
        return 1, (Xk,Yk,Zk)

    Q = (X, Y, Z)
    for p in _primes_upto(B1):
        e = 1
        while p**(e+1) <= B1: e += 1
        k = p**e
        g, Q = j_mul(k, Q)
        if 1 < g < n:
            return int(g)
    g = gcd(int(Q[2]), int(n))
    if 1 < g < n:
        return int(g)
    return None

def _mini_ecm(n, curves=6, B1=50_000):
    n = mpz(n)
    for _ in range(int(curves)):
        g = _ecm_stage1_once(n, B1=B1)
        if g: return g
    return None

# ---- Pollard Rho (Brent + block-GCD) ----------------------------------------
def _rho_brent_block(n, budget=500_000, seed=None, c=None, m=256):
    n = mpz(n)
    if n % 2 == 0: return 2, 0
    if c is None:
        c = mpz(RAND.randrange(1, int(n-1))) | 1
    if seed is None:
        seed = mpz(RAND.randrange(2, int(n-1)))
    y = mpz(seed)
    r = mpz(1)
    q = mpz(1)
    iters = 0
    while iters < budget:
        x = y
        for _ in range(int(r)):
            y = (y*y + c) % n
        k = 0
        while k < r and iters < budget:
            ys = y
            for _ in range(min(m, int(r-k))):
                y = (y*y + c) % n
                q = (q * abs(int(y - x))) % n
                iters += 1
            g = gcd(int(q), int(n))
            if 1 < g < n:
                return int(g), iters
            k += m
        r *= 2
        g = gcd(abs(int(y - x)), int(n))
        if 1 < g < n:
            return int(g), iters
    return None, iters

# ---- Orchestrator ------------------------------------------------------------
def pollard_rho_job(N, budget=500_000):
    n = _to_int(N)
    n = mpz(n)
    if n <= 1:
        return {"algo":"trivial","iters":0,"factor":int(n),"cofactor":1}
    if n % 2 == 0:
        return {"algo":"trial","iters":0,"factor":2,"cofactor":int(n//2)}

    # 0) small trial
    f = _small_trial(n, limit=min(1_000_000, max(50_000, int(budget//50))))
    if f:
        return {"algo":"trial","iters":0,"factor":int(f),"cofactor":int(n//f)}

    # 1) p-1 micro-stage
    B1 = min(100_000, max(20_000, int(budget//25)))
    f = _pminus1_stage1(n, B1=B1, base=2)
    if f:
        return {"algo":"p-1","iters":B1,"factor":int(f),"cofactor":int(n//f)}

    # 2) near-square sweep (Hart/Fermat)
    f = _hart_olf(n, k_limit=min(20000, max(2000, int(budget//50))))
    if f:
        return {"algo":"hart_olf","iters":0,"factor":int(f),"cofactor":int(n//f)}

    # 3) SQUFOF (for smaller factors)
    f = _squfof(n, iters=min(250_000, max(50_000, int(budget//4))))
    if f:
        return {"algo":"squfof","iters":0,"factor":int(f),"cofactor":int(n//f)}

    # 4) tiny ECM stage-1 burst (skip for very small n)
    if n.bit_length() > 90:
        curves = 6 if budget < 1_000_000 else 12
        B1_ecm = 30_000 if budget < 1_000_000 else 50_000
        f = _mini_ecm(n, curves=curves, B1=B1_ecm)
        if f:
            return {"algo":"ecm-s1","iters":curves,"factor":int(f),"cofactor":int(n//f)}

    # 5) fallback: Brent ρ + block-GCD
    f, it = _rho_brent_block(n, budget=max(10_000, int(budget)), m=256)
    if f:
        return {"algo":"Pollard Rho (Brent+blockGCD)","iters":int(it),"factor":int(f),"cofactor":int(n//f)}
    return {"algo":"Pollard Rho (Brent+blockGCD)","iters":int(it),"note":"budget exhausted","factor":None,"cofactor":None}
