import os, random, math, shutil, subprocess, json
from math import gcd

try:
    import gmpy2
    mpz = gmpy2.mpz
    HAVE_GMPY2 = True
except Exception:
    HAVE_GMPY2 = False
    mpz = int

# ---- tiny helpers -----------------------------------------------------------

def _to_int(x):
    if isinstance(x, (bytes, bytearray)):
        x = x.decode()
    if isinstance(x, str):
        x = x.strip()
    return mpz(x)

def _abs(x):
    return x if x >= 0 else -x

def _modmul(a, b, n):
    if HAVE_GMPY2:
        return (a * b) % n
    return (a * b) % n

def _f(x, c, n):
    # x^2 + c mod n
    if HAVE_GMPY2:
        return (x * x + c) % n
    return (x * x + c) % n

def _small_trial(n, limit=10000):
    if n % 2 == 0:
        return mpz(2)
    if n % 3 == 0:
        return mpz(3)
    # 6k±1 wheel
    i, step = 5, 2
    while i <= limit and i * i <= n:
        if n % i == 0:
            return mpz(i)
        i += step
        step = 6 - step
    return None

# ---- Brent ρ with block-GCD (fast constants) --------------------------------

def _rho_brent_batch(n, budget, seed=None, c=None, m=128):
    """Return (factor_or_None, iters_used). budget counts f() evaluations."""
    if n % 2 == 0:
        return mpz(2), 0
    if c is None:
        c = mpz(random.randrange(1, int(n-1))) | 1
    if seed is None:
        seed = mpz(random.randrange(2, int(n-1)))
    y = mpz(seed)
    r = mpz(1)
    q = mpz(1)
    g = mpz(1)
    iters = 0

    while g == 1 and budget > 0:
        x = y
        # advance y by r steps
        for _ in range(int(r)):
            if budget <= 0: break
            y = _f(y, c, n); iters += 1; budget -= 1
        k = 0
        while k < r and g == 1 and budget > 0:
            ys = y
            inner = int(min(m, r - k))
            for _ in range(inner):
                if budget <= 0: break
                y = _f(y, c, n); iters += 1; budget -= 1
                diff = _abs(x - y)
                if diff:
                    q = _modmul(q, diff, n)
            g = mpz(math.gcd(int(q), int(n))) if not HAVE_GMPY2 else gmpy2.gcd(q, n)
            k += inner
        r <<= 1

    if g == n:  # fallback to single-step gcd search
        if budget <= 0:
            return None, iters
        while True:
            if budget <= 0:
                return None, iters
            ys = _f(ys, c, n); iters += 1; budget -= 1
            g = mpz(math.gcd(int(_abs(x - ys)), int(n))) if not HAVE_GMPY2 else gmpy2.gcd(_abs(x - ys), n)
            if g > 1:
                break

    if g == 1 or g == n:
        return None, iters
    return mpz(g), iters

# ---- Optional: escalate to ECM if available ---------------------------------

def _have_ecm():
    return shutil.which("ecm") is not None

def _try_ecm(n, curves=30, B1=10000):
    """Uses external gmp-ecm if present. Returns factor (mpz) or None."""
    if not _have_ecm():
        return None
    try:
        # -q: quiet; -c curves; B1 bound
        p = subprocess.run(
            ["ecm", "-q", "-c", str(curves), str(B1)],
            input=(str(int(n)) + "\n").encode(),
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False, timeout=60
        )
        out = p.stdout.decode(errors="ignore")
        # gmp-ecm prints factors as decimal lines; pick the smallest nontrivial factor
        for line in out.splitlines():
            line = line.strip()
            if not line or not line.isdigit(): 
                continue
            f = mpz(line)
            if 1 < f < n and n % f == 0:
                return f
    except Exception:
        pass
    return None

# ---- Public RQ job -----------------------------------------------------------

def pollard_rho_job(N, budget=500_000, seeds=8, block=256):
    """
    Optimized factor search:
      1) small trial division (fast exit)
      2) Brent ρ + block-GCD with multiple random seeds
      3) optional ECM escalation for medium factors (if `ecm` is installed)
    Returns: dict with factor, cofactor, iters, algo, note
    """
    n = _to_int(N)
    if n <= 1:
        return {"algo": "noop", "iters": 0, "note": "N<=1", "factor": None, "cofactor": None}
    if n % 2 == 0:
        return {"algo": "trial", "iters": 0, "factor": int(2), "cofactor": int(n//2)}

    # 1) tiny trial division
    f = _small_trial(n)
    iters = 0
    if f:
        return {"algo": "trial", "iters": iters, "factor": int(f), "cofactor": int(n//f)}

    # 2) multi-seed Brent ρ (race seeds serially within budget)
    remaining = int(budget)
    for _ in range(max(1, int(seeds))):
        seed = mpz(random.randrange(2, int(n-1)))
        c    = mpz((random.randrange(1, int(n-1)) | 1))
        f, used = _rho_brent_batch(n, remaining, seed=seed, c=c, m=int(block))
        iters += used
        remaining -= used
        if f:
            return {"algo": "Pollard Rho (Brent+blockGCD)", "iters": iters, "factor": int(f), "cofactor": int(n//f)}
        if remaining <= 0:
            break

    # 3) ECM escalation (only if tool exists and n is biggish)
    if _have_ecm() and n.bit_length() >= 80:
        # try a quick set of curves with increasing B1
        for B1, C in [(5000, 20), (20000, 30), (50000, 40)]:
            f = _try_ecm(n, curves=C, B1=B1)
            if f:
                return {"algo": f"ECM(B1={B1},C={C})", "iters": iters, "factor": int(f), "cofactor": int(n//f)}

    return {"algo": "Pollard Rho (Brent+blockGCD)", "iters": iters, "note": "budget exhausted", "factor": None, "cofactor": None}
