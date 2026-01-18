#!/bin/bash
# ============================================================================
# BlueRadar Intelligence Engine - Run Script
# Real-time Ocean Hazard Monitoring System for Indian Coastal Waters
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Default values
MODE="realtime"
WS_PORT=8765
HTTP_PORT=8080
INTERVAL=60
PLATFORMS="twitter youtube news instagram"
NO_BROWSER=false
VERBOSE=false

# Print banner
print_banner() {
    echo -e "${CYAN}"
    echo "============================================================"
    echo "  ____  _            ____           _            "
    echo " | __ )| |_   _  ___|  _ \ __ _  __| | __ _ _ __ "
    echo " |  _ \| | | | |/ _ \ |_) / _\` |/ _\` |/ _\` | '__|"
    echo " | |_) | | |_| |  __/  _ < (_| | (_| | (_| | |   "
    echo " |____/|_|\__,_|\___|_| \_\__,_|\__,_|\__,_|_|   "
    echo "                                                 "
    echo "  Ocean Hazard Monitoring System v1.0            "
    echo "============================================================"
    echo -e "${NC}"
}

# Print help
print_help() {
    echo -e "${GREEN}Usage:${NC} ./run.sh [OPTIONS]"
    echo ""
    echo -e "${GREEN}Options:${NC}"
    echo "  -m, --mode MODE       Run mode: realtime, demo, or setup (default: realtime)"
    echo "  -p, --port PORT       WebSocket port (default: 8765)"
    echo "  -h, --http PORT       HTTP dashboard port (default: 8080)"
    echo "  -i, --interval SEC    Scrape interval in seconds (default: 60)"
    echo "  --platforms LIST      Platforms to scrape (default: twitter youtube news instagram)"
    echo "  --no-browser          Don't open browser automatically"
    echo "  -v, --verbose         Verbose output"
    echo "  --help                Show this help message"
    echo ""
    echo -e "${GREEN}Modes:${NC}"
    echo "  realtime    Start real-time monitoring with live dashboard"
    echo "  demo        Run demo mode with sample alerts"
    echo "  setup       Install dependencies and setup environment"
    echo "  stop        Stop all running BlueRadar processes"
    echo "  status      Check status of running processes"
    echo ""
    echo -e "${GREEN}Examples:${NC}"
    echo "  ./run.sh                           # Start real-time monitoring"
    echo "  ./run.sh -m demo                   # Run demo mode"
    echo "  ./run.sh -i 120 --no-browser       # 2-minute interval, no browser"
    echo "  ./run.sh --platforms twitter news  # Only Twitter and News"
    echo "  ./run.sh -m stop                   # Stop all processes"
    echo ""
}

# Check dependencies
check_dependencies() {
    echo -e "${BLUE}Checking dependencies...${NC}"

    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Error: Python 3 is not installed${NC}"
        exit 1
    fi

    # Check venv
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
        python3 -m venv venv
    fi

    # Activate venv
    source venv/bin/activate

    # Check required packages
    if ! python3 -c "import websockets, aiohttp" 2>/dev/null; then
        echo -e "${YELLOW}Installing missing packages...${NC}"
        pip install websockets aiohttp python-dotenv --quiet
    fi

    echo -e "${GREEN}Dependencies OK${NC}"
}

# Setup environment
setup_environment() {
    echo -e "${BLUE}Setting up BlueRadar environment...${NC}"

    # Create venv if needed
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv venv
    fi

    # Activate venv
    source venv/bin/activate

    # Install requirements
    echo -e "${YELLOW}Installing requirements...${NC}"
    pip install --upgrade pip --quiet
    pip install -r requirements.txt --quiet
    pip install websockets aiohttp --quiet

    # Check .env file
    if [ ! -f ".env" ]; then
        echo -e "${YELLOW}Creating .env file...${NC}"
        cat > .env << 'EOF'
# BlueRadar Intelligence - Environment Variables
# Keep this file secure and never commit to git

# RapidAPI Twitter241 API Key (500 requests/month on free tier)
RAPIDAPI_KEY=your_rapidapi_key_here

# RapidAPI Instagram120 API Key (for hashtag search)
RAPIDAPI_INSTAGRAM_KEY=your_rapidapi_key_here
EOF
        echo -e "${YELLOW}Please edit .env file with your API keys${NC}"
    fi

    # Create dashboard directory if needed
    if [ ! -d "dashboard" ]; then
        mkdir -p dashboard
    fi

    echo -e "${GREEN}Setup complete!${NC}"
    echo ""
    echo -e "${CYAN}Next steps:${NC}"
    echo "1. Edit .env file with your RapidAPI keys"
    echo "2. Run: ./run.sh"
}

# Start real-time monitoring
start_realtime() {
    echo -e "${BLUE}Starting BlueRadar Real-Time Engine...${NC}"

    # Check dependencies
    check_dependencies

    # Build command
    CMD="python run_realtime.py"
    CMD="$CMD --ws-port $WS_PORT"
    CMD="$CMD --http-port $HTTP_PORT"
    CMD="$CMD --interval $INTERVAL"
    CMD="$CMD --platforms $PLATFORMS"

    if [ "$NO_BROWSER" = true ]; then
        CMD="$CMD --no-browser"
    fi

    echo -e "${CYAN}Configuration:${NC}"
    echo "  WebSocket Port: $WS_PORT"
    echo "  Dashboard Port: $HTTP_PORT"
    echo "  Scrape Interval: ${INTERVAL}s"
    echo "  Platforms: $PLATFORMS"
    echo ""

    # Run
    source venv/bin/activate
    export PYTHONUNBUFFERED=1
    exec $CMD
}

# Start demo mode
start_demo() {
    echo -e "${BLUE}Starting BlueRadar Demo Mode...${NC}"
    check_dependencies
    source venv/bin/activate
    exec python main.py --mode demo
}

# Stop all processes
stop_processes() {
    echo -e "${BLUE}Stopping BlueRadar processes...${NC}"

    pkill -f "python run_realtime.py" 2>/dev/null && echo -e "${GREEN}Stopped real-time engine${NC}" || true
    pkill -f "python main.py" 2>/dev/null && echo -e "${GREEN}Stopped main process${NC}" || true

    echo -e "${GREEN}All processes stopped${NC}"
}

# Check status
check_status() {
    echo -e "${BLUE}BlueRadar Process Status:${NC}"
    echo ""

    if pgrep -f "python run_realtime.py" > /dev/null; then
        echo -e "${GREEN}[RUNNING]${NC} Real-time Engine"
        echo "  PID: $(pgrep -f 'python run_realtime.py')"
    else
        echo -e "${RED}[STOPPED]${NC} Real-time Engine"
    fi

    if pgrep -f "python main.py" > /dev/null; then
        echo -e "${GREEN}[RUNNING]${NC} Main Process"
        echo "  PID: $(pgrep -f 'python main.py')"
    else
        echo -e "${RED}[STOPPED]${NC} Main Process"
    fi

    echo ""

    # Check ports
    if lsof -i :$WS_PORT > /dev/null 2>&1; then
        echo -e "${GREEN}[ACTIVE]${NC} WebSocket on port $WS_PORT"
    else
        echo -e "${RED}[INACTIVE]${NC} WebSocket on port $WS_PORT"
    fi

    if lsof -i :$HTTP_PORT > /dev/null 2>&1; then
        echo -e "${GREEN}[ACTIVE]${NC} Dashboard on port $HTTP_PORT"
    else
        echo -e "${RED}[INACTIVE]${NC} Dashboard on port $HTTP_PORT"
    fi
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--mode)
            MODE="$2"
            shift 2
            ;;
        -p|--port)
            WS_PORT="$2"
            shift 2
            ;;
        -h|--http)
            HTTP_PORT="$2"
            shift 2
            ;;
        -i|--interval)
            INTERVAL="$2"
            shift 2
            ;;
        --platforms)
            PLATFORMS="$2"
            shift 2
            ;;
        --no-browser)
            NO_BROWSER=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            print_banner
            print_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            print_help
            exit 1
            ;;
    esac
done

# Main execution
print_banner

case $MODE in
    realtime)
        start_realtime
        ;;
    demo)
        start_demo
        ;;
    setup)
        setup_environment
        ;;
    stop)
        stop_processes
        ;;
    status)
        check_status
        ;;
    *)
        echo -e "${RED}Unknown mode: $MODE${NC}"
        print_help
        exit 1
        ;;
esac
