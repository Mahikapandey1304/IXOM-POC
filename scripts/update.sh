#!/bin/bash
# IXOM-POC Update Script
# Updates the application to the latest version from Git

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}IXOM-POC Update Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Pull latest changes from Git
echo -e "${YELLOW}Pulling latest changes from Git...${NC}"
git pull origin main
echo -e "${GREEN}✓ Git pull completed${NC}"
echo ""

# Stop containers
echo -e "${YELLOW}Stopping containers...${NC}"
docker-compose down
echo ""

# Rebuild image
echo -e "${YELLOW}Rebuilding Docker image...${NC}"
docker-compose build --no-cache
echo ""

# Start containers
echo -e "${YELLOW}Starting containers...${NC}"
docker-compose up -d
echo ""

# Wait for health check
echo -e "${YELLOW}Waiting for health check...${NC}"
sleep 15

# Check status
docker-compose ps
echo ""

echo -e "${GREEN}✓ Update completed successfully!${NC}"
echo ""
echo "View logs: docker-compose logs -f"
