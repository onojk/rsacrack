import json, random, csv, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from sympy import randprime, isprime

BASE = "https://rsacrack.com"
TIMEOUT = 15  # seconds

def http_json(path, params):
    url = f"{BASE}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent":"rsacrack-tester"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))

def classify(n):  return http_json("/api/classify", {"n": str(n)})
def factor(n):    return http_json("/api/factor",   {"n": str(n)})

def rand_k_digit_prime(k):
    lo = 10**(k-1)
    hi = 10**k - 1
    return randprime(lo, hi)

def rand_semiprime(k):
    # p and q near half the digits each (works even for k=1,2)
    k1 = max(1, k//2)
    k2 = max(1, k - k1)
    p = rand_k_digit_prime(k1)
    q = rand_k_digit_prime(k2)
    return int(p)*int(q), sorted([int(p), int(q)])

def rand_composite_non_semiprime(k):
    # Make something with ≥3 prime factors or a prime power.
    # For small k, multiply three smallish primes; for larger k, multiply random ints.
    if k <= 6:
        a = randprime(2, 97)
        b = randprime(2, 97)
        c = randprime(2, 97)
        n = int(a)*int(b)*int(c)
    else:
        a = random.randrange(10**(k-1), 10**k)
        b = random.randrange(2, 999)
        n = a * b
    if isprime(n):  # guard (should be rare)
        n *= 2
    return int(n)

def check_semiprime(n, classify_res, factor_res):
    c = classify_res.get("class")
    if c != "semiprime":
        return False, f"classify != semiprime (got {c})"
    # If the classify endpoint provided primes, make sure factor endpoint agrees (when we called it)
    primes_cls = sorted(classify_res.get("primes", []))
    if factor_res and "factors" in factor_res:
        f = factor_res["factors"]
        if len(f) == 2 and f[0]*f[1] == n:
            if primes_cls and sorted(f) != primes_cls:
                return False, f"mismatch primes vs factors: {primes_cls} vs {sorted(f)}"
        else:
            return False, f"factor invalid factors: {f}"
    return True, ""

def check_prime(n, classify_res, factor_res):
    c = classify_res.get("class")
    if c == "prime":
        return True, ""
    # factor endpoint may say class_:"prime" or class:"prime"
    if factor_res and (factor_res.get("class_") == "prime" or factor_res.get("class") == "prime"):
        return True, ""
    return False, f"prime disagreement (classify={c}, factor={factor_res})"

def check_other(n, classify_res, factor_res):
    c = classify_res.get("class")
    # anything not 'semiprime' is acceptable for "other"
    return (c != "semiprime"), ("" if c != "semiprime" else "classified as semiprime")

def run_case(n, expect):
    # factor() only for ≤9 digits (fast path)
    do_factor = len(str(n)) <= 9
    cls = classify(n)
    fac = factor(n) if do_factor else None

    if expect == "semiprime":
        ok, reason = check_semiprime(n, cls, fac)
    elif expect == "prime":
        ok, reason = check_prime(n, cls, fac)
    else:
        ok, reason = check_other(n, cls, fac)

    return {
        "n": str(n),
        "digits": len(str(n)),
        "expect": expect,
        "classify_class": cls.get("class"),
        "factor_class": (fac.get("class_") or fac.get("class")) if fac else None,
        "factor_factors": fac.get("factors") if fac else None,
        "ok": ok,
        "reason": reason,
    }

def main():
    random.seed(42)
    jobs = []

    # A) Handpicked fixtures
    jobs += [(97, "prime"), (91, "semiprime"), (17947, "semiprime"), (118901521, "other")]

    # B) Random semiprimes
    for k in [2,3,4,5,6,7,8,9]:     # small: factor+classify
        for _ in range(5):
            n, _ = rand_semiprime(k)
            jobs.append((n, "semiprime"))
    for k in [10,12,14,16]:        # larger: classify only
        for _ in range(5):
            n, _ = rand_semiprime(k)
            jobs.append((n, "semiprime"))

    # C) Random primes
    for k in [2,3,4,5,6,7,8,9]:
        for _ in range(3):
            jobs.append((rand_k_digit_prime(k), "prime"))
    for k in [10,12,14,16]:
        for _ in range(3):
            jobs.append((rand_k_digit_prime(k), "prime"))

    # D) Random non-semiprime composites
    for k in [3,4,5,6,7,8,9]:
        for _ in range(4):
            jobs.append((rand_composite_non_semiprime(k), "other"))
    for k in [10,12,14,16]:
        for _ in range(4):
            jobs.append((rand_composite_non_semiprime(k), "other"))

    results = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(run_case, n, tag) for n, tag in jobs]
        for fut in as_completed(futs):
            try:
                results.append(fut.result())
            except Exception as e:
                results.append({"n": "?", "digits": 0, "expect":"?", "classify_class":None, "factor_class":None, "factor_factors":None, "ok":False, "reason": f"exception: {e}"})

    # Summary
    total = len(results)
    ok = sum(1 for r in results if r["ok"])
    by = {}
    for r in results:
        by.setdefault(r["expect"], [0,0])
        if r["ok"]: by[r["expect"]][0]+=1
        else: by[r["expect"]][1]+=1

    print("\n=== SUMMARY ===")
    print(f"Total: {total} | PASS: {ok} | FAIL: {total-ok}")
    for k,(p,f) in by.items():
        print(f"  {k:10s}  PASS {p:3d}  FAIL {f:3d}")

    fails = [r for r in results if not r["ok"]]
    if fails:
        fn = "accuracy_failures.csv"
        with open(fn, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(fails[0].keys()))
            w.writeheader()
            w.writerows(fails)
        print(f"\nWrote details for {len(fails)} failures to {fn}")
    else:
        print("\nNo failures recorded.")

if __name__ == "__main__":
    main()
