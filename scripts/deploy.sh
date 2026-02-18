#!/bin/bash
# IXOM-POC Deployment Script for Digital Ocean Droplet
# This script automates the deployment process

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}IXOM-POC Deployment Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo -e "${YELLOW}Please create .env file from .env.example:${NC}"
    echo "  cp .env.example .env"
    echo "  nano .env  # Add your OPENAI_API_KEY"
    exit 1
fi

# Check if OPENAI_API_KEY is set
if ! grep -q "OPENAI_API_KEY=sk-" .env; then
    echo -e "${RED}Error: OPENAI_API_KEY not configured in .env file!${NC}"
    echo -e "${YELLOW}Please edit .env and add your OpenAI API key${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Environment configuration verified${NC}"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed!${NC}"
    echo "Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed!${NC}"
    echo "Please install Docker Compose first."
    exit 1
fi

echo -e "${GREEN}✓ Docker and Docker Compose are installed${NC}"
echo ""

# Create necessary directories
echo -e "${YELLOW}Creating required directories...${NC}"
mkdir -p data/specs data/certificates logs outputs/structured_json
chmod -R 755 data logs outputs
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Stop existing containers
echo -e "${YELLOW}Stopping existing containers (if any)...${NC}"
docker-compose down 2>/dev/null || true
echo ""

# Build Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker-compose build --no-cache
echo -e "${GREEN}✓ Docker image built successfully${NC}"
echo ""

# Start containers
echo -e "${YELLOW}Starting containers...${NC}"
docker-compose up -d
echo -e "${GREEN}✓ Containers started${NC}"
echo ""

# Wait for health check
echo -e "${YELLOW}Waiting for application to be healthy...${NC}"
sleep 10

# Check container status
if docker-compose ps | grep -q "Up (healthy)"; then
    echo -e "${GREEN}✓ Application is healthy and running!${NC}"
else
    echo -e "${YELLOW}⚠ Application is starting... (health check in progress)${NC}"
fi
echo ""

# Display status
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Summary${NC}"
echo -e "${GREEN}========================================${NC}"
docker-compose ps
echo ""

echo -e "${GREEN}✓ Deployment completed successfully!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Configure Nginx reverse proxy (see DEPLOYMENT.md)"
echo "  2. Set up SSL certificate with Certbot"
echo "  3. Configure your subdomain DNS"
echo ""
echo -e "${YELLOW}Useful commands:${NC}"
echo "  View logs:     docker-compose logs -f"
echo "  Stop app:      docker-compose down"
echo "  Restart app:   docker-compose restart"
echo "  Update app:    ./scripts/update.sh"
echo ""
