#!/bin/bash
# scripts/simulate-traffic.sh

APACHE_URL="http://localhost:8080"

echo "=== Étape 1 : Simulation de trafic légitime (normal) ==="
for i in {1..50}; do
  curl -s -o /dev/null -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" "${APACHE_URL}/index.html"
  sleep 0.5
done

echo "=== Étape 2 : Simulation d'attaque par brute-force / scan d'URL (anomalie) ==="
# On simule un scanner automatisé qui cherche des vulnérabilités (wp-admin, .env, phpmyadmin...) à haute fréquence
ATTACK_USER_AGENT="Mozilla/5.0 (compatible; Nmap Scripting Engine; https://nmap.org/book/nse.html)"
PATHS=("wp-login.php" "wp-admin" ".env" "config.php" "phpmyadmin" "administrator/index.php" "backup.sql" "api/.env")

for path in "${PATHS[@]}"; do
  for i in {1..5}; do
    curl -s -o /dev/null -A "${ATTACK_USER_AGENT}" "${APACHE_URL}/${path}"
    # Pas de sleep pour simuler la vélocité d'une attaque automatisée
  done
done

echo "Simulation terminée !"
