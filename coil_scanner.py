#!/usr/bin/env python3
import csv, sys, os, argparse, io, gzip, gc
from bisect import bisect_left
from collections import Counter
from tangent_prime_test import (
    factor, is_probable_prime,
    tangent_equal_split_info, tangent_prime_test_split_info,
)

WHEEL = tuple(sorted(r for r in range(210) if all(r % p for p in (2,3,5,7))))
OFFSETS, _prev = [], 0
for _r in WHEEL:
    OFFSETS.append(_r - _prev); _prev = _r
OFFSETS.append(210 - _prev)

def classify_and_count(n: int):
    if is_probable_prime(n): return "prime", Counter({n:1})
    fs = factor(n); fs.sort(); cnt = Counter(fs)
    if len(fs)==2 and len(cnt)<=2: return "semiprime", cnt
    return "composite", cnt

def factor_str(cnt: Counter):
    if not cnt: return ""
    return "*".join([f"{p}" if m==1 else f"{p}^{m}" for p,m in sorted(cnt.items())])

def next_wheel_candidate(n: int) -> int:
    r = n % 210
    i = bisect_left(WHEEL, r)
    if i < len(WHEEL) and WHEEL[i] == r: return n
    delta = (WHEEL[i] - r) if i < len(WHEEL) else (210 - r + WHEEL[0])
    return n + delta

def want_diagnostics(kind, cnt, samples, mode, period):
    if mode == "full": return True
    if mode == "thin": return False
    if period > 0 and samples % period == 0: return True
    spf = min(cnt) if cnt else None
    if kind == "semiprime": return True
    if spf and spf > 10_000: return True
    if sum(cnt.values()) >= 5: return True
    return False

def write_row(w, n, kind, cnt, want_diag: bool):
    row = {
        "n": n,
        "classification": kind,
        "omega_total": sum(cnt.values()),
        "omega_distinct": len(cnt),
        "smallest_prime_factor": min(cnt) if cnt else n,
        "largest_prime_factor": max(cnt) if cnt else n,
        "factorization": factor_str(cnt),
    }
    if want_diag:
        eq = tangent_equal_split_info(n)
        pt = tangent_prime_test_split_info(n)
        roots = pt.get("roots", (None, None))
        r1, r2 = (roots + (None, None))[:2] if isinstance(roots, tuple) else (None, None)
        row.update({
            "equal_L": str(eq.get("L","")),
            "equal_half": str(eq.get("half","")),
            "equal_product": str(eq.get("product","")),
            "equal_remainder": str(eq.get("remainder","")),
            "ptest_L": pt.get("L",""),
            "ptest_discriminant": pt.get("discriminant",""),
            "ptest_sqrt_disc_exact": bool(pt.get("sqrt_disc_exact", False)),
            "ptest_root1": r1,
            "ptest_root2": r2,
        })
    w.writerow(row)

def _open_maybe_gzip_for_read(path):
    if path.endswith(".gz"):
        return io.TextIOWrapper(gzip.GzipFile(filename=path, mode="rb"), encoding="utf-8", newline="")
    try:
        with open(path, "rb") as fh:
            if fh.read(2) == b"\x1f\x8b":
                return io.TextIOWrapper(gzip.GzipFile(filename=path, mode="rb"), encoding="utf-8", newline="")
    except Exception:
        pass
    return open(path, "r", encoding="utf-8", newline="")

def find_resume_point(path):
    if not os.path.exists(path) or os.path.getsize(path)==0: return None
    last = None
    try:
        with _open_maybe_gzip_for_read(path) as fh:
            for row in csv.DictReader(fh): last = row
    except Exception: return None
    if not last: return None
    try: return int(last.get("n",""))
    except Exception: return None

def _open_for_write(path, append: bool):
    if path.endswith(".gz"):
        rawfh = open(path, "ab" if append else "wb")
        return io.TextIOWrapper(gzip.GzipFile(fileobj=rawfh, mode="ab" if append else "wb"),
                                encoding="utf-8", newline="")
    return open(path, "a" if append else "w", newline="", encoding="utf-8")

def adaptive_coil(start, stop, out_path, batch=200, max_jump_blocks=512,
                  resume=True, progress_every=1_000_000,
                  mode="thin", diag_period=1000):
    fields = [
        "n","classification","omega_total","omega_distinct",
        "smallest_prime_factor","largest_prime_factor","factorization",
        "equal_L","equal_half","equal_product","equal_remainder",
        "ptest_L","ptest_discriminant","ptest_sqrt_disc_exact",
        "ptest_root1","ptest_root2",
    ]
    if start > stop:
        print("Nothing to do.", file=sys.stderr); return
    append = False
    if resume:
        last_n = find_resume_point(out_path)
        if last_n is not None:
            start = max(start, last_n+1); append = True
            if start > stop:
                print("Nothing to do.", file=sys.stderr); return
    fh = _open_for_write(out_path, append)
    with fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        if not append: w.writeheader()
        n = next_wheel_candidate(start)
        samples = 0; jump_blocks = 1; easy_streak = 0; MEM_CYCLE = 20000
        while n <= stop:
            for off in OFFSETS:
                if n > stop: break
                try:
                    kind, cnt = classify_and_count(n)
                    write_row(w, n, kind, cnt, want_diagnostics(kind, cnt, samples, mode, diag_period))
                except KeyboardInterrupt:
                    print("\nInterrupted — partial results saved to", out_path, file=sys.stderr); return
                except Exception as e:
                    print(f"[warn] n={n} failed: {e}", file=sys.stderr)
                samples += 1
                spf = min(cnt) if cnt else n
                if kind == "prime" or spf <= 1000:
                    easy_streak += 1
                    if easy_streak % batch == 0 and jump_blocks < max_jump_blocks:
                        jump_blocks *= 2
                        print(f"[progress] n={n} speed↑ jump_blocks={jump_blocks}", file=sys.stderr)
                else:
                    easy_streak = 0
                    if jump_blocks > 1:
                        jump_blocks //= 2
                        print(f"[progress] n={n} speed↓ jump_blocks={jump_blocks}", file=sys.stderr)
                if samples % MEM_CYCLE == 0: gc.collect()
                if samples % progress_every == 0:
                    print(f"[progress] n={n}", file=sys.stderr); fh.flush()
                n += off
            if jump_blocks > 1: n += 210 * (jump_blocks - 1)
            if n <= stop: n = next_wheel_candidate(n)
    print(f"Done. Wrote {out_path}")
    print("Tip: use --mode sampled to keep diagnostics sparse and RAM flat.")

def shard_loop(start, stop, shard_size, out_template, **kwargs):
    if start > stop:
        print("Nothing to do.", file=sys.stderr); return
    if shard_size <= 0:
        out_path = out_template.format(lo=start, hi=stop, idx=0)
        adaptive_coil(start, stop, out_path, **kwargs); return
    idx, n = 0, start
    while n <= stop:
        lo, hi = n, min(stop, n+shard_size-1)
        out_path = out_template.format(lo=lo, hi=hi, idx=idx)
        adaptive_coil(lo, hi, out_path, **kwargs)
        idx += 1; n = hi+1

def main():
    ap = argparse.ArgumentParser(description="Wheel-accelerated adaptive coil scanner.")
    ap.add_argument("--start", type=int, default=2)
    ap.add_argument("--stop",  type=int, required=True)
    ap.add_argument("--out",   type=str, default="coil.csv")
    ap.add_argument("--shard-size", type=int, default=0)
    ap.add_argument("--out-template", type=str,
        default="coil.n{lo:06d}-{hi:06d}.csv.gz",
        help="Used when --shard-size>0; supports {lo},{hi},{idx}. Add .gz to gzip.")
    ap.add_argument("--batch", type=int, default=200)
    ap.add_argument("--max-jump-blocks", type=int, default=512)
    ap.add_argument("--mode", choices=["thin","full","sampled"], default="thin")
    ap.add_argument("--diag-period", type=int, default=1000)
    ap.add_argument("--progress-every", type=int, default=1_000_000)
    ap.add_argument("--no-resume", action="store_true")
    args = ap.parse_args()
    if args.shard_size > 0:
        shard_loop(args.start, args.stop, args.shard_size, args.out_template,
                   batch=args.batch, max_jump_blocks=args.max_jump_blocks,
                   resume=not args.no_resume, mode=args.mode,
                   diag_period=args.diag_period, progress_every=args.progress_every)
    else:
        adaptive_coil(args.start, args.stop, args.out,
                      batch=args.batch, max_jump_blocks=args.max_jump_blocks,
                      resume=not args.no_resume, mode=args.mode,
                      diag_period=args.diag_period, progress_every=args.progress_every)

if __name__ == "__main__":
    main()
