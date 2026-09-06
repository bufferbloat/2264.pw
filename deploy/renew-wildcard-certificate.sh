#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "Run as root." >&2
    exit 1
fi
: "${LE_EMAIL:?Set LE_EMAIL to the ACME contact address}"

credentials=/root/.secrets/certbot/cloudflare.ini
if [ ! -f "$credentials" ]; then
    echo "Create $credentials with: dns_cloudflare_api_token = TOKEN" >&2
    exit 1
fi
if [ "$(stat -c %u "$credentials")" != "0" ] || [ "$(stat -c %a "$credentials")" != "600" ]; then
    echo "$credentials must be root-owned and mode 600." >&2
    exit 1
fi

certbot certonly \
    --dns-cloudflare \
    --dns-cloudflare-credentials "$credentials" \
    --cert-name 2264.eu \
    --renew-with-new-domains \
    --non-interactive \
    --agree-tos \
    --email "$LE_EMAIL" \
    -d 2264.eu \
    -d '*.2264.eu' \
    --deploy-hook 'docker exec nginx nginx -t && docker exec nginx nginx -s reload'

systemctl enable --now certbot.timer
certbot renew --cert-name 2264.eu --dry-run --no-random-sleep-on-renew
