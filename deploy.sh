#!/usr/bin/env bash
set -euo pipefail
git -C /home/onojk123/rsacrack pull --ff-only
sudo -n /usr/bin/systemctl restart rsacrack-gunicorn || sudo -n /bin/systemctl restart rsacrack-gunicorn
sudo -n /usr/bin/systemctl restart rsacrack-rq       || sudo -n /bin/systemctl restart rsacrack-rq
journalctl -u rsacrack-gunicorn -n 20 --no-pager || true
journalctl -u rsacrack-rq       -n 20 --no-pager || true
