#!/bin/bash
# IXOM-POC Backup Script
# Backs up logs, outputs, and data

set -e

# Configuration
BACKUP_DIR="/opt/ixom-backups"
PROJECT_DIR="/opt/ixom-poc"
DATE=$(date +%Y%m%d_%H%M%S)

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}IXOM-POC Backup Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup logs
echo -e "${YELLOW}Backing up logs...${NC}"
if [ -d "$PROJECT_DIR/logs" ]; then
    tar -czf $BACKUP_DIR/logs_$DATE.tar.gz -C $PROJECT_DIR logs/
    echo -e "${GREEN}✓ Logs backed up${NC}"
fi

# Backup outputs
echo -e "${YELLOW}Backing up outputs...${NC}"
if [ -d "$PROJECT_DIR/outputs" ]; then
    tar -czf $BACKUP_DIR/outputs_$DATE.tar.gz -C $PROJECT_DIR outputs/
    echo -e "${GREEN}✓ Outputs backed up${NC}"
fi

# Backup data
echo -e "${YELLOW}Backing up data...${NC}"
if [ -d "$PROJECT_DIR/data" ]; then
    tar -czf $BACKUP_DIR/data_$DATE.tar.gz -C $PROJECT_DIR data/
    echo -e "${GREEN}✓ Data backed up${NC}"
fi

# Backup environment file (without exposing secrets)
echo -e "${YELLOW}Backing up configuration...${NC}"
if [ -f "$PROJECT_DIR/.env" ]; then
    # Create sanitized copy (mask API key)
    sed 's/sk-[a-zA-Z0-9_-]*/sk-***MASKED***/g' $PROJECT_DIR/.env > $BACKUP_DIR/env_$DATE.txt
    echo -e "${GREEN}✓ Configuration backed up (sanitized)${NC}"
fi

# Clean up old backups (keep last 7 days)
echo -e "${YELLOW}Cleaning up old backups...${NC}"
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
find $BACKUP_DIR -name "*.txt" -mtime +7 -delete
echo -e "${GREEN}✓ Old backups cleaned${NC}"

# Show backup summary
echo ""
echo -e "${GREEN}Backup completed: $DATE${NC}"
echo ""
echo "Backup location: $BACKUP_DIR"
echo "Backup files:"
ls -lh $BACKUP_DIR/*$DATE* 2>/dev/null || echo "No backups created"
echo ""
