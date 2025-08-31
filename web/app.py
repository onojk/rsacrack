import time
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.exceptions import BadRequest
from lotto_factor import factor_lotto_64

app = Flask(__name__, static_folder="static")

@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

def _factor_core(n: int, budget_ms: int|None):
    t0 = time.perf_counter()
    res = factor_lotto_64(n, budget_ms=budget_ms)
    dt_ms = int((time.perf_counter() - t0) * 1000)
    if res is None:
        return {"ok": True, "n": str(n), "duration_ms": dt_ms, "result": "none"}
    p, q = res
    if q == 1:
        return {"ok": True, "n": str(n), "duration_ms": dt_ms, "result": "prime", "p": str(p)}
    else:
        return {"ok": True, "n": str(n), "duration_ms": dt_ms, "result": "factors", "p": str(p), "q": str(q)}

# Original POST JSON endpoint (kept)
@app.post("/api/lotto_factor")
def api_lotto_factor():
    try:
        data = request.get_json(force=True, silent=False)
        n = int(data.get("n"))
        budget_ms = data.get("budget_ms")
        if budget_ms is not None:
            budget_ms = int(budget_ms)
    except Exception as e:
        raise BadRequest(f"Invalid payload: {e}")
    if n < 0 or n > 0xFFFFFFFFFFFFFFFF:
        raise BadRequest("n must be a 64-bit unsigned integer (0..2^64-1)")
    return jsonify(_factor_core(n, budget_ms))

# New GET endpoint for your UI (query params)
# /api/factor?n=221&timeout_ms=200&max_bits=4096
@app.get("/api/factor")
def api_factor_query():
    n_str = request.args.get("n", "").strip()
    t_str = request.args.get("timeout_ms", "").strip()
    if not n_str:
        raise BadRequest("missing n")
    try:
        n = int(n_str)
    except:
        raise BadRequest("n must be integer")
    budget_ms = None
    if t_str and t_str != "0":
        try:
            budget_ms = int(t_str)
        except:
            raise BadRequest("timeout_ms must be integer")
    if n < 0 or n > 0xFFFFFFFFFFFFFFFF:
        raise BadRequest("n must be a 64-bit unsigned integer (0..2^64-1)")
    return jsonify(_factor_core(n, budget_ms))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

# --- Lotto-128 proxy to Node API ---
from flask import request, Response, jsonify
import requests as _rq

@app.route('/api/lotto128_factor', methods=['POST'])
def lotto128_factor_proxy():
    try:
        resp = _rq.post(
            'http://127.0.0.1:3000/api/lotto128_factor',
            data=request.get_data(),
            headers={'Content-Type': 'application/json'},
            timeout=120
        )
        return Response(resp.content, resp.status_code, headers={
            'Content-Type': resp.headers.get('Content-Type','application/json')
        })
    except Exception as e:
        return jsonify(ok=False, error=f'proxy error: {e}'), 500

# --- Generic API proxy to Node (:3000) ---
from flask import request, Response, jsonify
import requests as _rq

@app.route('/api/<path:path>', methods=['GET','POST','PUT','DELETE','PATCH','OPTIONS'])
def api_proxy(path):
    try:
        url = f'http://127.0.0.1:3000/api/{path}'
        resp = _rq.request(
            method=request.method,
            url=url,
            params=request.args,
            data=request.get_data(),
            headers={k:v for k,v in request.headers.items()
                     if k.lower() in ('content-type','accept','authorization')},
            timeout=300
        )
        # filter hop-by-hop headers
        drop = {'content-encoding','transfer-encoding','connection'}
        hdrs = [(k,v) for k,v in resp.headers.items() if k.lower() not in drop]
        return Response(resp.content, resp.status_code, headers=hdrs)
    except Exception as e:
        return jsonify(ok=False, error=f'proxy error: {e}'), 502
