# Laboratoire de Test Elastic : Ingest Pipelines Apache & Machine Learning (Détection d'Anomalies)

Guide complet pour déployer, configurer, injecter et analyser les logs d'un serveur Web Apache dans Elasticsearch avec les **Ingest Pipelines** et le **Machine Learning (ML)**.

---

## 📋 Informations d'accès

| Service | URL | Identifiants / Description |
| :--- | :--- | :--- |
| **Simulateur d'Attaques Web (UI)** | [http://localhost:5000](http://localhost:5000) | Dashboard de contrôle & flux en temps réel |
| **API Swagger Docs** | [http://localhost:5000/docs](http://localhost:5000/docs) | Endpoints REST de simulation d'attaques |
| **Kibana** | [http://localhost:5601](http://localhost:5601) | `elastic` / `MySecurePassword123!` |
| **Elasticsearch** | [https://localhost:9200](https://localhost:9200) | `elastic` / `MySecurePassword123!` |
| **Apache Web** | [http://localhost:8080](http://localhost:8080) | Serveur cible |

---

## 🛡️ Simulateur d'Attaques & API REST (Temps Réel)

L'application **FastAPI** propose une interface visuelle et des endpoints d'API pour injecter des attaques et observer les alertes ML immédiatement :

### Gestion du simulateur :
* **Démarrer l'application Web & API** :
  ```bash
  ./scripts/start-simulator-ui.sh
  ```
* **Arrêter l'application** :
  ```bash
  ./scripts/stop-simulator-ui.sh
  ```

### Endpoints d'API disponibles (`http://localhost:5000/docs`) :
* `POST /api/simulate/traffic/normal` : Trafic légitime utilisateur (pages valides, HTTP 200).
* `POST /api/simulate/attack/nmap` : Scan d'URLs sensibles avec User-Agent Nmap (HTTP 404).
* `POST /api/simulate/attack/bruteforce` : Rafale de tentatives de mot de passe échouées sur `/login` (HTTP 401).
* `POST /api/simulate/attack/sqli` : Payloads d'injection SQL (`' OR '1'='1`, `UNION SELECT`) provoquant des erreurs HTTP 500.
* `POST /api/simulate/attack/xss` : Payloads Cross-Site Scripting (`<script>`, tags onerror) (HTTP 400).
* `GET /api/stats` : Statistiques en direct (état cluster, nombre de docs indexés, job ML).
* `GET /api/alerts` : Remontée directe des anomalies et scores calculés par Elasticsearch ML.

---

## 💡 Comment filtrer / ignorer des variables ou des documents dans la Pipeline ?

Oui, il est tout à fait possible d'**ignorer des champs** ou d'**ignorer/filtrer des documents entiers** dans un Ingest Pipeline :

### 1. Supprimer/ignorer des variables (champs spécifiques)
Utilisez le processeur `remove` avec `ignore_missing: true` pour éliminer des champs que vous ne souhaitez pas stocker (champs sensibles, temporaires ou verbeux) :
```json
{
  "remove": {
    "field": ["user.name", "http.request.referrer", "temp"],
    "ignore_missing": true
  }
}
```

### 2. Ne modifier un champ que sous condition (ignorer certaines valeurs)
Ajoutez une condition Painless `if` sur le processeur :
```json
{
  "set": {
    "field": "source.ip",
    "value": "{{temp.client_ip}}",
    "if": "ctx.temp?.client_ip != null && ctx.temp.client_ip != '127.0.0.1'"
  }
}
```

### 3. Ignorer/abandonner complètement un document (Drop Processor)
Si vous souhaitez ne pas indexer certains logs (ex: ignorer les healthchecks ou une IP spécifique) :
```json
{
  "drop": {
    "if": "ctx.url?.original != null && ctx.url.original.contains('/healthz')"
  }
}
```

---

## 🚀 Étape 1 : Démarrage des Conteneurs

Depuis le dossier `elastic-apache-lab/` :

```bash
docker compose up -d
```

Vérifiez que tous les services sont `healthy` :
```bash
docker compose ps
```

---

## ⚙️ Étape 2 : Activer la Licence Trial (30 jours)

Elasticsearch démarre avec `xpack.license.self_generated.type=trial`.  
Pour vous assurer que la licence Platinum/Trial est bien activée :

```bash
./scripts/setup-licence.sh
```

---

## 📥 Étape 3 : Charger les Ingest Pipelines

Les Ingest Pipelines définis dans `pipelines/` gèrent le parsing ECS, GeoIP, User-Agent, le nettoyage des champs temporaires et le routage des logs :

```bash
./scripts/setup-pipelines.sh
```

---

## 🎯 Étape 4 : Générer les Données (Baseline Normale + Attaque ML)

Pour que l'algorithme de Machine Learning non supervisé détecte efficacement une anomalie, il lui faut une base d'apprentissage (trafic normal régulier) suivie de l'attaque.

Exécutez le script d'apprentissage et d'attaque :
```bash
./scripts/generate-training-data.sh
```

Ce script génère :
1. **~3 heures de trafic légitime régulier** (~12 requêtes / 5 min).
2. **Une vague d'attaque cynique** (120 requêtes en rafale vers `.env`, `wp-login.php`, `phpmyadmin` avec l'IP `45.133.1.99` et le User-Agent `Nmap Scripting Engine`).

*(Optionnel) Pour générer du trafic direct sur le conteneur Apache local :*
```bash
./scripts/simulate-traffic.sh
./scripts/send-logs-to-es.sh
```

Vérifier le nombre de documents indexés :
```bash
curl -k -s -u "elastic:MySecurePassword123!" "https://localhost:9200/logs-apache*/_count?pretty"
```

---

## 🧠 Étape 5 : Configuration & Visualisation dans Kibana

### 5.1 Créer la Data View dans Kibana
1. Connectez-vous sur **[http://localhost:5601](http://localhost:5601)** (`elastic` / `MySecurePassword123!`).
2. Allez dans le menu `☰` > **Stack Management** > **Data Views**.
3. Cliquez sur **Create data view** :
   * **Name** : `Apache Logs`
   * **Index pattern** : `logs-apache*`
   * **Timestamp field** : `@timestamp`
4. Cliquez sur **Save data view to Kibana**.

### 5.2 Créer le Job de Détection d'Anomalies (Machine Learning)
1. Allez dans le menu `☰` > **Analytics** > **Machine Learning** > **Anomaly Detection**.
2. Cliquez sur **Create job** et sélectionnez la Data View **Apache Logs**.
3. Choisissez **Multi-metric Job** :
   * **Time range** : Cliquez sur **Use full data** (ou sélectionnez la plage du jour).
   * **Fields & Metrics** :
     * Métrique 1 : `high_count` (détecte l'explosion du volume de requêtes).
     * Métrique 2 : `distinct count` (ou `cardinality`) sur le champ `http.response.status_code`.
   * **Bucket span** : Choisissez `5m` (5 minutes pour une détection fine).
   * **Split data by** : `source.ip`
   * **Influencers** : Ajoutez `source.ip` et `user_agent.original`.
   * **Job ID** : `apache-traffic-anomaly`
4. Cliquez sur **Create Job** puis sur **Start datafeed**.

*(Alternative en une commande CLI) :*
```bash
curl -k -s -X POST -u "elastic:MySecurePassword123!" "https://localhost:9200/_ml/anomaly_detectors/apache-traffic-anomaly/_open"
curl -k -s -X POST -u "elastic:MySecurePassword123!" "https://localhost:9200/_ml/datafeeds/datafeed-apache-traffic-anomaly/_start"
```

### 5.3 Analyser l'Anomalie dans Kibana
1. Ouvrez l'onglet **Anomaly Explorer** ou **Single Metric Viewer** sur le job `apache-traffic-anomaly`.
2. Réglez le sélecteur temporel (en haut à droite) sur **Today** ou **Last 24 hours**.
3. Vous observerez :
   * Un pic critique rouge/orange correspondant à l'heure de l'attaque.
   * L'écart statistique : valeur attendue (~13 requêtes) vs observée (120 requêtes).
   * Les **Influencers** identifiés : l'IP source `45.133.1.99` et le User-Agent offensif `Nmap Scripting Engine`.

---

## 🔍 Étape 6 : Examiner les Logs Normalisés ECS

### Dans Kibana Discover
* Allez dans **Analytics** > **Discover** > sélectionnez la Data View **Apache Logs**.
* Dépliez un document pour observer le découpage automatique : `http.response.status_code`, `http.request.method`, `url.original`, `source.ip`, `user_agent.name`.

### Tester le Pipeline en direct (Console Dev Tools)
```json
POST _ingest/pipeline/apache-access-pipeline/_simulate
{
  "docs": [
    {
      "_source": {
        "message": "8.8.8.8 - - [16/Nov/2026:16:00:00 +0000] \"POST /login.php HTTP/1.1\" 500 532 \"-\" \"curl/7.88.1\""
      }
    }
  ]
}
```

---

## 🛠️ Commandes Utiles de Debugging

* **Statut des conteneurs :**
  ```bash
  docker compose ps
  ```

* **Vérifier l'état du job ML et ses buckets d'anomalies :**
  ```bash
  curl -k -s -u "elastic:MySecurePassword123!" "https://localhost:9200/_ml/anomaly_detectors/apache-traffic-anomaly/results/records?pretty"
  ```
