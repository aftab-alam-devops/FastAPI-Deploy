# Production Deployment Walkthrough

This guide provides step-by-step instructions to deploy the AI Gateway API onto a VPS (Virtual Private Server) running Ubuntu 22.04 LTS.

---

## 1. VPS Host Setup & Requirements

### Recommended System Specifications
- **CPU**: 1 vCPU (minimum)
- **RAM**: 1GB (minimum), 2GB (recommended to comfortably support Docker build workloads)
- **Storage**: 15GB SSD or higher
- **OS**: Ubuntu 22.04 / 24.04 LTS

---

## 2. Server Security Hardening

Before deploying any code, secure the host VPS.

1. SSH into your VPS:
   ```bash
   ssh root@your_vps_ip
   ```
2. Create the target project directory:
   ```bash
   mkdir -p /srv/api
   ```
3. Copy the security setup script (`scripts/setup-security.sh`) to the server, or create it directly on the host, and execute:
   ```bash
   sudo bash /srv/api/scripts/setup-security.sh
   ```

> [!IMPORTANT]
> The security script restricts incoming network requests to only SSH (Port 22), HTTP (Port 80), and HTTPS (Port 443). All other ports, including Postgres (5432) and Redis (6379), are blocked from outside network access for database protection.

---

## 3. Install Docker & Docker Compose on VPS

Run the following commands on the server to install Docker Engine and the Compose plugin:

```bash
# Update package list and install prerequisites
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Set up the repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker packages
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Verify installation
docker --version
docker compose version
```

---

## 4. SSL Certificate Setup (Let's Encrypt)

### Option A: If you do NOT have a Domain Name (HTTP Only)
If you don't have a domain registered, you will access the service over standard HTTP using your server's IP address.
1. Leave the Nginx configuration as-is (with the port 443 block commented out).
2. Direct your client requests to `http://your_vps_ip/api/v1/summarize`.

---

### Option B: If you have a Domain Name (Recommended)
1. Point your domain's DNS `A Record` to your VPS public IP address.
2. Spin up Nginx in HTTP-only mode first to answer the challenge verification:
   ```bash
   cd /srv/api
   docker compose up -d nginx
   ```
3. Run Certbot in webroot mode to obtain an SSL certificate:
   ```bash
   docker run -it --rm --name certbot \
     -v "api_certbot_etc:/etc/letsencrypt" \
     -v "api_certbot_var:/var/lib/letsencrypt" \
     -v "api_certbot_webroot:/var/www/certbot" \
     certbot/certbot certonly --webroot \
     -w /var/www/certbot \
     -d yourdomain.com \
     --email your_email@example.com \
     --agree-tos \
     --no-eff-email
   ```
4. Once certificates are issued, modify Nginx rules:
   - Edit `/srv/api/nginx/conf.d/app.conf` (uncomment the port 443 server block, replace `yourdomain.com` with your actual domain).
5. Reload Nginx configuration without down-time:
   ```bash
   docker compose exec nginx nginx -s reload
   ```

---

## 5. Setting up GitHub Actions CI/CD Secrets

To automate deployments via Git commits, configure the following secrets in your GitHub repository:

1. In your GitHub repository, navigate to **Settings** > **Secrets and variables** > **Actions**.
2. Click **New repository secret** and add the following:

| Secret Name | Value Example / Description |
| :--- | :--- |
| `SERVER_HOST` | The public IP address of your VPS |
| `SERVER_USER` | SSH user to deploy with (e.g., `root`) |
| `SSH_PRIVATE_KEY` | Contents of your private SSH key (`~/.ssh/id_rsa`) that matches public key authorized on VPS (`~/.ssh/authorized_keys`) |
| `POSTGRES_USER` | DB admin username (e.g. `db_admin`) |
| `POSTGRES_PASSWORD` | Strong database password |
| `POSTGRES_DB` | Persistent database name (e.g. `ai_gateway`) |
| `REDIS_PASSWORD` | Secure password to access Redis instance |
| `HF_API_TOKEN` | (Optional) Hugging Face API key for external LLM calls |
| `API_SECRET_KEY` | (Optional) Secret token clients must pass in `X-API-Key` headers |

Once configured, pushing code to the `main` branch automatically triggers the lint checks, validates the docker builds, syncs code to the server, updates the containers, and reloads Nginx dynamically.

---

## 6. Zero-Downtime Deployment Architecture

Our deployment pipeline implements zero-downtime reloads using Nginx:
1. **Container Update**: Running `docker compose up -d --build app` updates the FastAPI container. If building a new image, the old container continues handling requests until the new container passes health checks and takes over the socket.
2. **Proxy Hot Reload**: Running `docker compose exec -T nginx nginx -s reload` instructs Nginx to spawn new worker processes using the updated configuration/routes, while gracefully shutting down old workers only after they complete current connections. Clients experience no connection drops.

---

## 7. Database Backups and Recovery

### Setting Up Automated Backups
We use the `scripts/backup.sh` script to perform nightly database dumps. 
1. Make sure backup scripts are executable:
   ```bash
   chmod +x /srv/api/scripts/backup.sh
   ```
2. Add a cron job to run the backup daily at 2:00 AM:
   ```bash
   # Open cron editor
   sudo crontab -e
   ```
3. Append this line at the bottom:
   ```text
   0 2 * * * /bin/bash /srv/api/scripts/backup.sh >> /var/log/cron-db-backup.log 2>&1
   ```

### Restoring the Database
To restore data from a specific backup file (e.g. `db_backup_20260604_020000.sql.gz`):
```bash
sudo bash /srv/api/scripts/restore.sh /srv/backups/db/db_backup_20260604_020000.sql.gz
```

---

## 8. Basic Monitoring and Diagnostics

- **Inspect Running Services**:
  ```bash
  docker compose ps
  ```
- **Real-Time Resource Metrics** (CPU, Memory, Net I/O):
  ```bash
  docker stats
  ```
- **Stream Application Logs**:
  ```bash
  docker compose logs -f app
  ```
- **Stream Web Proxy Logs**:
  ```bash
  docker compose logs -f nginx
  ```
