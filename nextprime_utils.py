import random

# --- Miller–Rabin primality test ---
def is_probable_prime(n: int, k: int = 10) -> bool:
    if n < 2: return False
    small_primes = [2,3,5,7,11,13,17,19,23,29,31]
    if n in small_primes: return True
    for p in small_primes:
        if n % p == 0: return False
    d, s = n-1, 0
    while d % 2 == 0:
        d //= 2; s += 1
    for _ in range(k):
        a = random.randrange(2, n-1)
        x = pow(a, d, n)
        if x == 1 or x == n-1: continue
        for _ in range(s-1):
            x = pow(x, 2, n)
            if x == n-1: break
        else:
            return False
    return True

# --- Wheel stepper for next prime ---
def next_prime(start: int, return_iters: bool=False):
    n = max(2, start)
    if n <= 2: return (2,0) if return_iters else 2
    if n == 3: return (3,0) if return_iters else 3
    if n % 2 == 0: n += 1
    step, iters = 2, 0
    while True:
        iters += 1
        if is_probable_prime(n):
            return (n,iters) if return_iters else n
        n += step
        step = 6-step

# --- Random prime of ~bits length ---
def random_prime(bits: int):
    if bits < 2: raise ValueError("bits must be >=2")
    while True:
        n = random.getrandbits(bits)
        n |= (1 << (bits-1)) | 1   # ensure top bit + odd
        if is_probable_prime(n):
            return n
