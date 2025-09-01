from __future__ import annotations
import shutil, subprocess, re, time
from dataclasses import dataclass

ECM_BIN = shutil.which("ecm")
_FACT_RE = re.compile(r"(?:(?:Found input number has a factor:)|(?:Factor found.*?:))\s*([0-9]{2,})")

@dataclass
class FactorHit:
    method: str
    p: int
    detail: str
    elapsed_ms: int

def _run(cmd:list[str], timeout:float)->tuple[int,str,str,int]:
    t0=time.time()
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       text=True, timeout=timeout)
    ms = int((time.time()-t0)*1000)
    return p.returncode, p.stdout, p.stderr, ms

def _pick_factor(n:int, text:str)->int|None:
    for m in _FACT_RE.finditer(text):
        try:
            f = int(m.group(1))
            if 1 < f < n and n % f == 0:
                return f
        except Exception:
            pass
    return None

def _ecm_available() -> bool:
    return bool(ECM_BIN)

def ecm_try(n:int, B1:int, B2:int|None=None, curves:int=1, timeout_s:float=30.0)->FactorHit|None:
    if not _ecm_available():
        return None
    args = [ECM_BIN, "-c", str(curves)]
    if B2: args += [str(B1), str(B2)]
    else:  args += [str(B1)]
    args += [str(n)]
    rc, out, err, ms = _run(args, timeout_s)
    f = _pick_factor(n, out + "\n" + err)
    return FactorHit("ecm", f, f"ECM B1={B1} B2={B2} c={curves}", ms) if f else None

def pm1_try(n:int, B1:int, B2:int|None=None, timeout_s:float=10.0)->FactorHit|None:
    if not _ecm_available():
        return None
    args = [ECM_BIN, "-pm1"]
    if B2: args += [str(B1), str(B2)]
    else:  args += [str(B1)]
    args += [str(n)]
    rc, out, err, ms = _run(args, timeout_s)
    f = _pick_factor(n, out + "\n" + err)
    return FactorHit("p-1", f, f"P-1 B1={B1} B2={B2}", ms) if f else None

def pp1_try(n:int, B1:int, B2:int|None=None, timeout_s:float=10.0)->FactorHit|None:
    if not _ecm_available():
        return None
    args = [ECM_BIN, "-pp1"]
    if B2: args += [str(B1), str(B2)]
    else:  args += [str(B1)]
    args += [str(n)]
    rc, out, err, ms = _run(args, timeout_s)
    f = _pick_factor(n, out + "\n" + err)
    return FactorHit("p+1", f, f"P+1 B1={B1} B2={B2}", ms) if f else None
