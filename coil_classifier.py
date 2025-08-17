#!/usr/bin/env python3
import sys
import json
import hashlib
import math
import argparse
import sympy as sp
from typing import Tuple, Dict, Any

# ---------- Classification ----------

def coil_classify(n: int) -> str:
    """
    Returns:
      - "prime"     : n is prime
      - "semiprime" : n = p*q (counting multiplicity = 2)
      - "other"     : n has >=3 prime factors or n<=1 invalid
    """
    if n <= 1:
        return "not valid (≤1)"
    if sp.isprime(n):
        return "prime"
    factors = sp.factorint(n)   # {prime: exponent}
    num_primes = sum(factors.values())
    return "semiprime" if num_primes == 2 else "other"

def semiprime_factors(n: int) -> Tuple[int, int]:
    """
    Precondition: n is semiprime.
    Returns the two prime factors sorted p <= q.
    """
    f = sp.factorint(n)
    # Expand with multiplicity, then pick two
    primes = []
    for p, e in f.items():
        primes.extend([int(p)] * int(e))
    if len(primes) != 2:
        raise ValueError("n is not semiprime by multiplicity")
    p, q = sorted(primes)
    return p, q

# ---------- Coil geometry ----------

def coil_point(n: int, r0: float, alpha: float, beta: float, L: float) -> Tuple[float, float, float]:
    """
    Map integer n to a conical helix point (x,y,z).
    r(n) = r0 + alpha*n
    theta(n) = 2*pi*n / L
    z(n) = beta*n
    """
    r = r0 + alpha * n
    theta = (2.0 * math.pi / L) * n
    x = r * math.cos(theta)
    y = r * math.sin(theta)
    z = beta * n
    return x, y, z

def euclid_dist(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    dz = a[2] - b[2]
    return math.sqrt(dx*dx + dy*dy + dz*dz)

def coil_distance(n1: int, n2: int, r0: float, alpha: float, beta: float, L: float) -> float:
    return euclid_dist(
        coil_point(n1, r0, alpha, beta, L),
        coil_point(n2, r0, alpha, beta, L),
    )

# ---------- Footprint for semiprimes ----------


def _sha256_hex(obj) -> str:
    data = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()

def geometry_signature(n: int, fp: dict, r0: float, alpha: float, beta: float, L: float) -> str:
    """Signature that includes geometry params (changes if r0/alpha/beta/L change)."""
    p, q = fp["primes"]
    norm = fp["normalized"]
    payload = {
        "n": n,
        "primes": [int(p), int(q)],
        "geom": {"r0": r0, "alpha": alpha, "beta": beta, "L": L},
        "norm": [norm["f1"], norm["f2"], norm["f3"]],
    }
    return _sha256_hex(payload)

def invariant_signature(n: int, fp: dict) -> str:
    """Signature independent of geometry, derived from the factor pair."""
    p, q = fp["primes"]
    p, q = (int(p), int(q)) if p <= q else (int(q), int(p))
    balance = fp["balance"]
    bit_gap = fp["bit_gap"]
    log_ratio = math.log(q) - math.log(p)  # ln(q/p)
    payload = {
        "n": n,
        "primes": [p, q],
        "bit_gap": int(bit_gap),
        "balance": float(balance),
        "log_ratio": float(log_ratio),
    }
    return _sha256_hex(payload)

def footprint_for_semiprime(n: int, r0: float, alpha: float, beta: float, L: float) -> Dict[str, Any]:
    """
    For n = p*q (p<=q), returns:
      - primes: (p,q)
      - distances: d1=dist(n,q), d2=dist(q,p), d3=dist(p,1)
      - per_step_slopes: each d / delta_n (Euclidean distance per integer step)
      - normalized: distances normalized to sum=1 (fingerprint shape only)
      - balance: |p-q| / sqrt(n)  (0 = perfectly balanced; larger = more lopsided)
      - bit_gap: |bitlen(p) - bitlen(q)|
    """
    p, q = semiprime_factors(n)

    d1 = coil_distance(n, q, r0, alpha, beta, L)
    d2 = coil_distance(q, p, r0, alpha, beta, L)
    d3 = coil_distance(p, 1, r0, alpha, beta, L)

    # per-step "slope" (distance per integer index)
    # Avoid division by zero: deltas are guaranteed positive here
    s1 = d1 / (n - q)
    s2 = d2 / (q - p)
    s3 = d3 / (p - 1)

    total = d1 + d2 + d3
    norm = (d1/total, d2/total, d3/total) if total > 0 else (0.0, 0.0, 0.0)

    balance = abs(q - p) / math.sqrt(n)
    bit_gap = abs(p.bit_length() - q.bit_length())

    return {
        "primes": (p, q),
        "distances": {"d1_n_to_q": d1, "d2_q_to_p": d2, "d3_p_to_1": d3},
        "per_step_slopes": {"s1": s1, "s2": s2, "s3": s3},
        "normalized": {"f1": norm[0], "f2": norm[1], "f3": norm[2]},
        "balance": balance,
        "bit_gap": bit_gap,
    }

# ---------- CLI ----------

def main():
    ap = argparse.ArgumentParser(
        description="Classify n as prime / semiprime / other and compute coil footprint for semiprimes."
    )
    ap.add_argument("n", type=int, help="Integer to classify")
    ap.add_argument("--r0", type=float, default=1.0, help="Base radius r0")
    ap.add_argument("--alpha", type=float, default=0.0125, help="Cone slope alpha")
    ap.add_argument("--beta", type=float, default=0.005, help="Pitch (z-step) beta")
    ap.add_argument("--L", type=float, default=360.0, help="Angular period L (integers per full turn)")
    ap.add_argument("--signature", action="store_true", help="Print geometry-aware and geometry-invariant signatures for semiprimes")
    ap.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    args = ap.parse_args()

    n = args.n
    cls = coil_classify(n)

    if args.json:
        out = {"n": n, "class": cls}
        if cls == "semiprime":
            out["footprint"] = footprint_for_semiprime(n, args.r0, args.alpha, args.beta, args.L)
        print(json.dumps(out, indent=2))
        return

    # Text output
    print(f"{n} → {cls}")
    if cls == "semiprime":
        fp = footprint_for_semiprime(n, args.r0, args.alpha, args.beta, args.L)
        p, q = fp["primes"]
        print(f"  factors: p={p}, q={q} (bit_gap={fp['bit_gap']}, balance={fp['balance']:.6f})")
        d = fp["distances"]
        print(f"  distances: d1(n→q)={d['d1_n_to_q']:.6f}, d2(q→p)={d['d2_q_to_p']:.6f}, d3(p→1)={d['d3_p_to_1']:.6f}")
        s = fp["per_step_slopes"]
        print(f"  per-step slopes: s1={s['s1']:.6e}, s2={s['s2']:.6e}, s3={s['s3']:.6e}")
        f = fp["normalized"]
        print(f"  normalized footprint: (f1,f2,f3)=({f['f1']:.6f}, {f['f2']:.6f}, {f['f3']:.6f})")
        if args.signature:
            sig_geom = geometry_signature(n, fp, args.r0, args.alpha, args.beta, args.L)
            sig_inv  = invariant_signature(n, fp)
            print(f"  signature (geom-aware):   {sig_geom}")
            print(f"  signature (geom-invariant): {sig_inv}")
        if fp["bit_gap"] == 0:
            print("  note: balanced semiprime (RSA-like).")
        else:
            print("  note: lopsided semiprime (smaller factor is much smaller).")

if __name__ == "__main__":
    main()

