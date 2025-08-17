#!/usr/bin/env python3
import math, random, sys, time

def is_probable_prime(n, k=10):
    """Miller-Rabin primality test"""
    if n < 2:
        return False
    # small primes
    for p in [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]:
        if n % p == 0:
            return n == p
    # write n-1 as 2^s * d
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for _ in range(k):
        a = random.randrange(2, n - 1)
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for __ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True

def pollard_rho(n):
    """Pollard’s Rho with retry logic"""
    if n % 2 == 0:
        return 2
    while True:
        x = random.randrange(2, n)
        y = x
        c = random.randrange(1, n)
        d = 1
        while d == 1:
            x = (x * x + c) % n
            y = (y * y + c) % n
            y = (y * y + c) % n
            d = math.gcd(abs(x - y), n)
        if d != n:
            return d

def factor(n, factors=None):
    """Recursive factorization"""
    if factors is None:
        factors = []
    if n == 1:
        return factors
    if is_probable_prime(n):
        factors.append(n)
        return factors
    d = pollard_rho(n)
    factor(d, factors)
    factor(n // d, factors)
    return factors

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python fast_factor.py <N>")
        sys.exit(1)
    N = int(sys.argv[1])
    start = time.time()
    factors = sorted(factor(N))
    elapsed = time.time() - start
    print(f"N = {N}")
    print(f"factors = {factors}")
    print(f"elapsed = {elapsed:.4f} seconds")
