# IXOM-POC Quick Deployment Guide

Deploy IXOM-POC to your Digital Ocean droplet in **15 minutes**.

---

## What You Need

- ✅ Digital Ocean droplet (2GB+ RAM recommended)
- ✅ Domain: `gowideai.com` (already have)
- ✅ OpenAI API key
- ✅ SSH access to droplet

---

## 5-Step Deployment

### 1️⃣ Clone Repository on Droplet

```bash
ssh root@YOUR_DROPLET_IP
cd /opt
git clone https://github.com/Mahikapandey1304/IXOM-POC.git ixom-poc
cd ixom-poc
```

### 2️⃣ Configure Environment

```bash
cp .env.example .env
nano .env
```

Add your OpenAI API key, save, and exit.

### 3️⃣ Run Automated Setup

```bash
chmod +x scripts/*.sh
./scripts/deploy.sh
```

This installs Docker, builds images, and starts containers.

### 4️⃣ Configure Nginx + SSL

```bash
# Copy nginx config
sudo cp nginx/ixom.gowideai.com.conf /etc/nginx/sites-available/ixom.gowideai.com
sudo ln -s /etc/nginx/sites-available/ixom.gowideai.com /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Test and reload
sudo nginx -t
sudo systemctl reload nginx

# Install SSL certificate
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d ixom.gowideai.com
```

### 5️⃣ Verify Deployment

Visit: **https://ixom.gowideai.com**

Should see Streamlit UI with green padlock! 🎉

---

## What Got Deployed?

- ✅ Docker container running Python 3.11 + Streamlit
- ✅ Nginx reverse proxy with HTTPS
- ✅ Free SSL certificate (auto-renewing)
- ✅ Auto-restart on droplet reboot
- ✅ Health monitoring
- ✅ Automated backups (optional, see DEPLOYMENT.md)

---

## Quick Commands

```bash
# View status
./scripts/monitor.sh

# View logs
docker-compose logs -f

# Update app
./scripts/update.sh

# Restart
docker-compose restart
```

---

## Troubleshooting

**Container won't start?**
```bash
docker-compose logs
# Check .env file has valid OPENAI_API_KEY
```

**502 Bad Gateway?**
```bash
docker-compose ps  # Ensure container is "Up (healthy)"
curl http://localhost:8501  # Test app responds
```

**DNS not working?**
```bash
nslookup ixom.gowideai.com
# Wait 30-60 min for DNS propagation
```

---

## Next Steps

1. Upload test PDFs via UI
2. Set up automatic backups (see DEPLOYMENT.md)
3. Monitor logs: `docker-compose logs -f`
4. Check SSL rating: https://www.ssllabs.com/ssltest/

---

**Full documentation**: [DEPLOYMENT.md](DEPLOYMENT.md)

**Need help?** Check logs first: `docker-compose logs -f`
