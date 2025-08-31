import os, time
from datetime import datetime
from flask import Blueprint, request, jsonify, Response
from redis import Redis
from rq import Queue
from rq.job import Job
from rq.exceptions import NoSuchJobError

rho_bp = Blueprint("rho_bp", __name__)

# Redis / RQ
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_conn = Redis.from_url(redis_url)
rho_q = Queue("rho", connection=redis_conn, default_timeout=60*60*12)  # 12h

# ------------------ helpers ------------------
def _age_secs(dt: datetime | None) -> float | None:
    if not dt:
        return None
    return max(0.0, time.time() - dt.timestamp())

def _job_dict(job: Job) -> dict:
    d = {
        "job_id": job.id,
        "status": job.get_status(),
        "meta": job.meta or {},
        "enqueued_at": job.enqueued_at.isoformat() if job.enqueued_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "ended_at": job.ended_at.isoformat() if job.ended_at else None,
        "age_sec": _age_secs(job.enqueued_at),
    }
    try:
        if job.is_finished:
            r = job.return_value() if hasattr(job, "return_value") else job.result
            d["result"] = str(r)[:512]
    except Exception:
        pass
    try:
        if job.is_failed:
            d["exc_info"] = (job.exc_info or "")[-1024:]
    except Exception:
        pass
    return d

def ip_can_start(ip: str) -> bool:
    """Allow only one active (queued or started) job per IP."""
    try:
        for jid in rho_q.started_job_registry.get_job_ids():
            j = Job.fetch(jid, connection=redis_conn)
            if (j.meta or {}).get("ip") == ip:
                return False
        for jid in rho_q.get_job_ids():
            j = Job.fetch(jid, connection=redis_conn)
            if (j.meta or {}).get("ip") == ip:
                return False
    except Exception:
        pass
    return True

# ------------------ API ------------------
@rho_bp.get("/api/health")
def health():
    ok, msg = True, "ok"
    try:
        redis_conn.ping()
    except Exception as e:
        ok, msg = False, f"redis error: {e.__class__.__name__}"
    return jsonify({"ok": ok, "msg": msg, "queue": {"name": rho_q.name, "size": rho_q.count}, "time": int(time.time())})

@rho_bp.get("/api/queue")
def queue_info():
    ids = rho_q.get_job_ids()
    head = ids[:10]
    def age(jid):
        try:
            j = Job.fetch(jid, connection=redis_conn)
            return _age_secs(j.enqueued_at)
        except Exception:
            return None
    return jsonify({"queue": rho_q.name, "size": len(ids), "head": [{"job_id": jid, "age_sec": age(jid)} for jid in head]})

@rho_bp.post("/api/rho/submit")
def rho_submit():
    data = request.get_json(silent=True) or {}
    nstr = str(data.get("N", "")).strip()
    budget = int(data.get("budget", 1_000_000))
    if not nstr.isdigit():
        return jsonify({"error": "Provide N as a positive integer string."}), 400
    N = int(nstr)
    bits = N.bit_length()
    if bits > 512:
        return jsonify({"error": "Max 512 bits for this demo."}), 400
    if budget > 50_000_000:
        return jsonify({"error": "Budget too large; cap is 50,000,000."}), 400

    xff = request.headers.get("X-Forwarded-For", "")
    ip = (xff.split(",")[0].strip() if xff else request.remote_addr)

    if not ip_can_start(ip):
        return jsonify({"error": "One active job per IP. Wait or cancel the running job."}), 429

    job = rho_q.enqueue("rho_worker.pollard_rho_job", N, budget,
                        meta={"bits": bits, "budget": budget, "ip": ip, "submitted": time.time()})
    ids = rho_q.get_job_ids()
    pos = ids.index(job.id) + 1 if job.id in ids else 1
    note = "Warning: \u2265 256-bit inputs can be very slow and may not finish." if bits >= 256 else ""
    return jsonify({"job_id": job.id, "status": job.get_status(), "bits": bits, "queue_position": pos, "note": note})

@rho_bp.get("/api/job/<job_id>")
def job_status(job_id):
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except NoSuchJobError:
        return jsonify({"error": "unknown job"}), 404
    return jsonify(_job_dict(job))

@rho_bp.post("/api/job/<job_id>/abort")
def job_abort(job_id):
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except NoSuchJobError:
        return jsonify({"error": "unknown job"}), 404
    try:
        if job.get_status() == "started":
            try:
                from rq.command import send_stop_job_command
                send_stop_job_command(redis_conn, job_id)
            except Exception:
                pass
        job.cancel()
    except Exception as e:
        return jsonify({"error": f"cancel failed: {e.__class__.__name__}"}), 400
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        pass
    return jsonify({"ok": True, "job_id": job_id, "status": getattr(job, "get_status", lambda: None)()})

# ------------------ UI assets ------------------
RHO_HTML = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>RSAcrack · Pollard Rho</title>
<link rel="stylesheet" href="/rho.css">
</head><body>
<main class="container">
  <h1>Pollard Rho (demo, up to 512-bit; ≥256-bit may be very slow)</h1>
  <div class="field">
    <label for="N">N (integer)</label>
    <textarea id="N" rows="4" placeholder="Enter integer N"></textarea>
  </div>
  <div class="field">
    <label for="budget">Budget (iterations)</label>
    <input id="budget" type="number" value="500000" min="1" max="50000000">
  </div>
  <button id="runBtn" type="button">RUN RHO</button>
  <pre id="status" class="status"></pre>
</main>
<script src="/rho.v2.js" defer></script>
</body></html>
"""

RHO_CSS = r""".container{max-width:900px;margin:2rem auto;padding:1rem;font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Helvetica,Arial,sans-serif;line-height:1.4}
h1{font-size:1.25rem;margin-bottom:1rem}
.field{margin:0.5rem 0}
label{display:block;font-weight:600;margin-bottom:0.25rem}
textarea,input{width:100%;box-sizing:border-box;padding:0.5rem}
button{margin-top:0.75rem;padding:0.6rem 1rem;border:0;border-radius:8px;background:#111;color:#fff;cursor:pointer}
.status{background:#f6f6f6;padding:0.5rem;height:12rem;overflow:auto;border-radius:6px}
"""

RHO_V2_JS = r"""(function(){
  function $(sel){ return document.querySelector(sel); }
  function out(msg){
    try{
      var el = $("#status"); if(!el) return;
      el.textContent += msg + "\n";
      el.scrollTop = el.scrollHeight;
    }catch(_){}
  }
  console.log("rho.v2.js loaded");
  window.addEventListener("error", function(e){ out("JS Error: " + e.message); });

  async function postJSON(url, data){
    const r = await fetch(url, { method:"POST", headers:{"content-type":"application/json"}, body: JSON.stringify(data) });
    if(!r.ok){
      let txt = ""; try{ txt = await r.text(); }catch(_){}
      throw new Error("HTTP " + r.status + (txt ? " - " + txt : ""));
    }
    return r.json();
  }
  const sleep = (ms)=>new Promise(r=>setTimeout(r,ms));
  async function poll(job_id){
    for(;;){
      const r = await fetch("/api/job/" + job_id);
      const j = await r.json();
      const age = (j && j.age_sec != null && typeof j.age_sec === "number") ? j.age_sec.toFixed(2) : j.age_sec;
      out("[" + j.status + "] age=" + age + "s");
      if (j.status === "finished"){ out("Result: " + (j.result || "")); break; }
      if (j.status === "failed" || j.status === "canceled"){ out("Stopped."); break; }
      await sleep(1000);
    }
  }
  window.addEventListener("DOMContentLoaded", function(){
    out("Ready.");
    const btn = $("#runBtn"), N = $("#N"), budget = $("#budget");
    if(!btn || !N){ out("UI not found."); return; }
    btn.addEventListener("click", async function(){
      btn.disabled = true; out("Submitting...");
      try{
        const nVal = (N.value || "").trim();
        const bVal = parseInt(budget && budget.value, 10) || 500000;
        const j = await postJSON("/api/rho/submit", {N: nVal, budget: bVal});
        out("Job " + j.job_id + " queued at position " + j.queue_position + " (bits=" + j.bits + ")");
        await poll(j.job_id);
      }catch(e){ out("Error: " + e); } finally { btn.disabled = false; }
    });
  });
})();"""

@rho_bp.get("/rho")
def rho_page():
    return Response(RHO_HTML, mimetype="text/html; charset=utf-8")

@rho_bp.get("/rho.css")
def rho_css():
    return Response(RHO_CSS, mimetype="text/css; charset=utf-8")

@rho_bp.get("/rho.v2.js")
def rho_js_v2():
    return Response(RHO_V2_JS, mimetype="text/javascript; charset=utf-8")

@rho_bp.get("/")
def home_redirect():
    return Response(RHO_HTML, mimetype="text/html; charset=utf-8")
