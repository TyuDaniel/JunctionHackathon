#!/bin/bash

# TASCO - Trip-Aware Smart Charging Orchestrator
# All-in-one startup script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Usage information
show_usage() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  TASCO - Smart Charging Orchestrator  ${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo "Usage: ./start.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --server-only    Start server only (default)"
    echo "  --demo           Setup demo data and train ML model"
    echo "  --test-session   Run a test charging session"
    echo "  --full           Complete setup: server + demo + test"
    echo "  --no-venv        Skip virtual environment (use system Python)"
    echo "  --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./start.sh                  # Start server"
    echo "  ./start.sh --full           # Full demo setup"
    echo "  ./start.sh --demo           # Setup demo data only"
    echo "  ./start.sh --no-venv        # Use system Python"
    echo ""
}

# Parse arguments
MODE="server"
USE_VENV=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --server-only)
            MODE="server"
            shift
            ;;
        --demo)
            MODE="demo"
            shift
            ;;
        --test-session)
            MODE="test"
            shift
            ;;
        --full)
            MODE="full"
            shift
            ;;
        --no-venv)
            USE_VENV=false
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_usage
            exit 1
            ;;
    esac
done

# Header
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  TASCO - Smart Charging Orchestrator  ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
echo -e "${GREEN}✓${NC} Python ${PYTHON_VERSION} found"

# Warn about Python 3.13
if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 13 ]; then
    echo -e "${YELLOW}⚠${NC}  Python 3.13+ detected - some packages may need to build from source"
    echo -e "${YELLOW}   If installation fails, try Python 3.11 or 3.12${NC}"
fi

# Check if we're in the project directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Error: requirements.txt not found. Please run this script from the project root.${NC}"
    exit 1
fi

# Setup virtual environment
if [ "$USE_VENV" = true ]; then
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv venv
        echo -e "${GREEN}✓${NC} Virtual environment created"
    else
        echo -e "${GREEN}✓${NC} Virtual environment exists"
    fi

    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source venv/bin/activate
fi

# Install/update dependencies
echo -e "${YELLOW}Installing dependencies (this may take a few minutes)...${NC}"
echo ""

# Upgrade pip silently
pip install --upgrade pip > /dev/null 2>&1

# Try installing with prefer-binary first (faster, no compilation needed)
echo -e "${YELLOW}Attempting to install pre-built packages...${NC}"
if pip install --prefer-binary -r requirements.txt 2>&1 | tee /tmp/pip_install.log | grep -i "error\|failed" > /dev/null; then
    echo -e "${YELLOW}Some packages need to build from source, this may take longer...${NC}"
    echo -e "${YELLOW}(If this fails, you may need build tools installed)${NC}"
    if ! pip install -r requirements.txt; then
        echo ""
        echo -e "${RED}✗${NC} Failed to install dependencies"
        echo -e "${YELLOW}This usually means missing build tools.${NC}"
        echo -e "${YELLOW}Quick fix: Use Python 3.11 or 3.12 instead of 3.13${NC}"
        echo ""
        exit 1
    fi
fi

echo -e "${GREEN}✓${NC} Dependencies installed successfully"

# Check if database exists
if [ -f "tasco.db" ]; then
    echo -e "${GREEN}✓${NC} Database found"
else
    echo -e "${YELLOW}ℹ${NC} Database will be created on first run"
fi

echo ""

# Function to wait for server to be ready
wait_for_server() {
    echo -e "${YELLOW}Waiting for server to start...${NC}"
    for i in {1..30}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} Server is ready"
            return 0
        fi
        sleep 1
    done
    echo -e "${RED}✗${NC} Server failed to start"
    return 1
}

# Function to setup demo data
setup_demo() {
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}Setting up demo environment...${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""

    echo -e "${YELLOW}Step 1/2: Generating demo data (30 days)...${NC}"
    RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/demo/generate-data?days=30")
    if echo "$RESPONSE" | grep -q "success"; then
        echo -e "${GREEN}✓${NC} Demo data generated"
        echo "$RESPONSE" | python3 -m json.tool 2>/dev/null | head -20
    else
        echo -e "${RED}✗${NC} Failed to generate demo data"
        echo "$RESPONSE"
    fi
    echo ""

    echo -e "${YELLOW}Step 2/2: Training ML forecasting model...${NC}"
    RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/forecasts/train")
    if echo "$RESPONSE" | grep -q "success"; then
        echo -e "${GREEN}✓${NC} ML model trained"
        echo "$RESPONSE" | python3 -m json.tool 2>/dev/null
    else
        echo -e "${RED}✗${NC} Failed to train model"
        echo "$RESPONSE"
    fi
    echo ""

    echo -e "${GREEN}✓ Demo environment ready!${NC}"
    echo ""
}

# Function to run test session
test_session() {
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}Testing charging session...${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""

    RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/sessions/start" \
      -H "Content-Type: application/json" \
      -d '{
        "driver": {
          "did": "did:denso:driver:demo001",
          "credentials": ["Employee:TechCorp"],
          "preferences": {
            "priority": "cost",
            "carbon_conscious": true
          },
          "allowed_sites": ["site_hq"]
        },
        "vehicle": {
          "did": "did:denso:vehicle:demo001",
          "battery_capacity_kwh": 75,
          "nominal_consumption_wh_per_km": 180,
          "max_charge_power_kw": 150,
          "current_soc_percent": 35
        },
        "charger": {
          "did": "did:denso:charger:site_hq_chr01",
          "site_id": "site_hq",
          "max_power_kw": 150,
          "location": {"lat": 60.1699, "lon": 24.9384},
          "current_availability": true,
          "current_tariff_eur_per_kwh": 0.35
        },
        "trip": {
          "distance_km": 120,
          "departure_time": "2025-11-15T20:00:00Z"
        }
      }')

    if echo "$RESPONSE" | grep -q "session_id"; then
        echo -e "${GREEN}✓${NC} Session created successfully"
        echo "$RESPONSE" | python3 -m json.tool 2>/dev/null
    else
        echo -e "${RED}✗${NC} Failed to create session"
        echo "$RESPONSE"
    fi
    echo ""
}

# Execute based on mode
case $MODE in
    server)
        echo -e "${BLUE}========================================${NC}"
        echo -e "${GREEN}Starting TASCO server...${NC}"
        echo -e "${BLUE}========================================${NC}"
        echo ""
        echo -e "📍 API Server: ${GREEN}http://localhost:8000${NC}"
        echo -e "📚 Documentation: ${GREEN}http://localhost:8000/docs${NC}"
        echo -e "🔧 Alternative docs: ${GREEN}http://localhost:8000/redoc${NC}"
        echo ""
        echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
        echo ""
        python -m backend.main
        ;;

    demo)
        # Start server in background
        echo -e "${YELLOW}Starting server in background...${NC}"
        python -m backend.main > /dev/null 2>&1 &
        SERVER_PID=$!

        if wait_for_server; then
            setup_demo
            echo -e "${CYAN}Server running at: ${GREEN}http://localhost:8000/docs${NC}"
            echo -e "${YELLOW}To stop: kill $SERVER_PID${NC}"
        else
            kill $SERVER_PID 2>/dev/null
            exit 1
        fi
        ;;

    test)
        # Start server in background
        echo -e "${YELLOW}Starting server in background...${NC}"
        python -m backend.main > /dev/null 2>&1 &
        SERVER_PID=$!

        if wait_for_server; then
            test_session
            echo -e "${CYAN}Server running at: ${GREEN}http://localhost:8000/docs${NC}"
            echo -e "${YELLOW}To stop: kill $SERVER_PID${NC}"
        else
            kill $SERVER_PID 2>/dev/null
            exit 1
        fi
        ;;

    full)
        # Start server in background
        echo -e "${YELLOW}Starting server in background...${NC}"
        python -m backend.main > /dev/null 2>&1 &
        SERVER_PID=$!

        if wait_for_server; then
            setup_demo
            sleep 2
            test_session

            echo -e "${BLUE}========================================${NC}"
            echo -e "${GREEN}✓ Full demo setup complete!${NC}"
            echo -e "${BLUE}========================================${NC}"
            echo ""
            echo -e "📍 API Server: ${GREEN}http://localhost:8000${NC}"
            echo -e "📚 Documentation: ${GREEN}http://localhost:8000/docs${NC}"
            echo ""
            echo -e "Try these commands:"
            echo -e "  ${CYAN}curl http://localhost:8000/api/v1/chargers${NC}"
            echo -e "  ${CYAN}curl http://localhost:8000/api/v1/sites${NC}"
            echo -e "  ${CYAN}curl http://localhost:8000/api/v1/sites/site_hq/analytics${NC}"
            echo ""
            echo -e "${YELLOW}Server PID: $SERVER_PID${NC}"
            echo -e "${YELLOW}To stop: kill $SERVER_PID${NC}"
        else
            kill $SERVER_PID 2>/dev/null
            exit 1
        fi
        ;;
esac
