from __future__ import annotations
import shutil, subprocess, re, time, os, math
import concurrent.futures
import random
from dataclasses import dataclass

ECM_BIN = shutil.which("ecm")
_FACT_RE = re.compile(r"(?:(?:Found input number has a factor:)|(?:Factor found.*?:))\s*([0-9]{2,})")

@dataclass
class FactorHit:
    method: str
    p: int
    detail: str
    elapsed_ms: int

def _run_with_stdin(cmd:list[str], input_data:str, timeout:float)->tuple[int,str,str,int]:
    t0=time.time()
    p = subprocess.run(cmd, input=input_data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       text=True, timeout=timeout)
    ms = int((time.time()-t0)*1000)
    return p.returncode, p.stdout, p.stderr, ms

def _pick_factor(n:int, text:str)->int|None:
    for m in _FACT_RE.finditer(text):
        try:
            f = int(m.group(1))
            if 1 < f < n and n % f == 0:
                return f
        except Exception:
            pass
    return None

def _ecm_available() -> bool:
    return bool(ECM_BIN)

# Trial division function
def trial_division(n: int, timeout_s: float = 10.0) -> int | None:
    t0 = time.time()
    if n % 2 == 0:
        return 2
    if n % 3 == 0:
        return 3
    limit = min(int(math.isqrt(n)) + 1, 1000000)
    for i in range(5, limit, 6):
        if time.time() - t0 > timeout_s:
            return None
        if n % i == 0:
            return i
        if n % (i + 2) == 0:
            return i + 2
    return None

# Fermat's factorization method - fixed implementation
def fermat_try(n: int, timeout_s: float = 10.0) -> int | None:
    t0 = time.time()
    if n % 2 == 0:
        return 2
    
    # Check if n is a perfect square
    root = math.isqrt(n)
    if root * root == n:
        return root
    
    # Fermat's algorithm for odd numbers
    x = math.isqrt(n) + 1
    while time.time() - t0 < timeout_s:
        y2 = x * x - n
        y = math.isqrt(y2)
        if y * y == y2:
            factor = x - y
            if factor != 1 and factor != n:  # Avoid trivial factors
                return factor
        x += 1
    return None

# Improved Pollard's Rho implementation using Brent's algorithm
def pollard_rho(n: int, timeout_s: float = 10.0) -> int | None:
    t0 = time.time()
    if n % 2 == 0:
        return 2
    
    # Check for small factors first
    for p in [3, 5, 7, 11, 13, 17, 19, 23, 29, 31]:
        if n % p == 0:
            return p
    
    # Brent's algorithm
    y = random.randint(1, n-1)
    c = random.randint(1, n-1)
    m = random.randint(1, n-1)
    g = r = q = 1
    i = 0
    
    while g == 1 and time.time() - t0 < timeout_s:
        x = y
        for _ in range(r):
            y = (y*y + c) % n
        k = 0
        while k < r and g == 1:
            ys = y
            for _ in range(min(m, r-k)):
                y = (y*y + c) % n
                q = (q * abs(x-y)) % n
            g = math.gcd(q, n)
            k += m
        r *= 2
    
    if g == n:
        while g == 1:
            ys = (ys*ys + c) % n
            g = math.gcd(abs(x-ys), n)
    
    return g if 1 < g < n else None

def pollard_rho_try(n: int, timeout_s: float = 10.0) -> FactorHit | None:
    t0 = time.time()
    try:
        f = pollard_rho(n, timeout_s=timeout_s)
    except TimeoutError:
        return None
    ms = int((time.time() - t0) * 1000)
    if f and 1 < f < n and n % f == 0:
        return FactorHit("pollard_rho", f, "Pollard's Rho", ms)
    return None

def pollard_rho_try_parallel(n: int, instances: int = 1, timeout_s: float = 10.0) -> FactorHit | None:
    if instances <= 1:
        return pollard_rho_try(n, timeout_s)
    
    num_workers = min(instances, os.cpu_count() or 1)
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(pollard_rho_try, n, timeout_s) for _ in range(instances)]
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
            except Exception as e:
                continue
            if result is not None:
                for f in futures:
                    f.cancel()
                return result
    return None

def ecm_try(n:int, B1:int, B2:int|None=None, timeout_s:float=30.0)->FactorHit|None:
    if not _ecm_available():
        return None
    args = [ECM_BIN]
    if B2: args += [str(B1), str(B2)]
    else:  args += [str(B1)]
    rc, out, err, ms = _run_with_stdin(args, str(n), timeout_s)
    f = _pick_factor(n, out + "\n" + err)
    return FactorHit("ecm", f, f"ECM B1={B1} B2={B2}", ms) if f else None

def ecm_try_parallel(n: int, B1: int, B2: int | None = None, curves: int = 1, timeout_s: float = 30.0) -> FactorHit | None:
    if not _ecm_available():
        return None
    if curves <= 1:
        return ecm_try(n, B1, B2, timeout_s)
    
    num_workers = min(curves, os.cpu_count() or 1)
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(ecm_try, n, B1, B2, timeout_s) for _ in range(curves)]
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
            except Exception as e:
                continue
            if result is not None:
                for f in futures:
                    f.cancel()
                return result
    return None

def pm1_try(n:int, B1:int, B2:int|None=None, timeout_s:float=10.0)->FactorHit|None:
    if not _ecm_available():
        return None
    args = [ECM_BIN, "-pm1"]
    if B2: args += [str(B1), str(B2)]
    else:  args += [str(B1)]
    rc, out, err, ms = _run_with_stdin(args, str(n), timeout_s)
    f = _pick_factor(n, out + "\n" + err)
    return FactorHit("p-1", f, f"P-1 B1={B1} B2={B2}", ms) if f else None

def pp1_try(n:int, B1:int, B2:int|None=None, timeout_s:float=10.0)->FactorHit|None:
    if not _ecm_available():
        return None
    args = [ECM_BIN, "-pp1"]
    if B2: args += [str(B1), str(B2)]
    else:  args += [str(B1)]
    rc, out, err, ms = _run_with_stdin(args, str(n), timeout_s)
    f = _pick_factor(n, out + "\n" + err)
    return FactorHit("p+1", f, f"P+1 B1={B1} B2={B2}", ms) if f else None
