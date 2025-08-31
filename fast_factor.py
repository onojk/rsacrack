from __future__ import annotations
import math, random, time
from typing import Optional, Tuple

# ---- Miller–Rabin (probabilistic; 64-bit deterministic bases) ----
_MR_BASES_64 = (2, 3, 5, 7, 11, 13, 17)
def _is_probable_prime(n: int) -> bool:
    if n < 2: return False
    small = (2,3,5,7,11,13,17,19,23,29)
    for p in small:
        if n == p: return True
        if n % p == 0: return False
    # write n-1 = d * 2^s
    d, s = n - 1, 0
    while d % 2 == 0: d //= 2; s += 1
    def check(a: int) -> bool:
        x = pow(a, d, n)
        if x in (1, n-1): return True
        for _ in range(s-1):
            x = (x * x) % n
            if x == n-1: return True
        return False
    bases = list(_MR_BASES_64)
    rng = random.Random(n ^ 0x9E3779B97F4A7C15)
    while len(bases) < len(_MR_BASES_64) + 3:
        a = rng.randrange(2, min(n-2, 2_000_000_000))
        if a not in bases: bases.append(a)
    for a in bases:
        if a % n and not check(a): return False
    return True

# ---- small trial division (<= 1e7) ----
def _trial_small(n: int, bound: int = 10_000_000) -> Optional[int]:
    if n % 2 == 0: return 2
    if n % 3 == 0: return 3
    f, step = 5, 2
    while f * f <= n and f <= bound:
        if n % f == 0: return f
        f += step; step = 6 - step  # 5,7,11,13,...
    return None

# ---- Pollard's Rho (Brent) ----
def _rho_brent(n: int, rng: random.Random, deadline: float) -> int:
    if n % 2 == 0: return 2
    if _is_probable_prime(n): return n
    while time.perf_counter() < deadline:
        y = rng.randrange(1, n-1)
        c = rng.randrange(1, n-1)
        m = 256
        g = r = q = 1
        while g == 1 and time.perf_counter() < deadline:
            x = y
            for _ in range(r): y = (y*y + c) % n
            k = 0
            while k < r and g == 1 and time.perf_counter() < deadline:
                ys = y
                cnt = min(m, r - k)
                for _ in range(cnt):
                    y = (y*y + c) % n
                    q = (q * (abs(x - y) % n)) % n
                g = math.gcd(q, n)
                k += cnt
            r <<= 1
        if g == n:
            while time.perf_counter() < deadline:
                ys = (ys * ys + c) % n
                g = math.gcd(abs(x - ys), n)
                if g > 1:
                    break
        if 1 < g < n: return g
    return 1

def _factor_one(n: int, deadline: float, rng: random.Random) -> int:
    if n % 2 == 0: return 2
    if _is_probable_prime(n): return n
    sm = _trial_small(n)
    if sm: return sm
    return _rho_brent(n, rng, deadline)

def factor_semiprime(n: int, max_ms: int = 2000) -> Optional[Tuple[int, int, str]]:
    if n <= 1: return None
    if _is_probable_prime(n): return None
    sm = _trial_small(n)
    if sm:
        p, q = sm, n//sm
        if p>q: p,q = q,p
        return int(p), int(q), "trial"
    deadline = time.perf_counter() + (max_ms/1000.0)
    rng = random.Random(n ^ 0xA24BAED4963EE407)
    g = _factor_one(n, deadline, rng)
    if g in (0,1,n): return None
    p, q = int(g), int(n//g)
    if not _is_probable_prime(p):
        g2 = _factor_one(p, deadline, rng)
        if g2 not in (0,1,p):
            p = int(g2); q = int(n//p)
    if not _is_probable_prime(q):
        g2 = _factor_one(q, deadline, rng)
        if g2 not in (0,1,q):
            q = int(g2); p = int(n//q)
    if p*q != n: return None
    if p>q: p,q = q,p
    return int(p), int(q), "rho"
