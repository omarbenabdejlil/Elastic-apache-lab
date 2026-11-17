#!/bin/bash
# scripts/generate-training-data.sh
# Génère un historique réaliste (plusieurs heures de trafic normal) puis injecte l'attaque

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

ES_URL="https://localhost:9200"
ES_USER="elastic"
ES_PASS="MySecurePassword123!"
INDEX_NAME="logs-apache_access-default"

echo "=== 1. Génération de 2 heures d'historique de trafic normal (apprentissage ML) ==="

python3 - << 'EOF'
import urllib.request
import ssl
import json
import time
from datetime import datetime, timedelta, timezone

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://localhost:9200/logs-apache_access-default/_doc?pipeline=apache-access-pipeline"
auth = "Basic " + __import__("base64").b64encode(b"elastic:MySecurePassword123!").decode("ascii")

# Heure de base : il y a 3 heures
now = datetime.now(timezone.utc)
start_time = now - timedelta(hours=3)

# 1. Générer du trafic normal régulier (ex: ~1 requête toutes les 30s pendant 2h45)
# Soit environ 330 requêtes normales réparties
current = start_time
print("Génération du trafic normal...")
batch_docs = []

while current < now - timedelta(minutes=15):
    # Log Apache Combined Format
    # IP - - [dd/MMM/yyyy:HH:mm:ss +0000] "GET /index.html HTTP/1.1" 200 191 "-" "Mozilla/5.0..."
    ts_str = current.strftime("%d/%b/%Y:%H:%M:%S +0000")
    log_line = f'192.168.1.50 - - [{ts_str}] "GET /index.html HTTP/1.1" 200 191 "-" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"'

    req = urllib.request.Request(url, data=json.dumps({"message": log_line}).encode(), headers={
        "Authorization": auth,
        "Content-Type": "application/json"
    })
    urllib.request.urlopen(req, context=ctx)
    current += timedelta(seconds=25)

print("Trafic normal généré !")

# 2. Générer l'attaque cynique (rafale massive de 150 requêtes en 2 minutes avec statut 404 et user agent Nmap)
print("Injection de l'attaque massive (scan de vulnérabilités)...")
attack_start = now - timedelta(minutes=10)
attack_paths = ["wp-admin", "wp-login.php", ".env", "config.php", "phpmyadmin", "backup.sql", "administrator", "api/.env"]
attacker_ip = "45.133.1.99"
attack_ua = "Mozilla/5.0 (compatible; Nmap Scripting Engine; https://nmap.org/book/nse.html)"

for i in range(120):
    attack_time = attack_start + timedelta(seconds=(i % 60))
    ts_str = attack_time.strftime("%d/%b/%Y:%H:%M:%S +0000")
    path = attack_paths[i % len(attack_paths)]
    log_line = f'{attacker_ip} - - [{ts_str}] "GET /{path} HTTP/1.1" 404 196 "-" "{attack_ua}"'

    req = urllib.request.Request(url, data=json.dumps({"message": log_line}).encode(), headers={
        "Authorization": auth,
        "Content-Type": "application/json"
    })
    urllib.request.urlopen(req, context=ctx)

print("Attaque injectée avec succès !")
EOF

# Rafraîchir
curl -k -s -X POST -u "${ES_USER}:${ES_PASS}" "${ES_URL}/logs-apache*/_refresh" > /dev/null
count=$(curl -k -s -u "${ES_USER}:${ES_PASS}" "${ES_URL}/logs-apache*/_count" | grep -o '"count":[0-9]*' | cut -d: -f2)
echo "Total documents indexés : $count"
