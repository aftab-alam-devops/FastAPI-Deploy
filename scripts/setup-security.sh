#!/usr/bin/env bash

# ====================================================================
# VPS Basic Security Hardening Script
# ====================================================================
# This script configures a basic firewall (UFW) and fail2ban rules
# to protect your VPS against brute force attacks and open port scans.
# Run this on your server as root: `sudo bash setup-security.sh`

set -euo pipefail

echo "=========================================================="
echo "Starting VPS Security Hardening Setup..."
echo "=========================================================="

# Ensure script runs as root
if [ "$EUID" -ne 0 ]; then
  echo "[ERROR] Please run this script with sudo or as root." >&2
  exit 1
fi

# 1. Update system package index
echo "[INFO] Updating package lists..."
apt-get update -y

# 2. Install Firewall (UFW) and Fail2ban
echo "[INFO] Installing UFW and Fail2ban..."
apt-get install -y ufw fail2ban

# 3. Configure UFW Firewall rules
echo "[INFO] Configuring firewall rules..."
ufw default deny incoming
ufw default allow outgoing

# Allow standard ports (adjust SSH port 22 if using a custom port)
ufw allow 22/tcp comment 'SSH Port'
ufw allow 80/tcp comment 'HTTP Nginx Reverse Proxy'
ufw allow 443/tcp comment 'HTTPS Nginx Secure Proxy'

# Enable the firewall (force bypass interactive prompt)
echo "y" | ufw enable
echo "[SUCCESS] Firewall configured and enabled."
ufw status verbose

# 4. Configure Fail2ban for SSH Protection
echo "[INFO] Creating local Fail2ban configuration..."
# Write custom jail rules to jail.local
cat <<EOF > /etc/fail2ban/jail.local
[DEFAULT]
# Ban host for 1 hour if they fail authentication
bantime  = 1h
# Window in which failures must occur to trigger a ban
findtime = 10m
# Number of failures before ban is applied
maxretry = 5

[sshd]
enabled = true
port    = ssh
logpath = %(sshd_log)s
backend = %(sshd_backend)s
EOF

# Restart and enable fail2ban service
echo "[INFO] Restarting Fail2ban service..."
systemctl restart fail2ban
systemctl enable fail2ban

echo "[SUCCESS] Fail2ban status:"
fail2ban-client status

echo "=========================================================="
echo "Security hardening complete!"
echo "Your server now denies all incoming traffic except SSH, HTTP, and HTTPS."
echo "Fail2ban is active and monitoring SSH logs for brute force attacks."
echo "=========================================================="
