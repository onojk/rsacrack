#!/usr/bin/env python3
import json
from pathlib import Path
from flask import Flask, request, send_from_directory, jsonify
from coil_classifier import (
    coil_classify, footprint_for_semiprime,
    geometry_signature, invariant_signature,
)

APP_DIR = Path(__file__).parent.resolve()
WEB_DIR = APP_DIR / "web"
CACHE_DIR = APP_DIR / "cache"
WEB_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

app = Flask(__name__, static_folder=str(WEB_DIR))

@app.get("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")

@app.get("/api/classify")
def api_classify():
    try:
        n = int(request.args.get("n",""))
    except Exception:
        return jsonify(error="bad n"), 400
    r0 = float(request.args.get("r0", 1.0))
    alpha = float(request.args.get("alpha", 0.0125))
    beta = float(request.args.get("beta", 0.005))
    L = float(request.args.get("L", 360.0))

    cls = coil_classify(n)
    out = {"n": n, "class": cls}
    if cls == "semiprime":
        fp = footprint_for_semiprime(n, r0, alpha, beta, L)
        out.update({
            "primes": fp["primes"],
            "normalized": fp["normalized"],
            "balance": fp["balance"],
            "bit_gap": fp["bit_gap"],
            "sig_geom": geometry_signature(n, fp, r0, alpha, beta, L),
            "sig_invariant": invariant_signature(n, fp),
        })
        (CACHE_DIR / f"{out['sig_geom']}.json").write_text(json.dumps(out))
    return jsonify(out)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)

@app.get("/healthz")
def healthz():
    return {"ok": True}

# --- factoring helpers + /api/factor ---
import math, random, time
from sympy import isprime

def _is_square(n:int)->bool:
    if n<0: return False
    r=math.isqrt(n); return r*r==n

def _trial_division(n:int, bound:int=100000):
    # try small primes via wheel-ish stepping; cheap screen before heavier algos
    if n%2==0: return 2
    if n%3==0: return 3
    f=5
    while f<=bound and f*f<=n:
        if n%f==0: return f
        if n%(f+2)==0: return f+2
        f += 6
    return None

def _fermat(n:int, max_steps:int=2_000_000):
    # works best if p≈q; O(|p-q|)
    if n%2==0: return 2
    a=math.isqrt(n)
    if a*a<n: a+=1
    for _ in range(max_steps):
        b2=a*a-n
        if _is_square(b2):
            b=math.isqrt(b2)
            x=a-b
            if 1<x<n and n%x==0: return x
        a+=1
    return None

def _pollard_rho_brent(n:int, max_rounds:int=50):
    if n%2==0: return 2
    if isprime(n): return n
    for _ in range(max_rounds):
        y = random.randrange(1, n-1)
        c = random.randrange(1, n-1)
        m = random.randrange(1, n-1) or 1
        g, r, q = 1, 1, 1
        while g==1:
            x=y
            for __ in range(r):
                y=(pow(y,2,n)+c)%n
            k=0
            while k<r and g==1:
                ys=y
                for __ in range(min(m, r-k)):
                    y=(pow(y,2,n)+c)%n
                    q=(q*abs(x-y))%n
                g=math.gcd(q,n)
                k+=m
            r*=2
        if g==n:
            g=1
            while g==1:
                ys=(pow(ys,2,n)+c)%n
                g=math.gcd(abs(x-ys), n)
        if 1<g<n:
            return g
    return None

@app.get("/api/factor")
def api_factor():
    try:
        n = int(request.args.get("n",""))
    except Exception:
        return jsonify(error="bad n"), 400

    t0 = time.monotonic()
    method = None
    p = None

    # trivial / quick paths
    if n<=1:
        dt = (time.monotonic()-t0)*1000
        return jsonify(n=n, class_="invalid", ms=dt)
    if n%2==0:
        method="even"; p=2
    elif isprime(n):
        method="prime"
        dt=(time.monotonic()-t0)*1000
        return jsonify(n=n, class_="prime", ms=dt)
    elif _is_square(n):
        r=math.isqrt(n)
        if isprime(r):
            method="square_of_prime"
            dt=(time.monotonic()-t0)*1000
            return jsonify(n=n, class_="semiprime", factors=[r,r], method=method, ms=dt)
        # fallthrough if not square of prime

    # small-prime screen
    if p is None:
        p = _trial_division(n, bound=int(request.args.get("trial", "100000")))
        if p: method = "trial"

    # Fermat (good for RSA-like near-balanced)
    if p is None:
        p = _fermat(n, max_steps=int(request.args.get("fermat", "2000000")))
        if p: method = "fermat"

    # Pollard ρ (Brent) fallback
    if p is None:
        p = _pollard_rho_brent(n, max_rounds=int(request.args.get("rho", "60")))
        if p: method = "rho_brent"

    dt = (time.monotonic()-t0)*1000

    if not p:
        # unknown / composite with >2 primes or hard instance
        return jsonify(n=n, class_="unknown", ms=dt, method=method or "none")

    q = n // p
    if p*q != n:
        return jsonify(n=n, class_="other", ms=dt, method=method)

    # order
    p, q = (int(p), int(q)) if p<=q else (int(q), int(p))

    # classify and (if semiprime) attach your coil footprint + signatures
    cls = coil_classify(n)
    resp = {"n": n, "class": cls, "factors": [p,q], "method": method, "ms": dt}
    if cls=="semiprime":
        r0 = float(request.args.get("r0", 1.0))
        alpha = float(request.args.get("alpha", 0.0125))
        beta = float(request.args.get("beta", 0.005))
        L = float(request.args.get("L", 360.0))
        fp = footprint_for_semiprime(n, r0, alpha, beta, L)
        resp.update({
            "footprint": {
                "normalized": fp["normalized"],
                "balance": fp["balance"],
                "bit_gap": fp["bit_gap"],
            },
            "sig_geom": geometry_signature(n, fp, r0, alpha, beta, L),
            "sig_invariant": invariant_signature(n, fp),
        })
    return jsonify(resp)
