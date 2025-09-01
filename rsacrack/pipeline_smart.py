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
        d=n-1;s=0
        while d%2==0: d//=2; s+=1
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

def factor_smart(n:int, max_ms:int=3000)->dict|None:
    """
    Returns dict: {p,q,method,steps} or None on timeout/exhaustion.
    CPU-only ladder: trial -> Fermat (short range) -> P-1 -> P+1 -> ECM tiers
    """
    t0=time.time()
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

    # 1) quick Fermat (|p-q| small)
    a = math.isqrt(n)
    if a*a<n: a+=1
    for i in range(1,256):
        b2 = a*a - n
        if b2>=0:
            b = math.isqrt(b2)
            if b*b==b2:
                p=a-b; q=a+b
                if 1<p<n:
                    return {"p":int(p), "q":int(q), "method":"fermat", "steps":[f"Fermat i={i}"]}
        a+=1
        if (time.time()-t0)*1000>max_ms: return None

    def budget_ms(): return int((time.time()-t0)*1000)

    # 2) P-1 tiers
    for (B1,B2,ts) in [(50_000, 5_000_000, 2.0), (500_000, 50_000_000, 3.5)]:
        if budget_ms()>max_ms: return None
        hit = pm1_try(n,B1,B2,timeout_s=ts)
        steps.append(f"P-1 {B1}/{B2} -> {'hit' if hit and hit.p else 'miss'}")
        if hit and hit.p:
            p=hit.p; q=n//p
            return {"p":int(p), "q":int(q), "method":"p-1", "steps":steps+[hit.detail]}

    # 3) P+1 tiers
    for (B1,B2,ts) in [(50_000, 5_000_000, 2.0), (300_000, 30_000_000, 3.0)]:
        if budget_ms()>max_ms: return None
        hit = pp1_try(n,B1,B2,timeout_s=ts)
        steps.append(f"P+1 {B1}/{B2} -> {'hit' if hit and hit.p else 'miss'}")
        if hit and hit.p:
            p=hit.p; q=n//p
            return {"p":int(p), "q":int(q), "method":"p+1", "steps":steps+[hit.detail]}

    # 4) ECM tiers
    ecm_tiers = [
        (50_000,    5_000_000,   30, 3.0),
        (250_000,  25_000_000,   60, 5.0),
        (1_000_000,100_000_000, 120, 8.0),
    ]
    for (B1,B2,curves,ts) in ecm_tiers:
        if budget_ms()>max_ms: return None
        hit = ecm_try(n,B1,B2,curves=curves, timeout_s=ts)
        steps.append(f"ECM {B1}/{B2} c={curves} -> {'hit' if hit and hit.p else 'miss'}")
        if hit and hit.p:
            p=hit.p; q=n//p
            return {"p":int(p), "q":int(q), "method":"ecm", "steps":steps+[hit.detail]}

    return None
