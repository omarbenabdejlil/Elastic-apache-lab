#!/bin/bash
# scripts/start-simulator-ui.sh
# Lance le simulateur d'attaques et dashboard en arrière-plan

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR/simulator-app"

# Arrêter une instance existante si en cours
fuser -k 5000/tcp 2>/dev/null || true

echo "Démarrage de l'application FastAPI & Dashboard sur http://0.0.0.0:5000..."
nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 5000 > /tmp/simulator-app.log 2>&1 &

sleep 2
if curl -s -I http://localhost:5000 | grep -q "200 OK"; then
  echo "Application démarrée avec succès !"
  echo "Interface Web : http://localhost:5000"
  echo "Documentation API Swagger : http://localhost:5000/docs"
else
  echo "Erreur lors du démarrage. Logs récents :"
  cat /tmp/simulator-app.log
  exit 1
fi
