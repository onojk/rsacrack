#!/usr/bin/env python3
# trail_compare.py — sweep a range and export E(n)

import argparse, csv
from trail_length import trail_length

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("start", type=int)
    ap.add_argument("end", type=int)
    ap.add_argument("--omega", type=float, default=0.3)
    ap.add_argument("--out", default="trail_excess.csv")
    args = ap.parse_args()

    rows = [("n","divisors","L(n)","Chord","Excess","is_prime")]
    for n in range(args.start, args.end+1):
        D, L, C, E = trail_length(n, omega=args.omega)
        rows.append((n, len(D), f"{L:.6f}", f"{C:.6f}", f"{E:.6f}", 1 if len(D)==2 else 0))

    with open(args.out, "w", newline="") as f:
        csv.writer(f).writerows(rows)
    print(f"Wrote {args.out} with {len(rows)-1} rows.")

if __name__ == "__main__":
    main()
