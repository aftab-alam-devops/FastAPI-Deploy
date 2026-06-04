# Production-Grade AI Summarization & Gateway Service

A production-ready, containerized FastAPI application acting as an AI model proxy/gateway. Features rate limiting, semantic caching, relational logging, a hardened reverse proxy, cron database backups, and GitHub Actions CI/CD automation.

---

## Key Features

* **FastAPI Application**: Extensible gateway serving text summarization models..
* **Semantic/Exact Caching**: Integrates with Redis to store prompt-to-response mapping, reducing AI API invocation costs and latency.
* **Audit Logging**: Persists request stats (IP address, prompt, cache-hit, processing duration) in PostgreSQL.
* **Proxy Hardening**: Nginx handles rate limiting (10 reqs/sec), gzip compression, HTTP/HTTPS forwarding, and custom connection logging.
* **Container Security**: FastAPI runs under a limited system user (`appuser`), keeping root privilege isolated.
* **Host Security**: Automates host firewall configuration (UFW) and brute-force block rules (Fail2ban).
* **CI/CD Pipeline**: GitHub Actions linting, Docker build testing, and automated VPS deployment over SSH with zero-downtime reloads.
* **Data Safety**: Shell scripts to run automated gzipped DB backups (with retention cleanup) and restoration.

---

## Project Directory Structure

```text
FastAPI-Deploy/
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Actions CI/CD deployment pipeline
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI entrance & endpoints (health, AI query, logs)
│   ├── config.py               # Pydantic Settings management
│   ├── database.py             # SQLAlchemy engine & session setup
│   ├── models.py               # Database schemas for ORM (logs, prompts)
│   ├── schemas.py              # Pydantic input/output schemas
│   ├── redis_client.py         # Redis connection, rate limiting & cache utilities
│   ├── logger.py               # Production JSON/structured logging setup
│   ├── requirements.txt        # Python package dependencies
│   └── Dockerfile              # Multi-stage production-grade Python Dockerfile
├── nginx/
│   ├── Dockerfile              # Custom NGINX Dockerfile
│   ├── nginx.conf              # Main NGINX configuration (rate limit, security headers)
│   └── conf.d/
│       └── app.conf            # Server block configuration for proxy & SSL
├── scripts/
│   ├── backup.sh               # Cron-friendly PostgreSQL backup script
│   ├── restore.sh              # Database recovery script
│   └── setup-security.sh       # VPS Security setup (UFW firewall, fail2ban, SSH hardening)
├── docs/
│   ├── architecture.md         # System design diagrams and flowcharts
│   └── deployment.md           # Hosting guides, Let's Encrypt certificates, GHA setup
├── docker-compose.yml          # Base Docker Compose configuration (Local/Prod base)
├── docker-compose.prod.yml     # Production Docker Compose overrides (SSL, logs, restart)
└── .env.example                # Template for environment variables
```

---

## Detailed Documentation

- 📐 **[System Architecture](file:///c:/Users/Aftab%20Alam/OneDrive/Desktop/FastAPI-Deploy/docs/architecture.md)**: Container diagrams, network structures, and end-to-end endpoint logic sequence flows.
- 🚀 **[Production Deployment Manual](file:///c:/Users/Aftab%20Alam/OneDrive/Desktop/FastAPI-Deploy/docs/deployment.md)**: Comprehensive VPS server provisioning, Let's Encrypt certificates, Cron tasks, and GitHub Secrets configuration.

---

## Quickstart: Running Locally

You can spin up the full cluster locally on your machine using Docker and Docker Compose.

### Prerequisites
- Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) on your machine.

### Step 1: Clone and Configure Environments
1. Navigate to the project root directory.
2. Copy the configuration file:
   ```bash
   cp .env.example .env
   ```
3. (Optional) Open `.env` and fill in `HF_API_TOKEN` to connect real Hugging Face models, otherwise, it runs using an offline heuristic engine.

### Step 2: Spin Up the Containers
Build and boot the services in detached mode:
```bash
docker compose up -d --build
```

Docker will automatically create the network, initialize the PostgreSQL database schema on start, boot Redis, compile the FastAPI app, and spin up Nginx.

### Step 3: Verify the Running Services
1. Run `docker compose ps` to verify that all 4 containers are in a `running` state.
2. Check the API health check endpoint:
   ```bash
   curl http://localhost/health
   ```
   **Expected Response (HTTP 200)**:
   ```json
   {
     "status": "healthy",
     "database": "connected",
     "redis": "connected",
     "version": "1.0.0",
     "timestamp": "2026-06-04T09:25:00.000Z"
   }
   ```

### Step 4: Interact with the Gateway API
* **API Documentation (Swagger UI)**: Open your browser to [http://localhost/docs](http://localhost/docs) to test requests interactively.
* **Inference Endpoint**:
  ```bash
  curl -X POST http://localhost/api/v1/summarize \
    -H "Content-Type: application/json" \
    -d '{"text": "FastAPI is a modern, fast (high-performance), web framework for building APIs with Python 3.8+ based on standard Python type hints. It is incredibly fast, easy to write, and supports automatic interactive documentation out of the box."}'
  ```
  *Subsequent identical requests will load instantly with `"cached": true`.*

* **Audit Logs Endpoint**:
  ```bash
  curl http://localhost/api/v1/logs
  ```

### Step 5: Tear Down Services
To stop and clean up containers and local networks:
```bash
docker compose down
```
*(To remove persistent data volumes as well, append the `-v` flag: `docker compose down -v`)*
