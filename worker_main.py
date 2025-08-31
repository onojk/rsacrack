import os, sys, time, json, random, requests

BASE_URL      = (os.getenv("BASE_URL", "https://rsacrack.com") or "https://rsacrack.com").rstrip("/")
TARGET_N      = os.getenv("TARGET_N", "110000479000513")
BUDGET_MS     = int(os.getenv("BUDGET_MS", "3000"))
READ_TIMEOUT  = float(os.getenv("READ_TIMEOUT", "90"))
MAX_TRIES     = int(os.getenv("MAX_TRIES", "4"))
TASK_BUDGET_S = float(os.getenv("TASK_BUDGET_S", "240"))

# Cloud Run exposes this; fallback to 0 when not present
TASK_INDEX = int(os.getenv("CLOUD_RUN_TASK_INDEX", "0"))

# --- Stagger start: spread load across your VM ---
# up to ~30s max stagger; spaced by index and a dash of randomness
jitter = min(30.0, 3.0 * TASK_INDEX + random.uniform(0, 5))
print("task_index", TASK_INDEX, "jitter_s", round(jitter, 2), flush=True)
time.sleep(jitter)

deadline = time.time() + TASK_BUDGET_S
session = requests.Session()
session.headers.update({"User-Agent": "rsacrack-batch/1.0"})

# quick health check (non-fatal)
try:
    session.get(f"{BASE_URL}/healthz", timeout=5)
except Exception as e:
    print("health_error", repr(e), flush=True)

def attempt_once(try_no: int) -> int:
    if time.time() + READ_TIMEOUT > deadline:
        print("stopping_before_timeout", flush=True)
        return 2
    url = f"{BASE_URL}/api/factor?n={TARGET_N}&budget_ms={BUDGET_MS}"
    print("url", url, "try", try_no, "idx", TASK_INDEX, flush=True)
    t0 = time.time()
    try:
        r = session.get(url, timeout=READ_TIMEOUT)
        print("HTTP", r.status_code, flush=True)
        # try to show body even on non-200 (useful for errors)
        try:
            print(json.dumps(r.json(), indent=2))
        except Exception:
            print("body", (r.text or "")[:500], flush=True)
        print("elapsed_s", round(time.time()-t0, 3), flush=True)
        return 0 if r.ok else 2
    except Exception as e:
        print("requests_error", f"try={try_no}", "err="+repr(e), flush=True)
        return 2

code = 2
for t in range(1, MAX_TRIES + 1):
    code = attempt_once(t)
    if code == 0:
        sys.exit(0)
    # small exponential backoff with jitter, but stay within task budget
    backoff = min(15.0, (2 ** t) + random.uniform(0, 2))
    if time.time() + backoff > deadline:
        print("stopping_before_timeout", flush=True)
        break
    time.sleep(backoff)

print("final_error", "gave up", flush=True)
sys.exit(2)
