#!/bin/sh
set -e

POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres}"

HASH=$(echo -n "${POSTGRES_PASSWORD}${POSTGRES_USER:-postgres}" | md5sum | cut -d' ' -f1)
echo "\"${POSTGRES_USER:-postgres}\" \"md5${HASH}\"" > /etc/pgbouncer/userlist.txt

exec "$@"
