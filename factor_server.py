import os, sys; sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from flask import Flask, request, jsonify
from rsacrack.pipeline_smart import factor_smart
from rsacrack import is_probable_prime
import time

app = Flask(__name__)

@app.post("/factor")
def factor_endpoint():
    t0 = time.time()
    data = request.get_json(force=True) if request.is_json else request.form
    try:
        n = int((data.get("n") or "").strip())
    except Exception:
        d = jsonify({"status":"error","error":"invalid n"}); d.status_code=400; return d
    
    time_ms = int(data.get("time_ms", 3000))
    strategy = data.get("strategy", "smart")
    
    # Use the correct parameter name: max_ms
    res = factor_smart(n, max_ms=time_ms)
    
    if not res:
        d = jsonify({"status": "timeout", "n": str(n), "time_ms": time_ms, "strategy": strategy})
        d.headers["X-Compute-ms"] = str(int((time.time()-t0)*1000))
        return d
    
    # Handle both dict and object response formats
    if hasattr(res, 'p'):  # object format
        p_val = res.p
        q_val = res.q
        method_val = res.method
        steps_val = res.steps
    else:  # dict format
        p_val = res['p']
        q_val = res['q']
        method_val = res['method']
        steps_val = res['steps']
    
    d = jsonify({
        "status": "ok",
        "n": str(n),
        "p": str(p_val),
        "q": str(q_val),
        "method": method_val,
        "steps": steps_val,
        "is_p_prime": is_probable_prime(p_val),
        "is_q_prime": is_probable_prime(q_val),
        "strategy": strategy
    })
    d.headers["X-Compute-ms"] = str(int((time.time()-t0)*1000))
    return d
