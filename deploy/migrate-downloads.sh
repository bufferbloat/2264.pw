#!/usr/bin/env bash
set -eu

repository=${1:-$(pwd)}
cd "$repository"
source_root=$(realpath html/src)
managed_root=$(realpath managed/public)

if [ "$source_root" = "$managed_root" ]; then
    echo "Source and destination unexpectedly match." >&2
    exit 1
fi

if [ -f managed/public/.gitkeep ]; then
    if [ "$(stat -c %i managed/public/.gitkeep)" != "$(stat -c %i html/src/.gitkeep)" ]; then
        unlink managed/public/.gitkeep
    fi
fi

# Hard links retain the rollback tree and consume no second copy of the 3.3 GB payload.
# Subsequent atomic replacements in managed/public do not modify the rollback link.
cp -al --update=none "$source_root"/. "$managed_root"/
find managed/public -type d -exec chown 2264:2264 {} +

source_count=$(find html/src -type f | wc -l)
managed_count=$(find managed/public -type f | wc -l)
if [ "$source_count" -ne "$managed_count" ]; then
    echo "File-count mismatch ($source_count source, $managed_count managed)." >&2
    exit 1
fi

find html/src -type f -print0 | while IFS= read -r -d '' source; do
    relative=${source#html/src/}
    destination=managed/public/$relative
    if [ ! -f "$destination" ] || [ "$(stat -c %i "$source")" != "$(stat -c %i "$destination")" ]; then
        echo "Hard-link verification failed: $relative" >&2
        exit 1
    fi
done

echo "Managed download tree contains $managed_count verified hard-linked files."
