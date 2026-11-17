#!/bin/bash
# scripts/stop-simulator-ui.sh
# Arrête le simulateur d'attaques

echo "Arrêt du simulateur d'attaques sur le port 5000..."
fuser -k 5000/tcp 2>/dev/null || true
echo "Simulateur arrêté."
