# Cloud-IoT : Infrastructure DevOps CI/CD

![CI](https://github.com/AhBourass/cloud-iot/actions/workflows/ci.yml/badge.svg)

Chaîne IoT de bout en bout : un boîtier publie des mesures en MQTT, une API les valide
et les stocke dans une base de séries temporelles, et une stack de supervision permet de
visualiser à la fois les données et la santé du système. Le tout est conteneurisé et
vérifié automatiquement par une pipeline CI/CD.

Projet académique, 2026.

## Architecture

```
 Boîtier / simulateur ──MQTT 1883──► Mosquitto ──subscribe──► API FastAPI ──HTTP 8086──► InfluxDB
                                                                  │                         │
                                                         GET /metrics (pull)                │
                                                                  ▼                         │
                                                             Prometheus ────────┐           │
                                                                                ▼           ▼
                                                                              Grafana (2 datasources)
```

Deux plans distincts :
- **Plan données** : boîtier, Mosquitto, API, InfluxDB (mesures métier : température, humidité).
- **Plan supervision** : API, Prometheus, Grafana (santé du service, nombre de messages, erreurs).

## Stack

| Brique | Rôle |
|--------|------|
| Mosquitto 2 | Broker MQTT (publish/subscribe) |
| FastAPI (Python 3.12) | Ingestion MQTT, API REST, endpoint `/metrics` |
| InfluxDB 2.7 | Stockage des séries temporelles (rétention 30 jours) |
| Prometheus | Collecte des métriques (modèle pull, toutes les 15 s) |
| Grafana | Dashboards (sources Prometheus et InfluxDB provisionnées) |
| Docker Compose | Orchestration, réseau privé, volumes, healthchecks |
| GitHub Actions | CI : flake8, pytest, build Docker, scan Trivy |

## Démarrage rapide

Prérequis : Docker et Docker Compose v2.

```bash
git clone https://github.com/AhBourass/cloud-iot.git
cd cloud-iot
cp .env.example .env        # PowerShell : Copy-Item .env.example .env
docker compose up -d --build
docker compose ps           # tous les services doivent être "healthy" ou "Up"
```

Pensez à modifier les valeurs de `.env` (mots de passe, token) avant tout usage réel.

## Services et ports

| Service | URL / port |
|---------|-----------|
| Mosquitto | `localhost:1883` (MQTT) |
| API (Swagger) | http://localhost:8000/docs |
| InfluxDB | http://localhost:8086 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |

## Tester la chaîne

Publier une mesure :

```bash
docker exec mosquitto mosquitto_pub -t "devices/esp32-01/telemetry" -q 1 \
  -m '{"temperature":23.4,"humidity":55.2}'
```

PowerShell (les guillemets du JSON passent par l'entrée standard) :

```powershell
'{"temperature":23.4,"humidity":55.2}' | docker exec -i mosquitto mosquitto_pub -t "devices/esp32-01/telemetry" -q 1 -s
```

Vérifier :

```bash
curl http://localhost:8000/health
curl http://localhost:8000/devices/esp32-01/readings
curl http://localhost:8000/metrics | grep mqtt_messages
```

Un message invalide (`{"temperature":500}`) est rejeté, journalisé, et compté dans la métrique
`mqtt_messages_received_total{status="invalid_payload"}`.

## Endpoints de l'API

| Méthode | Route | Rôle |
|---------|-------|------|
| GET | `/health` | État de l'API et de ses dépendances (InfluxDB, MQTT) |
| POST | `/devices/{id}/readings` | Ingestion d'une mesure par HTTP |
| GET | `/devices/{id}/readings` | Dernières mesures d'un boîtier |
| GET | `/metrics` | Métriques au format Prometheus |

Topics MQTT : `devices/<device_id>/telemetry` (abonnement `devices/+/telemetry`, QoS 1).

## Tests et qualité

```bash
pip install -r requirements-dev.txt
flake8 app tests
pytest -v
```

Les tests utilisent des mocks : ni broker ni base de données ne sont nécessaires.

## CI/CD

À chaque push sur `main` et à chaque pull request, le workflow `.github/workflows/ci.yml` exécute :

1. **lint-test** : flake8 et pytest sur Python 3.11 et 3.12 (matrice).
2. **docker-scan** (après lint-test) : scan Trivy du dépôt (CVE, secrets, mauvaise configuration),
   build de l'image Docker, puis scan Trivy de l'image. La pipeline échoue sur toute
   vulnérabilité de sévérité HIGH ou CRITICAL pour laquelle un correctif existe.

## Sécurité

- L'API tourne avec un utilisateur non-root dans le conteneur.
- Les secrets sont lus dans `.env`, ignoré par Git (`.env.example` documente les variables).
- Les versions des dépendances et des images sont épinglées.
- Validation stricte des payloads (Pydantic) et des identifiants de boîtier (protection contre
  l'injection dans les requêtes Flux).
- Permissions minimales du workflow CI (`contents: read`).

## Limites connues et pistes d'amélioration

  - Mosquitto est authentifié (`password_file`) mais sans TLS ni ACL par topic : les identifiants
    circulent en clair sur le port 1883.
  (`password_file`, ACL par topic) et MQTT sur TLS (port 8883).
- Tous les ports sont publiés pour faciliter les tests locaux : en production, un reverse proxy
  avec TLS serait le seul point d'entrée.
- Le client MQTT est intégré à l'API : avec plusieurs réplicas, chaque message serait traité
  plusieurs fois. Piste : un worker d'ingestion séparé ou les shared subscriptions MQTT 5.
- Le dashboard Grafana est créé manuellement (seules les datasources sont provisionnées).
- Un seul broker et une seule instance InfluxDB : pas de haute disponibilité.
- Pas d'alerting (règles Prometheus et Alertmanager à ajouter).

## Arborescence

```
app/            code de l'API (FastAPI, client MQTT, InfluxDB, métriques)
tests/          tests pytest
mosquitto/      configuration du broker
prometheus/     configuration de la collecte
grafana/        provisioning des datasources
.github/        workflow CI
Dockerfile, docker-compose.yml, requirements*.txt, .env.example
```