#!/usr/bin/env python3
from __future__ import annotations
import math, random, time, os, subprocess, shutil

try:
    import gmpy2
    HAVE_GMPY2 = True
    def _gcd(a,b): return int(gmpy2.gcd(a,b))
    def _powmod(a,e,n): return int(gmpy2.powmod(a,e,n))
    def _is_square(n): return gmpy2.is_square(n)
    def _is_prime_gmp(n:int)->bool: return gmpy2.is_prime(n) > 0
except Exception:
    HAVE_GMPY2 = False
    def _gcd(a,b): return math.gcd(a,b)
    def _powmod(a,e,n): return pow(a,e,n)
    def _is_square(n): r=math.isqrt(n); return r*r==n

_SMALL_PRIMES = (2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89,97)
_MR_BASES_64 = (2,3,5,7,11,13,17); _MR_EXTRA=(19,23,29,31,37)

def _mr_pass(a,s,d,n):
    x=_powmod(a,d,n)
    if x in (1,n-1): return True
    for _ in range(s-1):
        x=(x*x)%n
        if x==n-1: return True
    return False

def _is_probable_prime_py(n:int)->bool:
    if n<2: return False
    for p in _SMALL_PRIMES:
        if n==p: return True
        if n%p==0: return False
    d=n-1; s=(d & -d).bit_length()-1; d >>= s
    bases=list(_MR_BASES_64 if n < (1<<64) else _MR_BASES_64+_MR_EXTRA)
    if n >= (1<<64):
        rng=random.Random(n ^ 0x9E3779B97F4A7C15)
        for _ in range(2):
            a=rng.randrange(2,n-2)
            if a not in bases: bases.append(a)
    for a in bases:
        a%=n
        if a in (0,1,n-1): continue
        if not _mr_pass(a,s,d,n): return False
    return True

def is_probable_prime(n:int)->bool:
    return _is_prime_gmp(n) if HAVE_GMPY2 else _is_probable_prime_py(n)

def _trial_division(n:int, bound:int=100000)->int|None:
    for p in (2,3,5):
        if n%p==0: return p
    f, steps, i = 7, (4,2,4,2,4,6,2,6), 0
    while f*f<=n and f<=bound:
        if n%f==0: return f
        f += steps[i]; i=(i+1)&7
    return None

def _pollard_pm1(n:int, B:int=200000)->int:
    if n%2==0: return 2
    a=2
    for k in range(2,B+1):
        a=_powmod(a,k,n)
    g=_gcd(a-1,n)
    return g if 1<g<n else 1

def _rho_brent(n:int, rng:random.Random, limit_iters:int=1_000_000)->int:
    if n%2==0: return 2
    if is_probable_prime(n): return n
    for _try in range(8):
        y=rng.randrange(1,n-1); c=rng.randrange(1,n-1)
        m=1<<rng.randrange(5,9); g=r=q=1; x=0; it=0
        while g==1 and it<limit_iters:
            x=y
            for _ in range(r): y=(y*y+c)%n
            k=0
            while k<r and g==1 and it<limit_iters:
                ys=y; cnt=min(m, r-k)
                for _ in range(cnt):
                    y=(y*y+c)%n
                    q=(q*(x-y)%n)%n
                g=_gcd(q,n); k+=cnt; it+=cnt
            r<<=1
        if 1<g<n: return g
        if g==n:
            while True:
                ys=(ys*ys+c)%n
                g=_gcd(abs(x-ys),n)
                if 1<g<n: return g
                if g==n: break
    return 1

def _seconds_left(deadline):
    return float('inf') if deadline is None else (deadline - time.perf_counter())

def _try_ecm(n:int, seconds_left:float)->int:
    ecm=shutil.which("ecm")
    if not ecm or seconds_left<3: return 1
    if seconds_left==float('inf'):
        curves,B1 = 5000,"1e7"; timeout_kw={}
    elif seconds_left<10:   curves,B1 = 50,   "5e4";  timeout_kw={"timeout":max(2,int(seconds_left-1))}
    elif seconds_left<30:   curves,B1 = 200,  "2e5";  timeout_kw={"timeout":max(2,int(seconds_left-1))}
    elif seconds_left<90:   curves,B1 = 800,  "1e6";  timeout_kw={"timeout":max(2,int(seconds_left-1))}
    else:                   curves,B1 = 2000, "3e6";  timeout_kw={"timeout":max(2,int(seconds_left-1))}
    try:
        p = subprocess.run([ecm,"-c",str(curves),"-one","-q",str(B1)],
            input=(str(n)+"\n").encode(), stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, **timeout_kw)
        for tok in p.stdout.decode(errors="ignore").split():
            try:
                g=int(tok)
                if 1<g<n and n%g==0: return g
            except: pass
    except Exception:
        pass
    return 1

def _factor_rec(n:int, out:list[int], deadline):
    if n==1: return
    if is_probable_prime(n): out.append(int(n)); return
    f=_trial_division(n)
    if f:
        _factor_rec(f,out,deadline); _factor_rec(n//f,out,deadline); return
    r=math.isqrt(n)
    if r*r==n:
        _factor_rec(r,out,deadline); _factor_rec(r,out,deadline); return
    left=_seconds_left(deadline)
    if left>0:
        B=200000 if (left==float('inf') or left>10) else 50000
        g=_pollard_pm1(n,B=B)
        if 1<g<n:
            _factor_rec(g,out,deadline); _factor_rec(n//g,out,deadline); return
    left=_seconds_left(deadline)
    if left>3 or left==float('inf'):
        g=_try_ecm(n,left)
        if 1<g<n:
            _factor_rec(g,out,deadline); _factor_rec(n//g,out,deadline); return
    rng=random.Random(n ^ 0xA24BAED4963EE407)
    while deadline is None or time.perf_counter() < deadline:
        g=_rho_brent(n,rng,limit_iters=500_000)
        if 1<g<n:
            _factor_rec(g,out,deadline); _factor_rec(n//g,out,deadline); return
        rng.seed(rng.randrange(1<<63) ^ (n<<7))

def factor(n:int)->list[int]:
    if n<2: return [n]
    for p in _SMALL_PRIMES:
        if n==p: return [p]
    s=os.getenv("FACTOR_MAX_SECONDS","0").strip().lower()
    deadline=None if s in ("","0","inf","infinite") else (time.perf_counter()+float(s))
    out=[]; _factor_rec(int(n), out, deadline); return out

def tangent_equal_split_info(*a,**k): return {"note":"not implemented"}
def tangent_prime_test_split_info(*a,**k): return {"note":"not implemented"}
