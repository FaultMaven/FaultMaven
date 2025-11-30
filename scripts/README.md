# FaultMaven Development Scripts

This directory contains automation scripts for common FaultMaven development tasks.

## Scripts Overview

| Script | Purpose |
|--------|---------|
| `health_check.sh` | Check health status of all microservices |
| `api_test.sh` | Test core API flows (auth, cases, chat) |
| `fm_dev.py` | Python CLI for development tasks |
| `kb_manager.py` | Knowledge Base management CLI |

## Quick Start

```bash
# Make scripts executable
chmod +x *.sh *.py

# Check service health
./health_check.sh

# Run API tests
./api_test.sh http://localhost:8000 test@example.com password123

# Use development helper
python fm_dev.py health
python fm_dev.py services

# Manage knowledge base
python kb_manager.py search "database timeout"
```

## health_check.sh

Checks health endpoints for all FaultMaven services.

```bash
# Basic usage (default: localhost:8000)
./health_check.sh

# Custom URL
./health_check.sh http://api.faultmaven.local:8000

# Also check direct service ports
./health_check.sh http://localhost:8000 --direct
```

## api_test.sh

Tests complete API flows including authentication, case creation, and agent chat.

```bash
# Basic usage
./api_test.sh

# With custom credentials
./api_test.sh http://localhost:8000 user@example.com mypassword
```

**Tests performed:**
1. User registration
2. User login
3. Create troubleshooting case
4. Retrieve case
5. List cases
6. Chat with AI agent
7. Knowledge base search
8. Capabilities discovery

## fm_dev.py

Python development helper for common tasks.

```bash
# Check service health
python fm_dev.py health

# View service logs
python fm_dev.py logs agent-service
python fm_dev.py logs all --tail 50

# Rebuild a service
python fm_dev.py rebuild knowledge-service

# Open shell in container
python fm_dev.py shell case-service

# Database access
python fm_dev.py db-shell --service case-service
python fm_dev.py redis-cli

# Run tests/linting
python fm_dev.py test auth-service
python fm_dev.py lint agent-service

# Service management
python fm_dev.py up --build
python fm_dev.py down
python fm_dev.py status

# Show info
python fm_dev.py services
python fm_dev.py env
```

**Environment variables:**
- `FM_DEPLOY_DIR`: Path to faultmaven-deploy directory
- `FM_COMPOSE_FILE`: Docker compose filename (default: docker-compose.yml)

## kb_manager.py

Knowledge Base management CLI for uploading and searching documents.

```bash
# Upload a document
python kb_manager.py upload runbook.md --title "Database Runbook" --type playbook

# Search the knowledge base
python kb_manager.py search "connection timeout" --limit 10

# List all documents
python kb_manager.py list

# Check document processing status
python kb_manager.py status doc_abc123

# Delete a document
python kb_manager.py delete doc_abc123

# Bulk upload from directory
python kb_manager.py bulk-upload ./docs --type playbook --tags "ops,database"

# Export KB metadata
python kb_manager.py export -o kb_export.json
```

**Authentication options:**
```bash
# Via environment variables
export FM_API_URL=http://localhost:8000
export FM_ACCESS_TOKEN=your-token
# or
export FM_EMAIL=user@example.com
export FM_PASSWORD=password

# Via command line
python kb_manager.py --url http://localhost:8000 --token xxx search "query"
python kb_manager.py --email user@example.com --password pass search "query"

# Via config file (~/.faultmaven/config.json)
{
  "access_token": "your-token"
}
```

## Integration with CI/CD

These scripts can be used in CI/CD pipelines:

```yaml
# GitHub Actions example
jobs:
  test:
    steps:
      - name: Start services
        run: docker-compose up -d

      - name: Wait for services
        run: sleep 30

      - name: Health check
        run: ./scripts/health_check.sh

      - name: API tests
        run: ./scripts/api_test.sh http://localhost:8000 ci@test.com testpass
```

## Troubleshooting

**Services not responding:**
```bash
# Check container status
docker-compose ps

# View logs
./fm_dev.py logs all

# Restart services
./fm_dev.py down && ./fm_dev.py up --build
```

**Authentication issues:**
```bash
# Check environment variables
python fm_dev.py env

# Verify JWT secret is set
echo $FM_JWT_SECRET
```

**Knowledge base empty:**
```bash
# Check ChromaDB
docker-compose logs chromadb

# Check job worker (processes uploads)
docker-compose logs job-worker
```
