# IXOM-POC Deployment Guide for Digital Ocean

Complete guide for deploying IXOM-POC to a Digital Ocean droplet with Docker, Nginx reverse proxy, and SSL certificate.

---

## Prerequisites

- **Digital Ocean Droplet** (minimum 2GB RAM, 1 vCPU recommended)
- **Domain**: `gowideai.com` configured in Digital Ocean DNS
- **SSH Access** to your droplet
- **OpenAI API Key** with GPT-4o access

---

## Quick Start (TL;DR)

```bash
# On your droplet
cd /opt
git clone https://github.com/Mahikapandey1304/IXOM-POC.git ixom-poc
cd ixom-poc

# Configure environment
cp .env.example .env
nano .env  # Add your OPENAI_API_KEY

# Run deployment script
chmod +x scripts/*.sh
./scripts/deploy.sh

# Configure Nginx (see Step 4 below)
# Install SSL certificate (see Step 5 below)
```

---

## Detailed Deployment Steps

### Step 1: Configure DNS Subdomain

**1.1** Log into **Digital Ocean Dashboard** → **Networking** → **Domains**

**1.2** Click on **gowideai.com**

**1.3** Add new A record:
- **Type**: A
- **Hostname**: `ixom`
- **Will Direct To**: Select your droplet
- **TTL**: 3600

**1.4** Verify DNS propagation (wait 5-30 minutes):
```bash
nslookup ixom.gowideai.com
# Should return your droplet's IP
```

---

### Step 2: Prepare Droplet

**2.1** SSH into your droplet:
```bash
ssh root@YOUR_DROPLET_IP
```

**2.2** Update system:
```bash
sudo apt update && sudo apt upgrade -y
```

**2.3** Install Docker:
```bash
# Install dependencies
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Add Docker repository
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Verify
docker --version
```

**2.4** Install Docker Compose:
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

**2.5** Install Nginx:
```bash
sudo apt install -y nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

**2.6** Configure firewall:
```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
sudo ufw status
```

---

### Step 3: Deploy Application

**3.1** Clone repository:
```bash
cd /opt
git clone https://github.com/Mahikapandey1304/IXOM-POC.git ixom-poc
cd ixom-poc
```

**3.2** Configure environment:
```bash
# Copy example file
cp .env.example .env

# Edit with your OpenAI API key
nano .env
```

Add your actual API key:
```env
OPENAI_API_KEY=sk-proj-YOUR_ACTUAL_KEY_HERE
DEFAULT_MODEL=gpt-4o
TEMPERATURE=0
```

Save: `Ctrl+O`, Enter, `Ctrl+X`

**3.3** Make scripts executable:
```bash
chmod +x scripts/*.sh
```

**3.4** Run deployment:
```bash
./scripts/deploy.sh
```

This will:
- Create necessary directories
- Build Docker image
- Start containers
- Set up health checks

**3.5** Verify container is running:
```bash
docker-compose ps
docker-compose logs -f
```

Should show container status as "Up (healthy)"

---

### Step 4: Configure Nginx Reverse Proxy

**4.1** Copy Nginx configuration:
```bash
sudo cp nginx/ixom.gowideai.com.conf /etc/nginx/sites-available/ixom.gowideai.com
```

**4.2** Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/ixom.gowideai.com /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Remove default site
```

**4.3** Test configuration:
```bash
sudo nginx -t
```

Should output: "syntax is ok" and "test is successful"

**4.4** Reload Nginx:
```bash
sudo systemctl reload nginx
```

---

### Step 5: Install SSL Certificate

**5.1** Install Certbot:
```bash
sudo apt install -y certbot python3-certbot-nginx
```

**5.2** Obtain SSL certificate:
```bash
sudo certbot --nginx -d ixom.gowideai.com
```

Follow prompts:
- Enter email address
- Agree to Terms of Service
- Choose whether to share email with EFF

Certbot will automatically:
- Obtain certificate from Let's Encrypt
- Configure Nginx for HTTPS
- Set up automatic renewal

**5.3** Test automatic renewal:
```bash
sudo certbot renew --dry-run
```

**5.4** Verify SSL is working:
```bash
sudo systemctl reload nginx
```

Visit: **https://ixom.gowideai.com**

Should see:
- ✅ Streamlit UI loads
- ✅ Green padlock (secure HTTPS)
- ✅ No certificate warnings

---

### Step 6: Set Up Auto-Restart on Reboot

**6.1** Create systemd service:
```bash
sudo nano /etc/systemd/system/ixom-validator.service
```

Paste:
```ini
[Unit]
Description=IXOM Validator Docker Compose Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/ixom-poc
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Save: `Ctrl+O`, Enter, `Ctrl+X`

**6.2** Enable service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ixom-validator.service
sudo systemctl start ixom-validator.service
```

**6.3** Test auto-restart:
```bash
sudo reboot
```

Wait 2-3 minutes, then SSH back in and verify:
```bash
docker-compose -f /opt/ixom-poc/docker-compose.yml ps
```

---

### Step 7: Set Up Monitoring and Backups

**7.1** View application status:
```bash
cd /opt/ixom-poc
./scripts/monitor.sh
```

**7.2** Set up automatic backups:
```bash
# Edit crontab
sudo crontab -e

# Add this line (runs backup daily at 2 AM)
0 2 * * * /opt/ixom-poc/scripts/backup.sh >> /var/log/ixom-backup.log 2>&1
```

**7.3** Test backup manually:
```bash
./scripts/backup.sh
```

---

## Updating the Application

When you make changes to the code:

**Option 1: Automated update script**
```bash
cd /opt/ixom-poc
./scripts/update.sh
```

**Option 2: Manual update**
```bash
cd /opt/ixom-poc
git pull origin main
docker-compose down
docker-compose build --no-cache
docker-compose up -d
docker-compose logs -f
```

---

## Monitoring and Maintenance

### View Logs
```bash
# Application logs
docker-compose logs -f

# Nginx access logs
sudo tail -f /var/log/nginx/ixom.access.log

# Nginx error logs
sudo tail -f /var/log/nginx/ixom.error.log

# System logs
journalctl -u ixom-validator.service -f
```

### Check Status
```bash
# Quick status
docker-compose ps

# Detailed monitoring
./scripts/monitor.sh

# Container resource usage
docker stats ixom-validator

# System resources
htop
```

### Restart Services
```bash
# Restart application
docker-compose restart

# Restart Nginx
sudo systemctl restart nginx

# Restart both
docker-compose restart && sudo systemctl restart nginx
```

---

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs

# Common issues:
# 1. Missing .env file → cp .env.example .env
# 2. Invalid API key → check OPENAI_API_KEY in .env
# 3. Port conflict → check if port 8501 is in use
```

### 502 Bad Gateway
```bash
# Check if container is running
docker-compose ps

# Check if app is listening on 8501
curl http://localhost:8501

# Restart everything
docker-compose restart
sudo systemctl restart nginx
```

### SSL Certificate Issues
```bash
# Check certificate status
sudo certbot certificates

# Renew certificate manually
sudo certbot renew

# Check Nginx configuration
sudo nginx -t
```

### High Memory Usage
```bash
# Check usage
docker stats

# Restart container to free memory
docker-compose restart

# Consider upgrading droplet if consistently high
```

### DNS Not Resolving
```bash
# Check DNS propagation
nslookup ixom.gowideai.com

# Wait 30-60 minutes for full propagation
# Clear local DNS cache on your machine
```

---

## Security Best Practices

### 1. Secure SSH
```bash
# Change default SSH port
sudo nano /etc/ssh/sshd_config
# Change: Port 22 → Port 2222

# Restart SSH
sudo systemctl restart sshd

# Update firewall
sudo ufw allow 2222/tcp
sudo ufw delete allow OpenSSH
```

### 2. Install Fail2Ban
```bash
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 3. Enable Automatic Security Updates
```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

### 4. Rotate API Keys
- Rotate OpenAI API key quarterly
- Update `.env` file and restart: `docker-compose restart`

### 5. Monitor Logs Regularly
```bash
# Check for suspicious activity
sudo tail -f /var/log/nginx/ixom.access.log
```

---

## Performance Optimization

### Resource Limits
Edit `docker-compose.yml` to adjust:
```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'      # Increase for better performance
      memory: 2G       # Increase if processing large PDFs
```

### Nginx Tuning
For high traffic, edit `/etc/nginx/nginx.conf`:
```nginx
worker_processes auto;
worker_connections 1024;
```

---

## Cost Estimation

**Digital Ocean Droplet (2GB RAM, 1 vCPU)**: $12-18/month  
**Domain (gowideai.com)**: Already owned  
**SSL Certificate**: Free (Let's Encrypt)  
**Backups (Spaces)**: Optional, ~$5/month  
**OpenAI API Usage**: Variable, typically $10-50/month depending on usage

**Total**: ~$22-73/month

---

## Support

### Useful Commands Reference
```bash
# Application
./scripts/deploy.sh      # Initial deployment
./scripts/update.sh      # Update application
./scripts/monitor.sh     # View status
./scripts/backup.sh      # Create backup

# Docker
docker-compose ps        # Container status
docker-compose logs -f   # View logs
docker-compose restart   # Restart container
docker-compose down      # Stop container
docker-compose up -d     # Start container

# Nginx
sudo nginx -t            # Test configuration
sudo systemctl reload nginx    # Reload config
sudo tail -f /var/log/nginx/ixom.error.log  # Error logs

# SSL
sudo certbot renew       # Renew certificate
sudo certbot certificates # List certificates

# System
systemctl status ixom-validator.service  # Service status
sudo ufw status          # Firewall status
htop                     # Resource monitor
```

### Health Check URLs
- **Application**: https://ixom.gowideai.com
- **Health endpoint**: https://ixom.gowideai.com/_stcore/health
- **SSL test**: https://www.ssllabs.com/ssltest/analyze.html?d=ixom.gowideai.com

---

## Post-Deployment Checklist

✅ DNS configured for `ixom.gowideai.com`  
✅ Docker and Docker Compose installed  
✅ Application container running and healthy  
✅ Nginx reverse proxy configured  
✅ SSL certificate installed and valid  
✅ Auto-restart on reboot configured  
✅ Firewall configured (ports 22, 80, 443)  ✅ Automatic backups scheduled  
✅ Monitoring script accessible  
✅ Update procedure tested  
✅ Application accessible at https://ixom.gowideai.com  
✅ PDF upload and validation working  
✅ Logs being generated correctly  

---

**Your IXOM-POC application is now live at: https://ixom.gowideai.com** 🚀

For issues or questions, check the logs first: `docker-compose logs -f`
