from pathlib import Path
import subprocess
from typing import Optional, Tuple

BIN = Path.home() / "Cprime" / "cprime_rho"

def factor_uint64(n: int,
                  iters: int = 200_000,
                  restarts: int = 64,
                  timeout_s: float = 0.25) -> Optional[Tuple[int,int]]:
    """
    Try factoring 64-bit n via cprime_rho with a hard timeout.
    Returns (p,q) on success, (n,1) if prime, or None on no factor / timeout / failure.
    """
    if n < 0 or n > 0xFFFFFFFFFFFFFFFF:
        return None
    cmd = [str(BIN), "--n", str(n), "--iters", str(iters), "--restarts", str(restarts)]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return None
    if p.returncode != 0:
        return None
    out = p.stdout.strip()
    if out.startswith("factors "):
        _, a, b = out.split()
        return int(a), int(b)
    if out.startswith("prime "):
        return (n, 1)
    return None
