import os, sys; sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from flask import Flask, request, jsonify
from rsacrack import factor_one, is_probable_prime
import time

app = Flask(__name__)

@app.post("/factor")
def factor_endpoint():
    t0 = time.time()
    data = request.get_json(force=True) if request.is_json else request.form
    n = int(data.get("n"))
    time_ms = int(data.get("time_ms", 3000))
    res = factor_one(n, time_ms=time_ms)
    if not res:
        d = jsonify({"status": "timeout", "n": str(n), "time_ms": time_ms})
        d.headers["X-Compute-ms"] = str(int((time.time()-t0)*1000))
        return d
    d = jsonify({
        "status": "ok",
        "n": str(n),
        "p": str(res.p),
        "q": str(res.q),
        "method": res.method,
        "steps": res.steps,
        "is_p_prime": is_probable_prime(res.p),
        "is_q_prime": is_probable_prime(res.q),
    })
    d.headers["X-Compute-ms"] = str(int((time.time()-t0)*1000))
    return d
