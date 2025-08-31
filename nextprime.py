from math import isqrt
import time
import json
import sys

# Deterministic Miller–Rabin bases for n < 2^64
BASES_2_64 = (2, 325, 9375, 28178, 450775, 9780504, 1795265022)

# small primes for quick filters
SMALL_PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)

def _miller_rabin(n: int, bases) -> bool:
    if n < 2:
        return False
    for p in SMALL_PRIMES:
        if n == p:
            return True
        if n % p == 0:
            return False
    d = n - 1
    s = (d & -d).bit_length() - 1  # count trailing zeros
    d >>= s
    for a in bases:
        a %= n
        if a in (0, 1, n - 1):
            continue
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(s - 1):
            x = (x * x) % n
            if x == n - 1:
                break
        else:
            return False
    return True

def is_probable_prime(n: int) -> bool:
    if n < (1 << 64):
        return _miller_rabin(n, BASES_2_64)  # deterministic in 64-bit range
    return _miller_rabin(n, SMALL_PRIMES)   # very strong SPRP for larger n

def next_prime(start: int, *, return_iters=False):
    if start <= 2:
        return (2, 0) if return_iters else 2
    n = start + (start % 2 == 0)  # make odd if needed
    r = n % 6
    if   r == 0: n += 1
    elif r == 2: n += 3
    elif r == 3: n += 2
    elif r == 4: n += 1
    step = 4 if (n % 6) == 1 else 2  # 6k±1 alternation

    iters = 0
    while True:
        iters += 1
        divisible = False
        for p in SMALL_PRIMES[2:]:
            if n % p == 0 and n != p:
                divisible = True
                break
        if not divisible and is_probable_prime(n):
            return (n, iters) if return_iters else n
        n += step
        step = 6 - step  # toggle 4 <-> 2

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("usage: python3 nextprime.py <start>")
        sys.exit(1)
    start = int(sys.argv[1])
    t0 = time.perf_counter()
    p, iters = next_prime(start, return_iters=True)
    ms = (time.perf_counter() - t0) * 1000
    print(json.dumps({"start": start, "prime": p, "iters": iters, "ms": round(ms, 3)}))
