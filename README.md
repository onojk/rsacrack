# RSAcrack

RSAcrack is a tiny Flask + Gunicorn service for exploring prime and semiprime detection and **quick factoring** using:

* Small **trial division** (cheap screen, up to ≈1e7)
* **Pollard’s Rho (Brent)** with a time budget
* Lightweight **geometric classification** helpers (for viz/demo)

This is a research/educational project — **not** a replacement for industrial-strength factorization or cryptanalysis.

---

## Quick start (local)

```bash
git clone https://github.com/onojk/rsacrack.git
cd rsacrack
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade -r requirements.txt
# Dev run
python app_demo.py --host 127.0.0.1 --port 8001 --debug
```

Hit:

```
http://127.0.0.1:8001/healthz
http://127.0.0.1:8001/api/version
```

---

## API

### `GET /healthz`

Simple health probe.

**200 OK** → `ok`

---

### `GET /api/version`

Service metadata.

**Example**

```bash
curl -sS https://rsacrack.com/api/version | jq .
```

**Response**

```json
{
  "name": "rsacrack",
  "version": "2025-08-23",
  "methods": ["trial", "rho"],
  "limits": { "digits_max": 200, "budget_ms": [500, 10000] }
}
```

---

### `GET /api/classify`

Classify an integer as `prime | semiprime | other` and (for semiprimes) include geometry/invariant signatures.

**Query params**

* `n` (required, integer or numeric string)
* `r0` (float, default 1.0)
* `alpha` (float, default 0.0125)
* `beta` (float, default 0.005)
* `L` (float, default 360)

**Examples**

```bash
curl -sS "https://rsacrack.com/api/classify?n=91" | jq .
curl -sS "https://rsacrack.com/api/classify?n=2147483647" | jq .
```

**Typical response (semiprime)**

```json
{
  "n": 91,
  "class": "semiprime",
  "primes": [7, 13],
  "normalized": {"f1": 0.8894, "f2": 0.0566, "f3": 0.0540},
  "balance": 0.6289,
  "bit_gap": 1,
  "per_step_slopes": {"s1": 0.0288, "s2": 0.0238, "s3": 0.0227},
  "sig_geom": "…",
  "sig_invariant": "…",
  "n_str": "91",
  "prime_status": "91 is NOT prime (semiprime)",
  "tested": true,
  "n_js_safe": true,
  "dots": 4,
  "suspected": "composite"
}
```

---

### `GET /api/factor`

Attempt to factor an integer quickly. The server:

1. runs **small trial division** (≤ \~1e7)
2. if needed, runs **Pollard Rho (Brent)** with a **time budget**
3. if not factored within budget, returns `"class": "other"`

**Query params**

* `n` (required, **decimal string**; `+` sign allowed; max **200 digits**)
* `budget_ms` (optional, default **2000**; min **500**, max **10000**)

**Examples**

```bash
# tiny semiprime → trial
curl -sS "https://rsacrack.com/api/factor?n=15" | jq .

# mixed (one small, one big) → still trial
curl -sS "https://rsacrack.com/api/factor?n=$((65537*2147483647))" | jq .

# both primes > 1e7 (needs rho); may require ~2-4s
curl -sS "https://rsacrack.com/api/factor?n=110000479000513&budget_ms=4000" | jq .
```

**Responses**

* Semiprime (trial):

```json
{
  "class": "semiprime",
  "n": 15,
  "factors": [3, 5],
  "method": "trial",
  "ms": 0.01
}
```

* Semiprime (rho):

```json
{
  "class": "semiprime",
  "n": 110000479000513,
  "factors": [10000019, 11000027],
  "method": "rho",
  "ms": 2930.0
}
```

* Prime:

```json
{ "class": "prime", "n": 2147483647, "ms": 0.12 }
```

* Not factored in time:

```json
{
  "class": "other",
  "n": 12345678910111213141516,
  "factors": [],
  "method": "trial+rho_timeout",
  "ms": 2000.0
}
```

**Errors**

* `400` — `{"error":"n must be a non-negative integer string"}`
* `413` — `{"error":"n too large (max 200 digits)"}`
* `429` — `{"error":"too many requests"}` (simple in-process rate limit)

---

## Limits & Notes

* `n` must be a **non-negative integer string** (no spaces/commas).
* Size cap: **200 digits** (\~665 bits) to protect memory/CPU.
* `budget_ms`: 500–10000 (ms). More time → better chance for hard composites.
* Rho is probabilistic; repeated tries may succeed where one fails.
* **Not** suitable for real-world RSA key recovery or adversarial use.

---

## Performance Tips

* “Easy” semiprimes (one small factor) are instant via trial.
* Harder \~10–14 digit semiprimes with two \~1e7 factors often succeed in <4 s.
* For much larger composites, expect `"other"` unless a small factor exists.

---

## Deployment (what this site uses)

### 1) System packages

```bash
sudo apt update
sudo apt install -y python3-venv nginx certbot python3-certbot-nginx jq
```

### 2) App setup

```bash
cd /home/<USER>/rsacrack
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
```

### 3) Gunicorn via systemd

Create `/etc/systemd/system/rsacrack.service`:

```ini
[Unit]
Description=RSAcrack Flask via Gunicorn
After=network.target

[Service]
User=<USER>
Group=www-data
WorkingDirectory=/home/<USER>/rsacrack
Environment="PATH=/home/<USER>/rsacrack/.venv/bin"
Environment="HOST=0.0.0.0" "PORT=8080"
ExecStart=/home/<USER>/rsacrack/.venv/bin/gunicorn \
  -w 2 -k gthread --threads 4 --timeout 120 \
  -b 0.0.0.0:8080 app_demo:app
Restart=on-failure
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now rsacrack
sudo systemctl status rsacrack --no-pager
```

### 4) Nginx reverse proxy + HTTPS

Site config `/etc/nginx/sites-available/rsacrack`:

```nginx
server {
    listen 80;
    server_name rsacrack.com www.rsacrack.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name rsacrack.com www.rsacrack.com;

    ssl_certificate /etc/letsencrypt/live/rsacrack.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/rsacrack.com/privkey.pem;

    # Security headers (also see conf.d/*.conf below)
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options SAMEORIGIN always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

    # Static UI (optional)
    location /web/ {
        alias /home/<USER>/rsacrack/web/;
        access_log off;
        expires 7d;
        add_header Cache-Control "public, max-age=604800" always;
        try_files $uri =404;
    }

    # App
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
    }
}
```

Enable & test:

```bash
sudo ln -sf /etc/nginx/sites-available/rsacrack /etc/nginx/sites-enabled/rsacrack
sudo nginx -t && sudo systemctl reload nginx
```

Optional HSTS (global): `/etc/nginx/conf.d/hsts.conf`

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
```

### 5) Let’s Encrypt

```bash
sudo certbot --nginx -d rsacrack.com -d www.rsacrack.com
# Reinstall existing cert if prompted, or renew & replace.
# Auto-renew is handled by systemd timers: `systemctl list-timers | grep certbot`
```

### 6) GCP firewall (if on GCE)

* Make sure instance has tags `http-server, https-server` (or your custom ones).
* Open ports 80/443 (or 8080 if you expose it directly).

```bash
# login as your user; follow browser flow
gcloud auth login --update-adc
gcloud config set project <PROJECT_ID>

# Built-ins (if present in your project)
gcloud compute instances add-tags <INSTANCE_NAME> \
  --zone=<ZONE> --tags=http-server,https-server

# Or custom rule for 8080
gcloud compute firewall-rules create allow-rsacrack-8080 \
  --allow=tcp:8080 --direction=INGRESS --priority=1000 \
  --network=default --target-tags=rsacrack --source-ranges=0.0.0.0/0
gcloud compute instances add-tags <INSTANCE_NAME> \
  --zone=<ZONE> --tags=rsacrack
```

---

## Operations

**Logs**

```bash
journalctl -u rsacrack -n 100 --no-pager
```

**Reload after code changes**

```bash
sudo systemctl restart rsacrack
sudo systemctl reload nginx
```

**Sanity**

```bash
curl -sS https://rsacrack.com/healthz
curl -sS https://rsacrack.com/api/version | jq .
```

---

## Repo hygiene

* `.gitignore` excludes: `__pycache__/`, `.venv/`, `*.bak.*`, `*.bad.*`, `cache/`, `*.csv`
* Backups land in `backups/` (optional).
* `requirements.txt` pinned via `pip freeze` (already generated on the server).

---

## Security considerations

* Input is **string-parsed** and validated; `n` limited to **200 digits**.
* Simple per-worker **token-bucket rate limit** in `/api/factor` (429 on burst).
* Nginx adds conservative **security headers**; enable **HSTS** in prod.
* This service is **not** designed for adversarial workloads.

---

## License & Acknowledgments

* See [LICENSE](LICENSE).
* Thanks to the community work on Miller–Rabin and Pollard’s Rho (Brent variant).

---

## Examples (copy-paste)

```bash
# Health & version
curl -sS https://rsacrack.com/healthz && echo
curl -sS https://rsacrack.com/api/version | jq .

# Classification
curl -sS "https://rsacrack.com/api/classify?n=91" | jq .

# Factoring
curl -sS "https://rsacrack.com/api/factor?n=15" | jq .
curl -sS "https://rsacrack.com/api/factor?n=110000479000513&budget_ms=4000" | jq .
```

---

Happy hacking 👋
