import math, random, shutil, subprocess, time
from typing import Optional, Tuple

# ---- small primes for trial division ----
_SMALL_PRIMES = [
    2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89,97
]
def _more_small_primes(limit=10000):
    sieve = [True]*(limit+1)
    for p in range(2, int(limit**0.5)+1):
        if sieve[p]:
            sieve[p*p:limit+1:p] = [False]*(((limit-p*p)//p)+1)
    return [p for p in range(101, limit+1) if sieve[p]]
_SMALL_PRIMES += _more_small_primes()

# ---- primality ----
def is_probable_prime(n:int)->bool:
    if n < 2: return False
    for p in [2,3,5,7,11,13,17,19,23,29,31,37]:
        if n % p == 0:
            return n == p
    d = n - 1; s = 0
    while d % 2 == 0:
        s += 1; d //= 2
    def chk(a:int)->bool:
        x = pow(a, d, n)
        if x in (1, n-1): return True
        for _ in range(s-1):
            x = (x*x) % n
            if x == n-1: return True
        return False
    for a in [2,325,9375,28178,450775,9780504,1795265022]:
        a %= n
        if a == 0 or chk(a): 
            continue
        return False
    return True

# ---- quick methods ----
def trial_division(n:int)->Optional[int]:
    for p in _SMALL_PRIMES:
        if p*p > n: break
        if n % p == 0: return p
    return None

def pollard_pm1(n:int, B:int=100000)->Optional[int]:
    a = 2
    for p in _SMALL_PRIMES:
        e = int(math.log(B, p))
        if e > 0:
            a = pow(a, p**e, n)
    g = math.gcd(a-1, n)
    return g if 1 < g < n else None

def pollard_rho(n:int, iters:int=1_000_000, seed:Optional[int]=None)->Optional[int]:
    if n % 2 == 0: return 2
    if seed is None: seed = random.randrange(2**63-1)
    random.seed(seed ^ (n<<1))
    for _ in range(12):              # try several polynomials
        c = random.randint(1, n-1)
        f = lambda x: (x*x + c) % n
        x = random.randint(2, n-2); y = x; d = 1
        for _i in range(iters):
            x = f(x); y = f(f(y))
            d = math.gcd(abs(x-y), n)
            if d == 1: 
                continue
            if d == n: 
                break
            return d
    return None

def fermat_close(n:int, limit:int=100000)->Optional[int]:
    # works when p and q are close
    a = math.isqrt(n)
    if a*a < n: a += 1
    for _ in range(limit):
        b2 = a*a - n
        b = int(math.isqrt(b2))
        if b*b == b2:
            p, q = a-b, a+b
            if 1 < p < n: 
                return p
        a += 1
    return None

# ---- ECM wrapper (needs gmp-ecm installed) ----
def ecm_available()->bool:
    return shutil.which("ecm") is not None

def run_ecm(n:int, B1:int=10**5, B2:Optional[int]=None, curves:int=5, threads:int=1, timeout:int=30) -> Tuple[Optional[int], str]:
    if not ecm_available():
        return (None, "ecm not installed")
    cmd = ["ecm", "-q", "-c", str(curves)]
    if threads and threads > 1:
        cmd += ["-t", str(threads)]
    if B2:
        cmd += [str(B1), str(B2), str(n)]
    else:
        cmd += [str(B1), str(n)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return (None, "ECM timeout")
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    # Parse factor from output
    for line in out.splitlines():
        t = line.strip()
        if not t: continue
        if t.isdigit():
            v = int(t)
            if 1 < v < n and n % v == 0:
                return (v, out)
        if "Found" in t:
            digits = "".join(ch if ch.isdigit() else " " for ch in t).split()
            for s in digits:
                if s.isdigit():
                    v = int(s)
                    if 1 < v < n and n % v == 0:
                        return (v, out)
    return (None, out)

# ---- orchestration ----
def quick_factor(n:int, budget_s:float=3.0):
    if n <= 3: return (None, "n too small")
    if is_probable_prime(n): return (None, "n is prime (PRP)")
    t0 = time.time()
    d = trial_division(n)
    if d: return (d, "trial division")
    d = fermat_close(n, 50_000)
    if d: return (d, "Fermat close-primes")
    if time.time()-t0 < budget_s*0.5:
        d = pollard_pm1(n, 100000)
        if d: return (d, "Pollard p-1")
    remain = max(1, int((budget_s - (time.time()-t0)) * 2_000_000))
    d = pollard_rho(n, iters=remain)
    if d: return (d, "Pollard Rho")
    if ecm_available() and (time.time()-t0) < budget_s:
        d, _ = run_ecm(n, B1=100000, curves=3, threads=1, timeout=max(1, int(budget_s)))
        if d: return (d, "ECM taste")
    return (None, "no factor in budget")

def classify(n:int, attempt_s:float=2.0) -> dict:
    info = {
        "bits": n.bit_length(),
        "is_probable_prime": is_probable_prime(n),
        "is_even": (n % 2 == 0),
        "status": "unknown",
        "factor": None,
        "method": None,
    }
    if info["is_probable_prime"]:
        info["status"] = "prime"
        return info
    if n % 2 == 0:
        info.update(status="composite", factor=2, method="even")
        return info
    d, how = quick_factor(n, budget_s=attempt_s)
    if d:
        info.update(status="composite", factor=d, method=how)
    return info
