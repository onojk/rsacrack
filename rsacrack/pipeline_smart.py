from .exec_tools import (
    trial_division, fermat_try, pollard_rho_try_parallel, 
    pm1_try, pp1_try, ecm_try_parallel
)
import math

def get_curves_for_ecm(n: int) -> int:
    digits = len(str(n))
    if digits < 40:
        return 4
    elif digits < 60:
        return 8
    else:
        return 16

def get_instances_for_pollard_rho(n: int) -> int:
    digits = len(str(n))
    if digits < 30:
        return 2
    elif digits < 40:
        return 4
    else:
        return 8

def factorize_smart(n: int, timeout_ms: int = 5000) -> dict:
    steps = []
    time_used_ms = 0
    time_left_ms = timeout_ms

    # Helper to update time left
    def update_time(elapsed):
        nonlocal time_used_ms, time_left_ms
        time_used_ms += elapsed
        time_left_ms = max(0, timeout_ms - time_used_ms)

    # 1. Trial division
    if time_left_ms > 0:
        factor = trial_division(n, time_left_ms / 1000)
        if factor:
            steps.append("trial division hit")
            return {
                "status": "ok",
                "n": str(n),
                "p": str(factor),
                "q": str(n // factor),
                "method": "trial",
                "steps": steps,
                "time_ms": time_used_ms
            }
        steps.append("trial division missed")

    # 2. Fermat's method
    if time_left_ms > 0 and len(str(n)) < 40:  # Fermat is fast for close factors
        factor = fermat_try(n, time_left_ms / 1000)
        if factor:
            steps.append("fermat hit")
            return {
                "status": "ok",
                "n": str(n),
                "p": str(factor),
                "q": str(n // factor),
                "method": "fermat",
                "steps": steps,
                "time_ms": time_used_ms
            }
        steps.append("fermat missed")

    # 3. Pollard's Rho with parallel instances
    if time_left_ms > 0:
        instances = get_instances_for_pollard_rho(n)
        factor = pollard_rho_try_parallel(n, instances=instances, timeout_s=time_left_ms / 1000)
        if factor:
            steps.append(f"pollard_rho hit with {instances} instances")
            return {
                "status": "ok",
                "n": str(n),
                "p": str(factor.p),
                "q": str(n // factor.p),
                "method": factor.method,
                "detail": factor.detail,
                "steps": steps,
                "time_ms": time_used_ms + factor.elapsed_ms
            }
        steps.append("pollard_rho missed")

    # 4. P-1 method
    if time_left_ms > 0:
        # Choose B1 based on n size
        B1 = min(10000, int(math.sqrt(math.sqrt(n))))
        factor = pm1_try(n, B1, timeout_s=time_left_ms / 1000)
        if factor:
            steps.append("p-1 hit")
            return {
                "status": "ok",
                "n": str(n),
                "p": str(factor.p),
                "q": str(n // factor.p),
                "method": factor.method,
                "detail": factor.detail,
                "steps": steps,
                "time_ms": time_used_ms + factor.elapsed_ms
            }
        steps.append("p-1 missed")

    # 5. P+1 method
    if time_left_ms > 0:
        B1 = min(10000, int(math.sqrt(math.sqrt(n))))
        factor = pp1_try(n, B1, timeout_s=time_left_ms / 1000)
        if factor:
            steps.append("p+1 hit")
            return {
                "status": "ok",
                "n": str(n),
                "p": str(factor.p),
                "q": str(n // factor.p),
                "method": factor.method,
                "detail": factor.detail,
                "steps": steps,
                "time_ms": time_used_ms + factor.elapsed_ms
            }
        steps.append("p+1 missed")

    # 6. ECM with parallel curves
    if time_left_ms > 0:
        curves = get_curves_for_ecm(n)
        B1 = 10000
        B2 = 100000
        factor = ecm_try_parallel(n, B1, B2, curves=curves, timeout_s=time_left_ms / 1000)
        if factor:
            steps.append(f"ecm hit with {curves} curves")
            return {
                "status": "ok",
                "n": str(n),
                "p": str(factor.p),
                "q": str(n // factor.p),
                "method": factor.method,
                "detail": factor.detail,
                "steps": steps,
                "time_ms": time_used_ms + factor.elapsed_ms
            }
        steps.append("ecm missed")

    return {
        "status": "timeout" if time_left_ms <= 0 else "no factor found",
        "n": str(n),
        "steps": steps,
        "time_ms": time_used_ms
    }
