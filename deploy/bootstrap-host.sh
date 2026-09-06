#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "Run as root so storage ownership and secret permissions are deterministic." >&2
    exit 1
fi

repository=${1:-$(pwd)}
cd "$repository"

if [ ! -f .env.admin ]; then
    django_secret=$(openssl rand -hex 64)
    fernet_key=$(openssl rand -base64 32 | tr '/+' '_-' | tr -d '\n')
    stats_token=$(openssl rand -hex 32)
    sed \
        -e "s/CHANGE_ME_RANDOM_64_BYTES/$django_secret/" \
        -e "s/CHANGE_ME_FERNET_KEY/$fernet_key/" \
        -e "s/CHANGE_ME_RANDOM_32_BYTES/$stats_token/" \
        .env.admin.example > .env.admin
    chmod 600 .env.admin
    echo "Created .env.admin. Fill CF_ACCESS_TEAM_DOMAIN and CF_ACCESS_AUD before starting."
fi

install -d -m 0750 secrets
if [ ! -f secrets/restic-password ]; then
    openssl rand -hex 32 > secrets/restic-password
fi
chown -R 2264:2264 content generated media backups managed/staging managed/trash
# Existing download payloads remain root-owned even though their managed parent
# directories are writable for atomic rename. This prevents in-place mutation of
# hard-linked rollback bytes from the admin container.
find managed/public -type d -exec chown 2264:2264 {} +
chown 2264:2264 secrets/restic-password
chown root:2264 secrets
chmod 0750 secrets
chmod 600 secrets/restic-password

echo "Host storage initialized. Next: deploy/migrate-downloads.sh and edit .env.admin."
