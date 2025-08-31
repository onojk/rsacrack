import os, math
from redis import Redis
from rq import get_current_job

def pollard_rho_job(N: int, budget: int = 1_000_000, check_every: int = 2000):
    job = get_current_job()
    rid = job.id if job else None
    r = Redis()  # default: redis://localhost:6379/0

    if N <= 1:
        return {"error": "N must be > 1"}

    bits = N.bit_length()
    if job:
        job.meta.update({"bits": bits, "budget": budget, "iters": 0})
        job.save_meta()

    if N % 2 == 0:
        return {"factor": 2, "cofactor": N // 2, "iters": 0, "algo": "Pollard Rho"}

    rnd = int.from_bytes(os.urandom(16), "big")
    c = (rnd % (N - 1)) + 1
    x = y = 2
    g = 1
    iters = 0

    while iters < budget and g == 1:
        x = (x * x + c) % N
        y = (y * y + c) % N
        y = (y * y + c) % N
        g = math.gcd(abs(x - y), N)
        iters += 1

        if job and iters % check_every == 0:
            job.meta["iters"] = iters
            job.save_meta()
            if rid and r.get(f"abort:{rid}"):
                return {"aborted": True, "iters": iters}

    if 1 < g < N:
        return {"factor": int(g), "cofactor": int(N // g), "iters": iters, "algo": "Pollard Rho"}
    return {"factor": None, "iters": iters, "note": "budget exhausted"}
