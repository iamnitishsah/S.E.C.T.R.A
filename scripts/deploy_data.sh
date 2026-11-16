#!/usr/bin/env bash
# Copy this machine's loaded data to the server, so nothing is downloaded or embedded there.
#   scripts/deploy_data.sh ubuntu@HOST            (SSH_KEY and REMOTE_DIR can be set in the environment)
#
#   1. MySQL   dump the local database and restore it into the server's MySQL container, over SSH
#   2. reader  create the read-only user on the server (users are not part of a dump)
#   3. Qdrant  index the cached vectors into the server's Qdrant through an SSH tunnel
# Run from the repository root, with the local containers up and the virtualenv active.
# On the server: the repository cloned, .env in place, `make up` and `make build` done.
set -euo pipefail

HOST="${1:?usage: scripts/deploy_data.sh user@host}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/sectra.pem}"
REMOTE_DIR="${REMOTE_DIR:-S.E.C.T.R.A}"
TUNNEL_PORT="${TUNNEL_PORT:-16333}"
SSH=(ssh -i "$SSH_KEY" -o ServerAliveInterval=30 "$HOST")

count_local()  { docker compose exec -T mysql sh -c "MYSQL_PWD=\"\$MYSQL_ROOT_PASSWORD\" mysql -uroot -N -e \"SELECT COUNT(*) FROM \$MYSQL_DATABASE.$1\""; }
count_remote() { "${SSH[@]}" "cd $REMOTE_DIR && docker compose exec -T mysql sh -c 'MYSQL_PWD=\"\$MYSQL_ROOT_PASSWORD\" mysql -uroot -N -e \"SELECT COUNT(*) FROM \$MYSQL_DATABASE.$1\"'"; }

echo "== 1/3 MySQL: dump here, restore on $HOST"
docker compose exec -T mysql sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqldump -uroot --single-transaction --no-tablespaces --routines --databases "$MYSQL_DATABASE"' \
    | gzip \
    | "${SSH[@]}" "cd $REMOTE_DIR && gunzip -c | docker compose exec -T mysql sh -c 'MYSQL_PWD=\"\$MYSQL_ROOT_PASSWORD\" exec mysql -uroot'"
for table in companies filings filing_sections financial_metrics financial_facts; do
    printf "   %-20s local %-8s server %s\n" "$table" "$(count_local "$table")" "$(count_remote "$table")"
done

echo "== 2/3 read-only database user on the server"
"${SSH[@]}" "cd $REMOTE_DIR && docker compose --profile api run --rm api python -m sectra.storage.setup_reader"

echo "== 3/3 Qdrant: index cached vectors through an SSH tunnel (no embedding calls)"
SOCKET="$(mktemp -u)"
ssh -i "$SSH_KEY" -M -S "$SOCKET" -f -N -L "$TUNNEL_PORT:127.0.0.1:6333" "$HOST"
trap 'ssh -S "$SOCKET" -O exit "$HOST" 2>/dev/null || true' EXIT
QDRANT_URL="http://localhost:$TUNNEL_PORT" python -m sectra.ingestion.index_chunks
curl -s "http://localhost:$TUNNEL_PORT/collections" | head -c 300; echo

echo "== done. On the server: make up-api"