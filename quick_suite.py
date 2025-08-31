#!/usr/bin/env python3
import csv, json, random, urllib.request, urllib.parse, time
from math import log10

BASE = "https://rsacrack.com"
UA   = {"User-Agent": "rsacrack-quick-suite"}
TIMEOUT = 12

def jget(path, **params):
    q = urllib.parse.urlencode(params)
    url = f"{BASE}{path}?{q}"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))

def rnd_k_digit(k):
    lo = 10**(k-1)
    hi = 10**k - 1
    return random.randrange(lo, hi)

def cases():
    # Hand-picked sanity
    yield 97, "prime"
    yield 91, "semiprime"
    yield 173*173, "other"

    # A grab-bag across digit ranges
    for k in [2,3,4,5,6,7,8]:
        for _ in range(10):
            yield rnd_k_digit(k), "?"

def is_semiprime_fac(fac):
    f = fac.get("factors") or []
    return fac.get("class") == "semiprime" and len(f)==2 and f[0]*f[1]==fac.get("n")

def main():
    fails = []
    total = 0
    prime_ok = semi_ok = other_ok = 0
    for n, expect in cases():
        total += 1
        try:
            cls = jget("/api/classify", n=str(n))
            fac = jget("/api/factor",   n=str(n))
        except Exception as e:
            fails.append({"n": n, "expect": expect, "reason": f"HTTP: {e}"})
            continue

        c = cls.get("class")
        # Cross-checks
        if c == "prime":
            if fac.get("class_") == "prime":
                prime_ok += 1
            else:
                fails.append({"n": n, "expect": "prime", "reason": f"factor mismatch: {fac.get('class_')}"})
        elif c == "semiprime":
            if is_semiprime_fac(fac):
                # If classify includes primes, make sure they multiply back
                ps = cls.get("primes") or []
                if len(ps)==2 and ps[0]*ps[1]!=n:
                    fails.append({"n": n, "expect": "semiprime", "reason": "classify primes mismatch"})
                else:
                    semi_ok += 1
            else:
                fails.append({"n": n, "expect": "semiprime", "reason": "factor endpoint not semiprime"})
        elif c == "other":
            if fac.get("class") == "semiprime" and is_semiprime_fac(fac):
                fails.append({"n": n, "expect": "other", "reason": "factor says semiprime"})
            else:
                other_ok += 1
        else:
            fails.append({"n": n, "expect": "?", "reason": f"unknown classify: {c}"})

    print("\n=== QUICK SUITE SUMMARY ===")
    print(f"Total: {total} | prime_ok: {prime_ok} | semiprime_ok: {semi_ok} | other_ok: {other_ok} | fails: {len(fails)}")
    if fails:
        fn = "quick_suite_failures.csv"
        with open(fn, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["n","expect","reason"])
            w.writeheader()
            for row in fails:
                w.writerow(row)
        print(f"Wrote failure details to {fn}")

if __name__ == "__main__":
    main()
