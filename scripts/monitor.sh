#!/bin/bash
# IXOM-POC Monitoring Script
# Displays current status and health of the application

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

clear
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}IXOM-POC System Monitor${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Date: $(date)"
echo ""

# Container Status
echo -e "${BLUE}Container Status:${NC}"
docker-compose ps
echo ""

# Container Health
echo -e "${BLUE}Container Health:${NC}"
HEALTH=$(docker inspect --format='{{.State.Health.Status}}' ixom-validator 2>/dev/null || echo "N/A")
if [ "$HEALTH" = "healthy" ]; then
    echo -e "${GREEN}✓ Healthy${NC}"
elif [ "$HEALTH" = "unhealthy" ]; then
    echo -e "${YELLOW}⚠ Unhealthy${NC}"
else
    echo -e "${YELLOW}Status: $HEALTH${NC}"
fi
echo ""

# Docker Stats
echo -e "${BLUE}Resource Usage:${NC}"
docker stats --no-stream ixom-validator 2>/dev/null || echo "Container not running"
echo ""

# Disk Usage
echo -e "${BLUE}Disk Usage (Project Directory):${NC}"
du -sh data/ logs/ outputs/ 2>/dev/null || echo "Directories not accessible"
echo ""

# Recent Logs
echo -e "${BLUE}Recent Logs (last 15 lines):${NC}"
docker-compose logs --tail=15 ixom-validator
echo ""

# Nginx Status (if installed)
if command -v nginx &> /dev/null; then
    echo -e "${BLUE}Nginx Status:${NC}"
    systemctl status nginx --no-pager | head -3
    echo ""
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${YELLOW}Commands:${NC}"
echo "  Full logs:       docker-compose logs -f"
echo "  Restart:         docker-compose restart"
echo "  Stop:            docker-compose down"
echo "  Update:          ./scripts/update.sh"
echo ""
