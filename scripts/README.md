# IXOM-POC Deployment Scripts

This directory contains automation scripts for deploying and managing the IXOM-POC application on a Digital Ocean droplet.

## Scripts

### `deploy.sh`
**Purpose**: Initial deployment setup  
**Usage**: `./scripts/deploy.sh`  
**What it does**:
- Validates environment configuration (.env file)
- Creates required directories
- Builds Docker image
- Starts containers
- Performs health check

**Run this**:
- On first deployment
- After major infrastructure changes

---

### `update.sh`
**Purpose**: Update application to latest version  
**Usage**: `./scripts/update.sh`  
**What it does**:
- Pulls latest code from Git
- Rebuilds Docker image
- Restarts containers with zero downtime

**Run this**:
- After pushing code changes to GitHub
- When deploying new features or bug fixes

---

### `monitor.sh`
**Purpose**: Display system status and health  
**Usage**: `./scripts/monitor.sh`  
**What it does**:
- Shows container status
- Displays resource usage (CPU, memory)
- Shows recent logs
- Checks Nginx status
- Reports disk usage

**Run this**:
- To check application health
- When troubleshooting issues
- For routine status checks

---

### `backup.sh`
**Purpose**: Backup application data  
**Usage**: `./scripts/backup.sh`  
**What it does**:
- Backs up logs directory
- Backs up outputs directory
- Backs up data directory
- Creates sanitized copy of .env
- Cleans up backups older than 7 days

**Run this**:
- Manually before major updates
- Automatically via cron (recommended: daily at 2 AM)

**Set up automatic backups**:
```bash
sudo crontab -e
# Add: 0 2 * * * /opt/ixom-poc/scripts/backup.sh >> /var/log/ixom-backup.log 2>&1
```

---

## Quick Reference

```bash
# Make scripts executable (first time only)
chmod +x scripts/*.sh

# Deploy application
./scripts/deploy.sh

# Update to latest version
./scripts/update.sh

# Check status
./scripts/monitor.sh

# Create backup
./scripts/backup.sh
```

---

## Prerequisites

All scripts require:
- Docker and Docker Compose installed
- `.env` file configured with OPENAI_API_KEY
- Scripts to be executable (`chmod +x scripts/*.sh`)

---

## Troubleshooting

**Permission denied error**:
```bash
chmod +x scripts/*.sh
```

**Script fails with "command not found"**:
```bash
# Ensure you're in the project root
cd /opt/ixom-poc
./scripts/script-name.sh
```

**Docker errors**:
```bash
# Check Docker is running
sudo systemctl status docker

# Check Docker Compose is installed
docker-compose --version
```

---

For detailed deployment instructions, see [DEPLOYMENT.md](../DEPLOYMENT.md)
