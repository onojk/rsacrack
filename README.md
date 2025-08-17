# RSAcrack

**RSAcrack** explores a geometric/visual model for integers using a 3D **conical coil** and simple numerical fingerprints to quickly classify numbers (prime / semiprime / other) and surface helpful diagnostics.

- Live site: **https://rsacrack.com**
- API root: **`/api/classify?n=...`**

---

## 📖 Overview

We place the natural numbers along a 3D **conical spring (coil)**. At primes the “prime-only coil” and the “all-integers coil” are tangent. This intuition motivates quick fingerprints:

- **Classify:** `prime`, `semiprime`, or `other` (unknown/not tested)
- **Dots ≈ τ(n):** number of divisors (the “flattened coil tangencies” idea)
- **Semiprime extras:** factor pair, normalized footprint features, and simple signatures

> We do **not** claim cryptographic breakthroughs here; this is an experiment in visualization + heuristics with clear limits.

---

## 🚀 Features

- ⚙️ **REST API**: `/api/classify` and `/api/factor`
- 🖥 **Web UI**: interactive canvas + **Results** panel (shows class, dots, status, factors if semiprime)
- 🧠 **Why this works**: inline explanation panel tied to each result
- 🔎 **Semiprime footprint** (for small/medium `n`) with normalized features & signatures
- 🧪 **Test gallery** (below) with known values across types

---

## 🕹 Quick Start (local dev)

```bash
git clone https://github.com/onojk/rsacrack.git
cd rsacrack

# (optional) venv
python3 -m venv rsacrack-venv
source rsacrack-venv/bin/activate

pip install -r requirements.txt

# Run dev server (defaults HOST=127.0.0.1 PORT=8001)
python app_demo.py --debug
# open http://127.0.0.1:8001

Systemd / Gunicorn (prod)

A helper script is included:

# from repo root
chmod +x manage_rsacrack.sh

# Restart service cleanly and verify
./manage_rsacrack.sh

# Status only
./manage_rsacrack.sh --status

# Dev run on another port (stops service first)
./manage_rsacrack.sh --dev 5000

Health checks:

curl -sS http://127.0.0.1:8001/healthz && echo
curl -sS https://rsacrack.com/healthz && echo

🌐 Web UI

Open https://rsacrack.com.
Controls:

    n – number to classify

    Coil render params: r0, alpha, beta, L (optional)

    Classify + Render button runs /api/classify and updates:

        Badge with prime/semiprime/unknown (color hints)

        Results JSON (pretty)

        Why this works panel (expanded by default)
        Includes: n_str, tested class, divisor dots (τ(n)), suspected class from dots, and JS-safety.

    Tip: hard refresh to bust cache if you edit the UI: Ctrl+Shift+R (Cmd+Shift+R on macOS).

🧭 API
GET /api/classify?n=... (plus optional r0, alpha, beta, L)

Response (fields may vary by class):

{
  "n": 91,
  "n_str": "91",
  "n_js_safe": true,           // true if |n| <= 2^53-1 and digits-only
  "class": "semiprime",        // "prime" | "semiprime" | "other"
  "prime_status": "91 is NOT prime (semiprime)",
  "tested": true,              // true for prime/semiprime/composite; false if unknown
  "dots": 4,                   // τ(n), computed exactly up to 1e12; null above
  "suspected": "composite",    // from τ(n): 1=special, 2=prime, >2=composite
  "primes": [7, 13],           // present for semiprime
  "normalized": {...},         // semiprime footprint features (if available)
  "balance": 0.62,
  "bit_gap": 1,
  "sig_geom": "...",           // optional geometry-aware signature
  "sig_invariant": "..."       // optional invariant signature
}

GET /api/factor?n=... (small trial)

    Quickly detects prime or semiprime by tiny trial division; returns "other" if inconclusive.

🧪 Test Gallery

Try these known values in the UI or with curl:
n	Type	τ(n) (dots)	Notes / Factors
1	Special	1	unique, not prime
2	Prime	2	smallest prime
3	Prime	2	prime
4	Composite	3	2×2 (square)
6	Semiprime	4	2×3
15	Semiprime	4	3×5
91	Semiprime	4	7×13 (good demo)
899	Semiprime	4	29×31
104729	Prime	2	10000th prime
2310	Composite	32	2×3×5×7×11
360360	Composite	192	2×3×5×7×11×13 (very rich)
10403	Semiprime	4	101×103
19879	Prime	2	larger prime
999983	Prime	2	largest 6-digit prime
1000003	Prime	2	~1e6 range prime
10^40	Other	—	τ(n) not computed above 1e12; UI shows unknown
10000000000000000000000000000000000000061	Other	—	large; unknown

Examples:

# semiprime
curl -sS "https://rsacrack.com/api/classify?n=91" | jq

# prime
curl -sS "https://rsacrack.com/api/classify?n=104729" | jq

# highly composite
curl -sS "https://rsacrack.com/api/classify?n=360360" | jq

🧩 Why this works (intuition)

    Define dots = τ(n), the number of positive divisors of n.

    In the “flattened coil” picture, each divisor corresponds to a “tangent hit.” Counting hits ≈ counting divisors.

Consequences

    τ(1) = 1 → special (only 1 divides 1)

    τ(n) = 2 → prime (divisors are {1, n})

    τ(n) = 4 → typical semiprime (divisors {1, p, q, pq})

    τ(n) > 2 → composite

Limits

    We compute τ(n) exactly up to 10¹². Above that we report unknown for dots and avoid misleading float output by returning n_str and n_js_safe.

🧱 Project Layout

rsacrack/
├─ app_demo.py            # Flask app (web + API)
├─ manage_rsacrack.sh     # restart/status/dev helpers for systemd+gunicorn
├─ web/
│  └─ index.html          # UI (canvas + results + “Why this works”)
├─ coil_classifier.py     # classification and footprint helpers
├─ whitepaper/rsacrack_whitepaper.pdf
└─ requirements.txt

🔒 Ethics & Scope

    Educational and experimental.

    Only small/medium toy examples; not intended for real cryptographic key recovery.

    Please use responsibly and legally.

🤝 Contributing

Issues and PRs welcome! Ideas:

    Better large-n heuristics for τ(n)

    Alternative coil parametrizations

    Stronger semiprime footprint features

    UI polish & accessibility
