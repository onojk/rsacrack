from __future__ import annotations
import math, time

try:
    from rsacrack import is_probable_prime
except Exception:
    def _mr(n:int)->bool:
        if n<2: return False
        small=(2,3,5,7,11,13,17,19,23,29,31,37)
        for p in small:
            if n%p==0: return n==p
        d=n-1; s=0
        while d%2==0:
            d//=2; s+=1
        for a in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
            if a%n==0: continue
            x=pow(a,d,n)
            if x==1 or x==n-1: continue
            for _ in range(s-1):
                x=(x*x)%n
                if x==n-1: break
            else:
                return False
        return True
    is_probable_prime=_mr

from .exec_tools import pm1_try, pp1_try, ecm_try

_SMALL_PRIMES = [2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89,97]

def _trial(n:int):
    for p in _SMALL_PRIMES:
        if n%p==0:
            return p if n!=p else None
    return None

def _now_ms():
    return int(time.time()*1000)

def factor_smart(n:int, max_ms:int=3000)->dict|None:
    """
    Returns dict: {p,q,method,steps} or None on timeout/exhaustion.
    CPU-only ladder: trial -> short Fermat -> P-1 -> P+1 -> ECM tiers, staying within max_ms.
    """
    start_ms=_now_ms()
    def time_left():
        return max(0, max_ms - (_now_ms()-start_ms))
    def budget_s(seconds:float)->float:
        # clamp by remaining time
        return max(0.0, min(seconds, time_left()/1000.0))

    steps=[]
    n=int(n)
    if n<=1: return None
    if is_probable_prime(n):
        return {"p":n, "q":1, "method":"prime", "steps":["n is (probable) prime"]}

    # 0) tiny trial
    p=_trial(n)
    if p:
        q=n//p
        return {"p":int(p), "q":int(q), "method":"trial", "steps":["trial division hit"]}

    # 1) quick Fermat for near-square (try a few hundred deltas)
    a = math.isqrt(n)
    if a*a<n: a+=1
    limit = 256
    for i in range(limit):
        b2 = a*a - n
        if b2>=0:
            b = math.isqrt(b2)
            if b*b==b2:
                p = a-b
                q = a+b
                if 1<p<n and n%p==0:
                    return {"p":int(p), "q":int(q), "method":"fermat", "steps":[f"Fermat hit at i={i}"]}
        a += 1
        if time_left() <= 0:
            return None

    # 2) P-1 small/medium bounds
    for (B1,B2,sec) in [(1000, 100000, 0.5), (10000, 1000000, 1.0)]:
        hit = pm1_try(n, B1, B2, timeout_s=budget_s(sec))
        if hit and hit.p:
            p=hit.p; q=n//p
            return {"p":int(p), "q":int(q), "method":"p-1", "steps":steps+[hit.detail]}

    # 3) P+1 small/medium bounds
    for (B1,B2,sec) in [(2000, 200000, 0.5), (20000, 1000000, 1.0)]:
        hit = pp1_try(n, B1, B2, timeout_s=budget_s(sec))
        if hit and hit.p:
            p=hit.p; q=n//p
            return {"p":int(p), "q":int(q), "method":"p+1", "steps":steps+[hit.detail]}

    # 4) ECM tiers (1–few curves within remaining budget)
    for (B1,B2,curves,sec) in [
        (5000,   500000,   2, 1.0),
        (50000,  5000000,  2, 1.5),
        (250000, 20000000, 1, 2.0),
    ]:
        hit = ecm_try(n, B1, B2, curves=curves, timeout_s=budget_s(sec))
        if hit and hit.p:
            p=hit.p; q=n//p
            return {"p":int(p), "q":int(q), "method":"ecm", "steps":steps+[hit.detail]}

        if time_left() <= 0:
            return None

    # Exhausted budget
    return None
