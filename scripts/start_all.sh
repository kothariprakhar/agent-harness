#!/bin/bash
# Start all backend services + frontend
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_DIR/backend"

echo "Starting AgentHarness services..."

# Start worker agents first (they need to be available for Orchestrator discovery)
echo "Starting Researcher agent (port 8011)..."
cd "$BACKEND_DIR" && python -m agents.researcher.main &
PIDS+=($!)

echo "Starting Writer agent (port 8012)..."
cd "$BACKEND_DIR" && python -m agents.writer.main &
PIDS+=($!)

echo "Starting Critic agent (port 8013)..."
cd "$BACKEND_DIR" && python -m agents.critic.main &
PIDS+=($!)

echo "Starting Data Analyst agent (port 8014)..."
cd "$BACKEND_DIR" && python -m agents.data_analyst.main &
PIDS+=($!)

# Wait for workers to start
sleep 3

echo "Starting Orchestrator agent (port 8010)..."
cd "$BACKEND_DIR" && python -m agents.orchestrator.main &
PIDS+=($!)

sleep 2

echo "Starting Gateway (port 8000)..."
cd "$BACKEND_DIR" && python -m gateway.main &
PIDS+=($!)

echo ""
echo "All services started!"
echo "  Gateway:       http://localhost:8000"
echo "  Orchestrator:  http://localhost:8010"
echo "  Researcher:    http://localhost:8011"
echo "  Writer:        http://localhost:8012"
echo "  Critic:        http://localhost:8013"
echo "  Data Analyst:  http://localhost:8014"
echo ""
echo "Press Ctrl+C to stop all services"

# Trap SIGINT to kill all child processes
trap 'echo "Stopping all services..."; kill ${PIDS[@]} 2>/dev/null; exit 0' SIGINT SIGTERM

# Wait for all background processes
wait
