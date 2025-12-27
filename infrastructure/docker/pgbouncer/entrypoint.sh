#!/bin/sh
set -e

# Create userlist.txt from environment variables
# Format: "username" "password_hash"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres}"

# Generate MD5 hash for pgbouncer
# Format: md5<md5_hash_of_password+username>
HASH=$(echo -n "${POSTGRES_PASSWORD}${POSTGRES_USER:-postgres}" | md5sum | cut -d' ' -f1)
echo "\"${POSTGRES_USER:-postgres}\" \"md5${HASH}\"" > /etc/pgbouncer/userlist.txt

# Execute the command
exec "$@"
