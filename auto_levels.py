#!/usr/bin/env python3
import os, time, json, random
from datetime import datetime
from urllib import request, parse, error

from nextprime_utils import random_prime

BASE_URL   = os.getenv("RSACRACK_URL", "http://127.0.0.1:8080")
LOG_PATH   = os.getenv("AUTO_BENCH_LOG", "autobench.log")

# Levels: (name, p_bits, q_bits, budget_ms)  -- 0 => no timeout (server-side)
LEVELS = [
    ("64x64", 64, 64, 0),
    ("72x72", 72, 72, 0),
    ("80x80", 80, 80, 0),
    ("96x96", 96, 96, 0),
]

MAX_TRIALS_PER_LEVEL = int(os.getenv("MAX_TRIALS_PER_LEVEL", "50"))
SLEEP_BETWEEN_TRIALS = float(os.getenv("SLEEP_BETWEEN_TRIALS", "0.2"))
CLIENT_EXTRA_S       = float(os.getenv("CLIENT_EXTRA_S", "86400"))  # cushion on top of budget

def now():
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"

def log(line: str):
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line.rstrip() + "\n")
    print(line, flush=True)

def http_get_json(url: str, params: dict, timeout_s: float):
    q = parse.urlencode(params)
    req = request.Request(url + "?" + q, headers={
        "User-Agent": "rsacrack-autobench/1.1",
        "Accept": "application/json",
    })
    with request.urlopen(req, timeout=timeout_s) as resp:
        data = resp.read().decode("utf-8", errors="replace")
    return json.loads(data)

def wait_for_health(max_wait_s: float = 120.0):
    t0 = time.time()
    back = 0.5
    while time.time() - t0 < max_wait_s:
        try:
            data = http_get_json(BASE_URL + "/healthz", {}, timeout_s=3.0)
            if data.get("ok") is True:
                return True
        except Exception:
            pass
        time.sleep(back)
        back = min(back * 1.5, 5.0)
    return False

def gen_semiprime(pb: int, qb: int):
    p = random_prime(pb)
    q = random_prime(qb)
    while q == p:
        q = random_prime(qb)
    return p*q, p, q

def product_from_factors_map(fmap: dict) -> int:
    prod = 1
    for k, mult in (fmap or {}).items():
        f = int(k)
        for _ in range(int(mult)):
            prod *= f
    return prod

def attempt(level_name: str, pb: int, qb: int, budget_ms: int, trial_no: int):
    """returns 'ok' | 'fail' | 'transient'"""
    n, p, q = gen_semiprime(pb, qb)
    bits = n.bit_length()
    timeout_s = (budget_ms/1000.0 + CLIENT_EXTRA_S) if budget_ms > 0 else (CLIENT_EXTRA_S)
    t0 = time.perf_counter()
    try:
        data = http_get_json(
            BASE_URL + "/api/factor",
            {"n": str(n), "timeout_ms": str(budget_ms)},
            timeout_s=timeout_s,
        )
    except error.HTTPError as e:
        code = getattr(e, "code", None)
        if code and 500 <= code < 600:
            log(f"{now()} NET_RETRY level={level_name} trial={trial_no} http={code}")
            return "transient"
        log(f"{now()} TRIAL_FAIL level={level_name} trial={trial_no} http={code}")
        return "fail"
    except Exception as e:
        # connection refused / reset / dns / read timeout etc.
        log(f"{now()} NET_RETRY level={level_name} trial={trial_no} err={repr(e)}")
        return "transient"

    elapsed_ms = round((time.perf_counter() - t0) * 1000)
    cls = data.get("classification")
    status = data.get("status")
    fmap = data.get("factors") or {}
    ok = (cls == "composite" and status == "ok" and product_from_factors_map(fmap) == n)

    log(json.dumps({
        "ts": now(), "event": "trial",
        "level": level_name, "trial": trial_no,
        "n_bits": bits, "budget_ms": budget_ms,
        "classification": cls, "status": status,
        "elapsed_ms": elapsed_ms, "ok": ok
    }))

    if ok:
        fb = []
        for k, mult in fmap.items():
            b = int(k).bit_length()
            fb.extend([b]*int(mult))
        fb.sort()
        log(f"{now()} SUCCESS level={level_name} n_bits={bits} elapsed_ms={elapsed_ms} factors_bits={','.join(map(str,fb))}")
        return "ok"

    prev = json.dumps(data)[:200]
    log(f"{now()} ATTEMPT_FAIL level={level_name} n_bits={bits} elapsed_ms={elapsed_ms} payload={prev}")
    return "fail"

def main():
    log(f"{now()} START auto_levels levels={','.join(n for n,_,_,_ in LEVELS)} max_trials={MAX_TRIALS_PER_LEVEL}")
    if not wait_for_health():
        log(f"{now()} WARN healthz not ready; continuing anyway")
    for (name, pb, qb, budget_ms) in LEVELS:
        log(f"{now()} ENTER_LEVEL name={name} pb={pb} qb={qb} budget_ms={budget_ms}")
        trial = 1
        back = 0.5
        while trial <= MAX_TRIALS_PER_LEVEL:
            res = attempt(name, pb, qb, budget_ms, trial)
            if res == "ok":
                log(f"{now()} LEVEL_SUCCESS name={name}")
                break
            if res == "fail":
                trial += 1
                back = 0.5
                time.sleep(SLEEP_BETWEEN_TRIALS)
            else:  # transient
                time.sleep(back)
                back = min(back * 1.5, 5.0)
        else:
            log(f"{now()} LEVEL_FAIL name={name} after_trials={MAX_TRIALS_PER_LEVEL}")
            log(f"{now()} STOP overall_result=FAIL at_level={name}")
            return 1
    log(f"{now()} ALL_LEVELS_SUCCESS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
