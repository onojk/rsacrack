# rsacrack/factor_pipeline.py
# Biggest-gain factoring pipeline for RSAcrack
# - BPSW probable-prime test (MR base 2 + strong Lucas)
# - Small wheel trial division
# - Pollard-ρ (Brent) with batch-GCD
# - Quick p−1 / p+1
# - Short ECM burst via GMP-ECM `ecm` binary

from __future__ import annotations
import math, random, time, subprocess, shutil
from dataclasses import dataclass
from typing import Optional, Tuple, List

# ---------- Utilities ----------

def is_square(n: int) -> bool:
    if n < 0: return False
    r = math.isqrt(n)
    return r*r == n

def jacobi(a: int, n: int) -> int:
    """Jacobi symbol (a/n), n odd positive."""
    if n <= 0 or n % 2 == 0:
        raise ValueError("n must be odd positive")
    a %= n
    result = 1
    while a:
        # factor out powers of two from a
        t = (a & -a)  # lowest set bit as power-of-two factor
        v2 = (t.bit_length() - 1)
        if v2:
            if n % 8 in (3, 5):
                result = -result
            a >>= v2
        # quadratic reciprocity
        if a % 4 == 3 and n % 4 == 3:
            result = -result
        a, n = n % a, a
    return result if n == 1 else 0

def _miller_rabin_base(n: int, a: int) -> bool:
    """One strong Miller–Rabin round for base a (assuming n>2 odd)."""
    d = n - 1
    s = (d & -d).bit_length() - 1  # v2(n-1)
    d >>= s
    x = pow(a % n, d, n)
    if x == 1 or x == n-1:
        return True
    for _ in range(s-1):
        x = (x * x) % n
        if x == n-1:
            return True
    return False

def _lucas_selfridge_params(n: int) -> Tuple[int,int,int]:
    """
    Selfridge method: find D with Jacobi(D|n) = -1; P=1, Q=(1-D)/4.
    """
    D = 5
    while True:
        j = jacobi(D, n)
        if j == -1:
            P = 1
            Q = (1 - D) // 4
            return (D, P, Q)
        # next candidate: 5, -7, 9, -11, 13, ...
        D = -D - 2 if D > 0 else -D + 2

def _lucas_prp(n: int) -> bool:
    """
    Strong Lucas probable-prime test with Selfridge parameters.
    """
    if n < 2: return False
    if n % 2 == 0: return n == 2
    if is_square(n): return False

    D, P, Q = _lucas_selfridge_params(n)
    # write n+1 = d*2^s
    d = n + 1
    s = (d & -d).bit_length() - 1
    d >>= s

    # Lucas sequences modulo n via binary method
    def lucas_uv(k: int) -> Tuple[int,int]:
        U, V = 0, 2 % n
        Qk = 1
        # exponentiation by squaring on k
        for bit in bin(k)[2:]:
            # double
            U2 = (U * V) % n
            V2 = (V * V - 2 * Qk) % n
            U, V = U2, V2
            Qk = (Qk * Qk) % n
            if bit == '1':
                # add
                U1 = (U + V) % n
                V1 = (V + U * P) % n
                U, V = U1, V1
                Qk = (Qk * Q) % n
        return U % n, V % n

    U, V = lucas_uv(d)
    if U == 0 or V == 0:
        return True
    for _ in range(s-1):
        V = (V * V - 2) % n
        if V == 0:
            return True
    return False

def is_probable_prime(n: int) -> bool:
    """
    Baillie–PSW: trial by small primes, one strong MR base-2 + Lucas PRP.
    Deterministic for all 64-bit and extremely reliable beyond.
    """
    if n < 2: return False
    small_primes = [2,3,5,7,11,13,17,19,23,29,31,37]
    for p in small_primes:
        if n == p:
            return True
        if n % p == 0:
            return False
    if not _miller_rabin_base(n, 2):
        return False
    return _lucas_prp(n)

# ---------- Small trial division (wheel-ish) ----------

def small_trial_division(n: int, limit: int = 100000) -> Tuple[int,int,Optional[int]]:
    """Try to peel a small prime factor up to 'limit'. Returns (n_after, factor_found_or_1, last_tried)."""
    if n % 2 == 0:
        return n//2, 2, 2
    if n % 3 == 0:
        return n//3, 3, 3
    p = 5
    last = None
    while p <= limit and p*p <= n:
        if n % p == 0:
            return n//p, p, p
        q = p + 2
        if q <= limit and n % q == 0:
            return n//q, q, q
        p += 6
        last = p
    return n, 1, last

# ---------- Pollard-ρ (Brent) with batch-GCD ----------

def pollard_rho_brent(n: int, time_ms: int = 1500, seed: Optional[int] = None) -> int:
    """Return a nontrivial factor of n or 1 if failure/timeout."""
    if n % 2 == 0: return 2
    if seed is None:
        seed = random.randrange(2, n-1)
    rand = random.Random(seed)
    deadline = time.time() + (time_ms / 1000.0)
    while time.time() < deadline:
        y = rand.randrange(1, n-1)
        c = rand.randrange(1, n-1)
        m = 128  # batch size for product-of-differences
        g = 1
        r = 1
        q = 1
        f = lambda x: (pow(x, 2, n) + c) % n
        while time.time() < deadline and g == 1:
            x = y
            for _ in range(r):
                y = f(y)
            k = 0
            while k < r and g == 1:
                ys = y
                for _ in range(min(m, r - k)):
                    y = f(y)
                    diff = x - y
                    if diff < 0: diff = -diff
                    q = (q * (diff % n)) % n
                g = math.gcd(q, n)
                k += m
            r <<= 1
        if 1 < g < n:
            return g
        if g == n:
            # backtrack
            while True:
                ys = f(ys)
                g = math.gcd(abs(x - ys), n)
                if g > 1:
                    return g
    return 1

# ---------- GMP-ECM wrappers (p−1, p+1, ECM) ----------

def _run_ecm_lines(args: List[str], timeout_s: float) -> List[str]:
    if not shutil.which("ecm"):
        return []
    try:
        cp = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout_s
        )
    except subprocess.TimeoutExpired:
        return []
    out = (cp.stdout or "") + "\n" + (cp.stderr or "")
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    return lines

def _parse_factor_from_ecm_lines(lines: List[str], n: int) -> int:
    for ln in lines:
        if ln.isdigit():
            f = int(ln)
            if 1 < f < n and n % f == 0:
                return f
        toks = [t for t in ''.join(ch if ch.isdigit() else ' ' for ch in ln).split() if t]
        for t in toks:
            f = int(t)
            if 1 < f < n and n % f == 0:
                return f
    return 0

def quick_pminus1(n: int, B1: int = 100000, timeout_s: float = 2.5) -> int:
    lines = _run_ecm_lines(["ecm", "-q", "-pm1", str(B1), str(n)], timeout_s)
    return _parse_factor_from_ecm_lines(lines, n)

def quick_pplus1(n: int, B1: int = 100000, timeout_s: float = 2.5) -> int:
    lines = _run_ecm_lines(["ecm", "-q", "-pp1", str(B1), str(n)], timeout_s)
    return _parse_factor_from_ecm_lines(lines, n)

def quick_ecm(n: int, digits: int, time_ms: int) -> int:
    """
    A small ECM burst scaled by size/time.
    We pick a B1 and #curves heuristic; let ECM choose B2.
    """
    if digits <= 40:
        B1, curves = 5000, 30
    elif digits <= 60:
        B1, curves = 20000, 60
    elif digits <= 80:
        B1, curves = 50000, 120
    else:
        B1, curves = 110000, 200
    if time_ms < 1000:
        curves = max(10, curves // 6)
    elif time_ms < 3000:
        curves = max(20, curves // 3)

    batch = min(25, curves)
    remaining = curves
    deadline = time.time() + (time_ms / 1000.0)
    while remaining > 0 and time.time() < deadline:
        b = min(batch, remaining)
        lines = _run_ecm_lines(
            ["ecm", "-q", "-c", str(b), "-one", str(B1), str(n)],
            timeout_s=max(1.0, min(6.0, (deadline - time.time()) * 0.9))
        )
        f = _parse_factor_from_ecm_lines(lines, n)
        if f:
            return f
        remaining -= b
    return 0

# ---------- Orchestration ----------

@dataclass
class FactorResult:
    method: str
    p: int
    q: int
    steps: List[str]

def _finish(n: int, f: int, steps: List[str], method: str) -> FactorResult:
    p = f
    q = n // f
    if p > q: p, q = q, p
    steps.append(f"FOUND {method}: {p} × {q}")
    return FactorResult(method=method, p=p, q=q, steps=steps)

def factor_one(n: int, time_ms: int = 3000) -> Optional[FactorResult]:
    """
    Main entry. Tries: trial -> p−1 -> p+1 -> ρ(Brent) -> ECM burst.
    Recurses once if a composite cofactor remains and budget allows.
    """
    start = time.time()
    steps: List[str] = []

    if n <= 1:
        return None
    if is_probable_prime(n):
        steps.append("n is probable prime (BPSW)")
        return FactorResult(method="prime", p=n, q=1, steps=steps)

    # Peel small factors quickly
    N = n
    N, f, last = small_trial_division(N, limit=100000)
    if f != 1:
        steps.append(f"trial division found {f}")
        if is_probable_prime(N):
            return _finish(n, f, steps, "trial")
        # recurse once on remaining cofactor (use half budget)
        sub = factor_one(N, max(500, time_ms // 2))
        if sub and sub.q == 1:
            return _finish(n, f, steps + sub.steps, "trial+recurse")
        if sub:
            p = f
            q = sub.p * sub.q
            steps += sub.steps
            g = math.gcd(n, p)
            if g == 1: g = math.gcd(n, q)
            return _finish(n, g, steps, "trial+recurse")

    digits = len(str(N))
    rem_ms = max(200, int((start + time_ms/1000.0 - time.time()) * 1000))

    # Cheap algebraic methods first
    if rem_ms > 200:
        f = quick_pminus1(N, B1=100000, timeout_s=min(2.5, rem_ms/1000.0))
        if 1 < f < N:
            steps.append(f"p−1 found {f}")
            return _finish(n, f, steps, "p-1")

    rem_ms = max(150, int((start + time_ms/1000.0 - time.time()) * 1000))
    if rem_ms > 150:
        f = quick_pplus1(N, B1=100000, timeout_s=min(2.5, rem_ms/1000.0))
        if 1 < f < N:
            steps.append(f"p+1 found {f}")
            return _finish(n, f, steps, "p+1")

    # Pollard-ρ (Brent) with batch-GCD
    rem_ms = max(300, int((start + time_ms/1000.0 - time.time()) * 1000))
    f = pollard_rho_brent(N, time_ms=min(1500, rem_ms))
    if 1 < f < N:
        steps.append(f"ρ(Brent) found {f}")
        return _finish(n, f, steps, "rho-brent")

    # ECM burst
    rem_ms = max(400, int((start + time_ms/1000.0 - time.time()) * 1000))
    f = quick_ecm(N, digits, rem_ms)
    if 1 < f < N:
        steps.append(f"ECM found {f}")
        return _finish(n, f, steps, "ecm")

    steps.append("no factor found in budget")
    return None

# ---------- Tiny CLI for quick testing ----------
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 factor_pipeline.py <n> [time_ms]")
        sys.exit(1)
    n = int(sys.argv[1])
    t = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
    res = factor_one(n, t)
    if not res:
        print("FAILED: no factor in time budget")
    else:
        print(f"{res.p} {res.q}  # method={res.method}")
        for s in res.steps:
            print("  -", s)
