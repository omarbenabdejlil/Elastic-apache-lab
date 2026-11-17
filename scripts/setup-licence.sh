#!/bin/bash
# scripts/setup-licence.sh

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

echo "Activation de la licence d'essai 30 jours (Trial)..."
curl -k -X POST -u "elastic:MySecurePassword123!" "https://localhost:9200/_license/start_trial?acknowledge=true"
echo ""
echo "Licence activée avec succès !"
