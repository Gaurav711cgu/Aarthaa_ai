#!/usr/bin/env bash

# ==============================================================================
# Artha AI — Production Deployment and Developer Launcher Script
# ==============================================================================
# Resolves dependency gates, builds pipelines, and orchestrates containerized 
# or local services transparently.
# ==============================================================================

set -euo pipefail

# ANSI color codes for premium developer terminal feedback
RED='\033[0,31m'
GREEN='\033[0,32m'
BLUE='\033[0,34m'
CYAN='\033[0,36m'
YELLOW='\033[1,33m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Print decorative banner
echo -e "${CYAN}${BOLD}"
echo "  ================================================================"
echo "    ARTHA AI — ELITE FINTECH ARTIFICIAL INTELLIGENCE PLATFORM     "
echo "  ================================================================"
echo -e "${NC}"

# Script directory resolution
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_help() {
    echo "Usage: ./deploy_local.sh [options]"
    echo ""
    echo "Options:"
    echo "  --stack       Deploy the COMPLETE system inside Docker containers (FastAPI + DB + Redis + Kafka)"
    echo "  --dev         Hybrid Dev: Run DB/Cache in Docker, run FastAPI locally with reload"
    echo "  --offline     Local Bare-metal: Run FastAPI locally using SQLite & in-memory fallbacks"
    echo "  --help, -h    Show this options index"
    echo ""
    echo "If no option is specified, the script automatically checks if Docker is running"
    echo "and defaults to Hybrid Dev (--dev), falling back to Local Bare-metal (--offline)."
}

# Parse input flags
DEPLOY_MODE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --stack)
            DEPLOY_MODE="stack"
            shift
            ;;
        --dev)
            DEPLOY_MODE="dev"
            shift
            ;;
        --offline)
            DEPLOY_MODE="offline"
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown argument: $1"
            show_help
            exit 1
            ;;
    esac
done

# ----------------------------------------------------
# Step 1: Environment Integrity Check (Python & pip)
# ----------------------------------------------------
log_info "Verifying developer environment dependencies..."

if ! command -v python3 &> /dev/null; then
    log_error "Python 3 is required but could not be found. Please install Python 3.9+."
    exit 1
fi

# Determine Python version
PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
log_info "Detected Python version: ${PY_VERSION}"

# ----------------------------------------------------
# Step 2: Virtual Environment Setup
# ----------------------------------------------------
if [ ! -d ".venv" ]; then
    log_info "Creating clean Python virtual environment (.venv)..."
    python3 -m venv .venv
    log_success "Virtual environment established."
fi

# Activate virtual environment
log_info "Activating Python virtual environment..."
source .venv/bin/activate

# Upgrade packaging tools and install requirements
log_info "Installing dependencies from requirements.txt..."
pip install --upgrade pip &> /dev/null || true
pip install -r requirements.txt --quiet
log_success "All python packages installed successfully."

# ----------------------------------------------------
# Step 3: ML Models & Regulatory Vector Compilation
# ----------------------------------------------------
log_info "Validating intelligence pipelines..."

MODEL_FILE="app/models/fraud_model.pkl"
EMBEDDINGS_FILE="app/models/reg_embeddings.json"

if [ ! -f "${MODEL_FILE}" ]; then
    log_warn "FraudSense RandomForest ensemble not compiled. Initiating pipeline training run..."
    PYTHONPATH=. python3 scripts/train_fraud_model.py
    log_success "FraudSense models serialized successfully."
else
    log_info "FraudSense ensemble models verified: OK"
fi

if [ ! -f "${EMBEDDINGS_FILE}" ]; then
    log_warn "RegGuard compliance vector store empty. Initiating section-aware corpus ingestion..."
    PYTHONPATH=. python3 scripts/ingest_regulations.py
    log_success "RegGuard semantic regulatory vector index built successfully."
else
    log_info "RegGuard compliance vector indexes verified: OK"
fi

# ----------------------------------------------------
# Step 4: Infrastructure Check & Orchestration Selection
# ----------------------------------------------------
DOCKER_ACTIVE=false
if command -v docker &> /dev/null; then
    if docker info &> /dev/null; then
        DOCKER_ACTIVE=true
    fi
fi

if [ "${DEPLOY_MODE}" == "" ]; then
    if [ "${DOCKER_ACTIVE}" == "true" ]; then
        DEPLOY_MODE="dev"
        log_info "Docker daemon active. Defaulting to Hybrid Dev mode (--dev)..."
    else
        DEPLOY_MODE="offline"
        log_warn "Docker daemon is offline. Defaulting to Zero-Dependency local fallback mode (--offline)..."
    fi
fi

# Executing orchestration paths
if [ "${DEPLOY_MODE}" == "stack" ]; then
    if [ "${DOCKER_ACTIVE}" == "false" ]; then
        log_error "Docker is not running. Cannot execute complete --stack deployment. Please start Docker first."
        exit 1
    fi
    log_info "Launching the FULL containerized Artha AI ecosystem (FastAPI + pgvector + Redis + Kafka)..."
    docker compose down
    docker compose up --build
    
elif [ "${DEPLOY_MODE}" == "dev" ]; then
    if [ "${DOCKER_ACTIVE}" == "false" ]; then
        log_warn "Docker not available. Falling back to local offline mode..."
        DEPLOY_MODE="offline"
    else
        log_info "Starting backing infrastructure (Postgres, Redis, Kafka) inside Docker Compose..."
        docker compose up postgres redis zookeeper kafka -d
        log_info "Waiting for backing services to pass healthchecks..."
        
        # Simple loop to wait for databases
        MAX_RETRIES=12
        RETRIES=0
        while [ $RETRIES -lt $MAX_RETRIES ]; do
            # Check postgres state inside compose
            PG_STATE=$(docker inspect -f '{{.State.Health.Status}}' artha_postgres 2>/dev/null || echo "unhealthy")
            REDIS_STATE=$(docker inspect -f '{{.State.Health.Status}}' artha_redis 2>/dev/null || echo "unhealthy")
            
            if [ "${PG_STATE}" == "healthy" ] && [ "${REDIS_STATE}" == "healthy" ]; then
                log_success "Backing infrastructure is healthy!"
                break
            fi
            
            log_info "Services booting (Postgres: ${PG_STATE}, Redis: ${REDIS_STATE})... Retrying in 5 seconds."
            sleep 5
            RETRIES=$((RETRIES+1))
        done
        
        if [ $RETRIES -eq $MAX_RETRIES ]; then
            log_warn "Infrastructure check timed out. Proceeding and allowing API gateway to use SQLite fallbacks where needed."
        fi
        
        log_info "Booting local FastAPI gateway in active development hot-reload environment..."
        PYTHONPATH=. uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    fi
fi

if [ "${DEPLOY_MODE}" == "offline" ]; then
    log_info "Initializing bare-metal execution stack..."
    log_info "Database: Local SQLite (artha_local.db)"
    log_info "Cache: Thread-safe in-memory MockRedis dictionary"
    log_info "Event-Streamer: Async MockKafka queue"
    
    echo -e "${YELLOW}${BOLD}Server is running in OFFLINE fallback mode. Zero external container dependency.${NC}"
    log_info "Starting uvicorn server..."
    PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000
fi
