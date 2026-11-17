#!/bin/bash
# scripts/send-logs-to-es.sh
# Lit les logs Apache générés et les injecte directement dans Elasticsearch via l'Ingest Pipeline

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

ES_URL="https://localhost:9200"
ES_USER="elastic"
ES_PASS="MySecurePassword123!"
INDEX_NAME="logs-apache_access-default"

echo "=== 1. Envoi des logs d'accès Apache vers Elasticsearch (Pipeline : apache-access-pipeline) ==="

docker compose exec -T apache-web cat /usr/local/apache2/logs/access_log 2>/dev/null | while IFS= read -r line; do
  if [ -n "$line" ]; then
    # Échappement des guillemets et barres obliques pour JSON
    json_escaped=$(printf '%s' "$line" | python3 -c 'import json, sys; print(json.dumps(sys.stdin.read()))')
    curl -k -s -X POST -u "${ES_USER}:${ES_PASS}" \
      "${ES_URL}/${INDEX_NAME}/_doc?pipeline=apache-access-pipeline" \
      -H "Content-Type: application/json" \
      -d "{\"message\": ${json_escaped}}" > /dev/null
  fi
done

echo "=== 2. Envoi des logs d'erreur Apache vers Elasticsearch (Pipeline : apache-error-pipeline) ==="
INDEX_ERROR="logs-apache_error-default"
docker compose exec -T apache-web cat /usr/local/apache2/logs/error_log 2>/dev/null | while IFS= read -r line; do
  if [ -n "$line" ]; then
    json_escaped=$(printf '%s' "$line" | python3 -c 'import json, sys; print(json.dumps(sys.stdin.read()))')
    curl -k -s -X POST -u "${ES_USER}:${ES_PASS}" \
      "${ES_URL}/${INDEX_ERROR}/_doc?pipeline=apache-error-pipeline" \
      -H "Content-Type: application/json" \
      -d "{\"message\": ${json_escaped}}" > /dev/null
  fi
done

# Rafraîchir les index pour recherche immédiate
curl -k -s -X POST -u "${ES_USER}:${ES_PASS}" "${ES_URL}/logs-apache*/_refresh" > /dev/null

echo "Logs ingérés avec succès dans ${INDEX_NAME} et ${INDEX_ERROR} !"
count=$(curl -k -s -u "${ES_USER}:${ES_PASS}" "${ES_URL}/logs-apache*/_count" | grep -o '"count":[0-9]*' | cut -d: -f2)
echo "Nombre total de documents indexés : ${count:-0}"
