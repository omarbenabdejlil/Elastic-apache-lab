#!/bin/bash
# scripts/setup-pipelines.sh
# Charge l'ensemble des Ingest Pipelines Apache dans Elasticsearch

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

ES_URL="https://localhost:9200"
AUTH="elastic:MySecurePassword123!"

echo "Chargement du pipeline 'apache-access-pipeline'..."
curl -k -s -X PUT -u "$AUTH" \
  -H "Content-Type: application/json" \
  -d @pipelines/apache-access-pipeline.json \
  "$ES_URL/_ingest/pipeline/apache-access-pipeline" | grep -q '"acknowledged":true' && echo "OK : apache-access-pipeline"

echo "Chargement du pipeline 'apache-error-pipeline'..."
curl -k -s -X PUT -u "$AUTH" \
  -H "Content-Type: application/json" \
  -d @pipelines/apache-error-pipeline.json \
  "$ES_URL/_ingest/pipeline/apache-error-pipeline" | grep -q '"acknowledged":true' && echo "OK : apache-error-pipeline"

echo "Chargement du pipeline 'apache-logs-router'..."
curl -k -s -X PUT -u "$AUTH" \
  -H "Content-Type: application/json" \
  -d @pipelines/apache-logs-router.json \
  "$ES_URL/_ingest/pipeline/apache-logs-router" | grep -q '"acknowledged":true' && echo "OK : apache-logs-router"

echo ""
echo "Tous les pipelines ont été enregistrés avec succès dans Elasticsearch !"
