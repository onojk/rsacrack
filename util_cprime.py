from typing import Optional, Tuple
from cprime_runner import factor_uint64

def try_factor_if_u64(n: int,
                      iters: int = 300_000,
                      restarts: int = 128) -> Optional[Tuple[int,int]]:
    """If n fits in 64 bits, try C prime rho; otherwise return None."""
    if n < 0 or n > 0xFFFFFFFFFFFFFFFF:
        return None
    return factor_uint64(n, iters=iters, restarts=restarts)
