from rho_api import rho_bp
import os, sys
from flask import Flask, request, jsonify, render_template_string, send_from_directory

# Prefer system-wide /opt/factor-core; fall back to ./vendor
try:
    from factor_core import quick_factor, classify, run_ecm, ecm_available, pollard_rho
except Exception:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "vendor"))
    from factor_core import quick_factor, classify, run_ecm, ecm_available, pollard_rho

STATIC_DIR = os.path.join(os.path.dirname(__file__), "web", "public")
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")
app.register_blueprint(rho_bp)

PAGE = """<!doctype html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>RSACrack</title><link rel="icon" href="/favicon.ico">
<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,Noto Sans,Helvetica,Arial,sans-serif;margin:0;background:#fafafa;color:#111}
.wrap{max-width:860px;margin:40px auto;padding:0 16px}
h1{font-weight:700}.card{background:#fff;border:1px solid #eee;border-radius:12px;padding:16px 16px;margin:18px 0;box-shadow:0 1px 2px rgba(0,0,0,.03)}
label{font-size:12px;color:#555}input,button{font-size:14px;padding:10px;border-radius:8px;border:1px solid #d0d0d0}
input{width:100%;box-sizing:border-box}button{background:#111;color:#fff;cursor:pointer}button:hover{opacity:.92}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.mono{font-family:ui-monospace,Menlo,Consolas,monospace}
pre{white-space:pre-wrap;word-break:break-all;background:#f6f6f6;border:1px solid #eee;border-radius:8px;padding:10px}
.note{color:#555;font-size:12px}.small{font-size:12px}footer{color:#777;font-size:12px;margin:30px 0}
</style></head><body><div class="wrap">
<h1>RSACrack</h1>
<div class="small">Interactive factoring tools (RSA-oriented). Matched to ECC-Tools layout.</div>

<div class="card">
  <h3>Quick factor</h3>
  <div class="grid">
    <div><label>N (integer)</label><input id="q_n" class="mono" placeholder="enter integer"/></div>
    <div style="display:flex;align-items:flex-end"><button id="q_go">Factor</button></div>
  </div>
  <div class="note">trial → Fermat (close) → p-1 → Rho → tiny ECM taste.</div>
  <pre id="q_out">–</pre>
</div>

<div class="card">
  <h3>ECM (tunable)</h3>
  <div class="grid">
    <div><label>N (integer)</label><input id="e_n" class="mono"/></div>
    <div><label>B1</label><input id="e_b1" value="100000"/></div>
    <div><label>B2 (optional)</label><input id="e_b2"/></div>
    <div><label>Curves (c)</label><input id="e_c" value="5"/></div>
    <div><label>Threads</label><input id="e_t" value="1"/></div>
    <div><label>Timeout (s)</label><input id="e_to" value="30"/></div>
  </div>
  <div style="margin-top:8px"><button id="e_go">Run ECM</button></div>
  <div class="note">{{ECM_STATE}}</div>
  <pre id="e_out">–</pre>
</div>

<div class="card">
  <h3>Rho (fast demo, up to 512-bit; ≥256-bit may be very slow)</h3>
  <div class="grid">
    <div><label>N (≤128-bit integer)</label><input id="r_n" class="mono"/></div>
    <div><label>Iterations (budget)</label><input id="r_it" value="1000000"/></div>
  </div>
  <div style="margin-top:8px"><button id="r_go">Run rho</button></div>
  <pre id="r_out">–</pre>
</div>

<footer>© RSACrack • Flask + Gunicorn</footer>
</div>
<script>
async function post(url,p){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});return await r.json();}
document.querySelector('#q_go').onclick=async()=>{const n=(document.querySelector('#q_n').value||'').trim();const out=document.querySelector('#q_out');out.textContent='Thinking…';try{const res=await post('/api/quick_factor',{n});out.textContent=res.pretty||JSON.stringify(res,null,2);}catch(e){out.textContent='Error: '+e;}};
document.querySelector('#e_go').onclick=async()=>{const n=(document.querySelector('#e_n').value||'').trim();const b1=parseInt(document.querySelector('#e_b1').value||'0',10);const b2v=(document.querySelector('#e_b2').value||'').trim();const b2=b2v?parseInt(b2v,10):null;const c=parseInt(document.querySelector('#e_c').value||'0',10);const t=parseInt(document.querySelector('#e_t').value||'1',10);const to=parseInt(document.querySelector('#e_to').value||'30',10);const out=document.querySelector('#e_out');out.textContent='Running ECM…';try{const res=await post('/api/ecm',{n,B1:b1,B2:b2,curves:c,threads:t,timeout:to});out.textContent=res.pretty||JSON.stringify(res,null,2);}catch(e){out.textContent='Error: '+e;}};
document.querySelector('#r_go').onclick=async()=>{const n=(document.querySelector('#r_n').value||'').trim();const it=parseInt(document.querySelector('#r_it').value||'1000000',10);const out=document.querySelector('#r_out');out.textContent='Running rho…';try{const res=await post('/api/rho',{n,it});out.textContent=res.pretty||JSON.stringify(res,null,2);}catch(e){out.textContent='Error: '+e;}};
</script></body></html>"""

@app.get("/")
def home():
    ecm_state = "ECM available ✓" if ecm_available() else "ECM not installed on this host"
    return render_template_string(PAGE.replace("{{ECM_STATE}}", ecm_state))

@app.post("/api/quick_factor")
def api_quick():
    data = request.get_json(force=True, silent=True) or {}
    try:
        n = int(str(data.get("n","")).strip())
    except:
        return jsonify(error="invalid integer"), 400
    d, how = quick_factor(n, budget_s=3.0)
    if d:
        q = n//d
        return jsonify(n_bits=n.bit_length(), method=how, factor=int(d), cofactor=int(q),
                       pretty=f"{n} = {d} × {q}  (method: {how})")
    info = classify(n, attempt_s=0.2)
    return jsonify(n_bits=n.bit_length(), method="quick", factor=None,
                   pretty=f"No factor found quickly. status={info['status']} bits={info['bits']}")

@app.post("/api/ecm")
def api_ecm():
    data = request.get_json(force=True, silent=True) or {}
    try:
        n = int(str(data.get("n","")).strip())
        B1 = int(data.get("B1", 100000))
        B2 = int(data["B2"]) if (data.get("B2") not in (None,"")) else None
        curves = int(data.get("curves",5))
        threads = int(data.get("threads",1))
        timeout = int(data.get("timeout",30))
    except:
        return jsonify(error="bad params"), 400
    f, log = run_ecm(n, B1=B1, B2=B2, curves=curves, threads=threads, timeout=timeout)
    if f:
        co = n//f
        return jsonify(factor=int(f), cofactor=int(co), n_bits=n.bit_length(),
                       pretty=f"{n} = {f} × {co}  (ECM)")
    return jsonify(factor=None, n_bits=n.bit_length(), pretty="No factor found by ECM.", log=(log or "")[-4000:])

@app.post("/api/rho")
def api_rho():
    data = request.get_json(force=True, silent=True) or {}
    try:
        n = int(str(data.get("n","")).strip())
        it = int(data.get("it", 1_000_000))
    except:
        return jsonify(error="bad params"), 400
    if n.bit_length() > 128:
        return jsonify(error="Please keep N ≤ 128 bits for this demo."), 400
    d = pollard_rho(n, iters=max(1,it))
    if d:
        co = n//d
        return jsonify(factor=int(d), cofactor=int(co), pretty=f"{n} = {d} × {co}  (Pollard Rho)")
    return jsonify(factor=None, pretty="No factor found within iteration budget.")

@app.get("/api/health")
def api_health():
    return jsonify(ok=True, ecm=ecm_available())

@app.get("/robots.txt")
def robots():
    return send_from_directory(STATIC_DIR, "robots.txt")

@app.get("/favicon.ico")
def favicon():
    return send_from_directory(STATIC_DIR, "favicon.ico")

if __name__ == "__main__":
    app.run("127.0.0.1", 8082, debug=True)
