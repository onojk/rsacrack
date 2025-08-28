from pathlib import Path
import subprocess
from typing import Optional, Tuple

BIN = Path.home() / "Cprime" / "cprime_rho"

def factor_uint64(n: int, iters: int = 200_000, restarts: int = 64) -> Optional[Tuple[int,int]]:
    """
    Try factoring 64-bit n using cprime_rho. Returns (p, q) or None if not found.
    Exit codes: 0 = prime/factors/unknown handled by stdout; nonzero = failure.
    """
    cmd = [str(BIN), "--n", str(n), "--iters", str(iters), "--restarts", str(restarts)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        return None
    out = p.stdout.strip()
    if out.startswith("factors "):
        _, a, b = out.split()
        return (int(a), int(b))
    if out.startswith("prime "):
        return (n, 1)  # or return None; your call
    return None
