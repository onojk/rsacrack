#!/usr/bin/env python3
# trail_length.py — compute coil trail length for divisors of n

import math, argparse
from itertools import product
from typing import List
import numpy as np
from sympy import factorint

# --- coil definition (match your repo’s choice) ---
def coil_coords(t: int, omega=0.3):
    r = 1.0 / math.log(t + 2.0)
    theta = omega * t
    x = r * math.cos(theta)
    y = r * math.sin(theta)
    z = float(t)
    return np.array([x, y, z], dtype=float)

def divisors_from_factorization(factors: dict) -> List[int]:
    # factors: {p: e}
    primes, exps = zip(*factors.items()) if factors else ([], [])
    divs = [1]
    for p, e in zip(primes, exps):
        divs = [d * (p ** k) for d in divs for k in range(e + 1)]
    return sorted(divs)

def trail_length(n: int, omega=0.3):
    fac = factorint(n)  # {p: e}
    D = divisors_from_factorization(fac)  # sorted divisors
    P = [coil_coords(d, omega=omega) for d in D]
    # sum of segment lengths
    segs = [np.linalg.norm(P[i+1] - P[i]) for i in range(len(P)-1)]
    L = float(sum(segs))
    chord = float(np.linalg.norm(P[-1] - P[0]))  # C(n)-C(1)
    excess = L - chord
    return D, L, chord, excess

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("N", type=int, nargs="+", help="integers to evaluate")
    ap.add_argument("--omega", type=float, default=0.3, help="coil angular step")
    ap.add_argument("--plot", action="store_true", help="plot 3D trail for the last N")
    args = ap.parse_args()

    for n in args.N:
        D, L, C, E = trail_length(n, omega=args.omega)
        print(f"n={n}")
        print(f"  divisors: {D}")
        print(f"  trail L(n) = {L:.6f}")
        print(f"  chord ||C(n)-C(1)|| = {C:.6f}")
        print(f"  excess E(n)=L(n)-chord = {E:.6f}  ({'prime' if len(D)==2 else 'composite'})")
        print()

    if args.plot:
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
        n = args.N[-1]
        D, _, _, _ = trail_length(n, omega=args.omega)
        P = np.array([coil_coords(d, omega=args.omega) for d in D])
        fig = plt.figure(figsize=(7,8))
        ax = fig.add_subplot(111, projection="3d")
        ax.plot(P[:,0], P[:,1], P[:,2], lw=2, label=f"trail for n={n}")
        ax.scatter(P[:,0], P[:,1], P[:,2], s=25)
        ax.set_title(f"Divisor trail on the conical coil (n={n})")
        ax.set_xlabel("x"); ax.set_ylabel("y"); ax.set_zlabel("t")
        ax.legend()
        plt.tight_layout()
        label = "prime" if len(D) == 2 else "composite"
        plt.tight_layout()
        plt.savefig(f"trail_{n}_{label}.png")
        # plt.show()

if __name__ == "__main__":
    main()
