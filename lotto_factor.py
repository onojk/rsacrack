import random, time, argparse
from typing import Optional, Tuple, Dict
from cprime_runner import factor_uint64

# Deterministic Miller-Rabin for 64-bit
def _is_probable_prime_64(n: int) -> bool:
    if n < 2: return False
    small = [2,3,5,7,11,13,17,19,23]
    for p in small:
        if n % p == 0:
            return n == p
    d, s = n-1, 0
    while d & 1 == 0:
        d >>= 1; s += 1
    for a in [2,3,5,7,11,13,17]:
        if a % n == 0: return True
        x = pow(a, d, n)
        if x == 1 or x == n-1: continue
        for _ in range(s-1):
            x = (x*x) % n
            if x == n-1: break
        else:
            return False
    return True

# Lotto "tickets": (iters, restarts, per_call_timeout_s)
_TICKETS = [
    (  5_000,  8, 0.06),
    ( 10_000,  8, 0.08),
    ( 20_000, 12, 0.10),
    ( 40_000, 16, 0.12),
    ( 80_000, 16, 0.14),
    (120_000, 16, 0.16),
    (160_000, 16, 0.18),
    (200_000, 16, 0.20),
]

# Default budgets by bit-length (tweak freely)
_DEFAULT_BUDGETS: Dict[range, int] = {
    range(48, 53): 150,   # 48-52 bits → 150 ms
    range(53, 57): 250,   # 53-56 bits → 250 ms
    range(57, 61): 400,   # 57-60 bits → 400 ms
    range(61, 65): 700,   # 61-64 bits → 700 ms
}

def _auto_budget_ms(n: int, fallback_ms: int = 600) -> int:
    bits = n.bit_length()
    for r, ms in _DEFAULT_BUDGETS.items():
        if bits in r:
            return ms
    return fallback_ms

def factor_lotto_64(n: int,
                    budget_ms: Optional[int] = None,
                    seed: Optional[int] = None) -> Optional[Tuple[int,int]]:
    """
    Fail-fast factor attempt for 64-bit n.
    - Uses bit-length to pick a budget if not provided.
    - Repeats short randomized shards with tiny timeouts until budget exhausted.
    Returns (p,q) on success, (n,1) if prime, or None on no factor.
    """
    if n < 0 or n > 0xFFFFFFFFFFFFFFFF:
        return None
    if _is_probable_prime_64(n):
        return (n, 1)
    if budget_ms is None:
        budget_ms = _auto_budget_ms(n)

    if seed is not None:
        random.seed(seed)

    deadline = time.monotonic() + (budget_ms / 1000.0)
    tickets = _TICKETS[:]
    random.shuffle(tickets)

    while time.monotonic() < deadline:
        iters, restarts, per_call = random.choice(tickets)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        per_call = min(per_call, max(0.02, remaining))
        res = factor_uint64(n, iters=iters, restarts=restarts, timeout_s=per_call)
        if res:
            return res
    return None

# Simple CLI: python -m lotto_factor --n N [--budget-ms 600]
def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True, help="64-bit integer to factor")
    ap.add_argument("--budget-ms", type=int, default=None, help="overall time budget in ms")
    ap.add_argument("--seed", type=int, default=None, help="rng seed for reproducibility")
    args = ap.parse_args()
    res = factor_lotto_64(args.n, budget_ms=args.budget_ms, seed=args.seed)
    if res is None:
        print("none")
        raise SystemExit(1)
    p, q = res
    if q == 1:
        print(f"prime {p}")
    else:
        print(f"factors {p} {q}")

if __name__ == "__main__":
    _main()
