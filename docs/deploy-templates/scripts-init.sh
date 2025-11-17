#!/bin/bash
set -e

# FaultMaven Initialization Script
# This script helps set up FaultMaven for first-time deployment

echo "╔══════════════════════════════════════════════════════════╗"
echo "║   FaultMaven Self-Hosted Initialization                 ║"
echo "║   AI-Powered Troubleshooting Platform                   ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================================================
# Step 1: Check Prerequisites
# ============================================================================

echo "📋 Checking prerequisites..."
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    echo "   Install from: https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}✅ Docker installed:${NC} $(docker --version)"

# Check Docker Compose
if ! command -v docker compose &> /dev/null && ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    echo "   Install from: https://docs.docker.com/compose/install/"
    exit 1
fi
echo -e "${GREEN}✅ Docker Compose installed${NC}"

echo ""

# ============================================================================
# Step 2: Environment Configuration
# ============================================================================

echo "⚙️  Configuring environment..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "📝 Creating .env from template..."
        cp .env.example .env
        echo -e "${GREEN}✅ Created .env file${NC}"
    else
        echo -e "${RED}❌ .env.example not found${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  .env file already exists${NC}"
    read -p "   Overwrite with template? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cp .env.example .env
        echo -e "${GREEN}✅ Overwrote .env with template${NC}"
    else
        echo "   Keeping existing .env"
    fi
fi

echo ""

# ============================================================================
# Step 3: Validate Configuration
# ============================================================================

echo "🔍 Validating configuration..."
echo ""

# Check JWT_SECRET
if grep -q "please-change-me" .env; then
    echo -e "${YELLOW}⚠️  JWT_SECRET is set to default value${NC}"
    echo "   Generating secure random secret..."

    if command -v openssl &> /dev/null; then
        NEW_SECRET=$(openssl rand -hex 32)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s/JWT_SECRET=.*/JWT_SECRET=$NEW_SECRET/" .env
        else
            # Linux
            sed -i "s/JWT_SECRET=.*/JWT_SECRET=$NEW_SECRET/" .env
        fi
        echo -e "${GREEN}✅ Generated new JWT_SECRET${NC}"
    else
        echo -e "${YELLOW}⚠️  openssl not found - please set JWT_SECRET manually${NC}"
    fi
fi

# Check for LLM API key
HAS_LLM_KEY=false

if grep -E "^OPENAI_API_KEY=.+" .env > /dev/null 2>&1; then
    echo -e "${GREEN}✅ OpenAI API key configured${NC}"
    HAS_LLM_KEY=true
elif grep -E "^ANTHROPIC_API_KEY=.+" .env > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Anthropic API key configured${NC}"
    HAS_LLM_KEY=true
elif grep -E "^FIREWORKS_API_KEY=.+" .env > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Fireworks API key configured${NC}"
    HAS_LLM_KEY=true
fi

if [ "$HAS_LLM_KEY" = false ]; then
    echo -e "${RED}❌ No LLM API key configured${NC}"
    echo ""
    echo "   You must configure ONE of the following in .env:"
    echo "   - OPENAI_API_KEY=sk-..."
    echo "   - ANTHROPIC_API_KEY=sk-ant-..."
    echo "   - FIREWORKS_API_KEY=fw-..."
    echo ""
    echo "   Edit .env and add your API key, then run this script again."
    exit 1
fi

echo ""

# ============================================================================
# Step 4: Check Port Availability
# ============================================================================

echo "🔌 Checking port availability..."
echo ""

# Function to check if port is in use
check_port() {
    local port=$1
    local service=$2

    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 || netstat -an | grep -q ":$port "; then
        echo -e "${YELLOW}⚠️  Port $port ($service) is already in use${NC}"
        return 1
    else
        echo -e "${GREEN}✅ Port $port ($service) is available${NC}"
        return 0
    fi
}

# Extract ports from .env or use defaults
API_PORT=$(grep "^API_PORT=" .env | cut -d '=' -f2)
API_PORT=${API_PORT:-8000}

DASHBOARD_PORT=$(grep "^DASHBOARD_PORT=" .env | cut -d '=' -f2)
DASHBOARD_PORT=${DASHBOARD_PORT:-3000}

check_port $API_PORT "API Gateway"
check_port $DASHBOARD_PORT "Dashboard"
check_port 6379 "Redis"

echo ""

# ============================================================================
# Step 5: Create Required Directories
# ============================================================================

echo "📁 Creating required directories..."
echo ""

mkdir -p configs
mkdir -p scripts

echo -e "${GREEN}✅ Directories created${NC}"
echo ""

# ============================================================================
# Step 6: Summary
# ============================================================================

echo "╔══════════════════════════════════════════════════════════╗"
echo "║   Configuration Summary                                  ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "   API Gateway:    http://localhost:$API_PORT"
echo "   Dashboard:      http://localhost:$DASHBOARD_PORT"
echo "   API Docs:       http://localhost:$API_PORT/docs"
echo "   Capabilities:   http://localhost:$API_PORT/v1/meta/capabilities"
echo ""

# ============================================================================
# Step 7: Deploy Option
# ============================================================================

echo "🚀 Ready to deploy FaultMaven!"
echo ""
read -p "Start services now? (Y/n): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    echo ""
    echo "Starting FaultMaven services..."
    echo ""

    docker compose pull
    docker compose up -d

    echo ""
    echo "Waiting for services to start..."
    sleep 10

    # Health check
    echo ""
    echo "Checking service health..."

    if curl -sf http://localhost:$API_PORT/health > /dev/null; then
        echo -e "${GREEN}✅ API Gateway is healthy${NC}"
    else
        echo -e "${YELLOW}⚠️  API Gateway not responding (may need more time)${NC}"
    fi

    echo ""
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║   FaultMaven Deployed Successfully!                      ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo ""
    echo "Access your instance at:"
    echo "  • Dashboard: http://localhost:$DASHBOARD_PORT"
    echo "  • API: http://localhost:$API_PORT"
    echo ""
    echo "Next steps:"
    echo "  1. Install the browser extension (faultmaven-copilot)"
    echo "  2. Configure extension to use: http://localhost:$API_PORT"
    echo "  3. Upload documents to Knowledge Base via dashboard"
    echo "  4. Start troubleshooting!"
    echo ""
    echo "View logs: docker compose logs -f"
    echo "Stop services: docker compose down"
    echo ""
else
    echo ""
    echo "Configuration complete! Run when ready:"
    echo "  docker compose up -d"
    echo ""
fi
