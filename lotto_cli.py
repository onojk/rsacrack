import sys, argparse
from lotto_factor import factor_lotto_64

def process(n: int, budget_ms: int|None):
    res = factor_lotto_64(n, budget_ms=budget_ms)
    if res is None: print(f"{n}\tnone"); return 1
    p, q = res
    if q == 1: print(f"{n}\tprime\t{p}"); return 0
    print(f"{n}\tfactors\t{p}\t{q}"); return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget-ms", type=int, default=None, help="override auto budget")
    ap.add_argument("N", nargs="*", type=int, help="optional list of integers")
    args = ap.parse_args()

    rc = 0
    if args.N:
        for n in args.N:
            rc |= process(n, args.budget_ms)
    else:
        for line in sys.stdin:
            line=line.strip()
            if not line: continue
            try: n=int(line,10)
            except: 
                print(f"# skip: {line}", file=sys.stderr); rc |= 1; continue
            rc |= process(n, args.budget_ms)
    raise SystemExit(rc)

if __name__ == "__main__":
    main()
