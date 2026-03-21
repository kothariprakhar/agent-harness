.PHONY: setup run test frontend start-all stop

# Install Python dependencies
setup:
	cd backend && pip install -r requirements.txt

# Start all backend services
run:
	bash scripts/start_all.sh

# Run a test prompt
test:
	bash scripts/seed_test.sh

# Install frontend dependencies
frontend-setup:
	cd frontend && npm install

# Start frontend dev server
frontend:
	cd frontend && npm run dev

# Start everything (backend + frontend)
start-all:
	@echo "Starting backend..."
	bash scripts/start_all.sh &
	@sleep 5
	@echo "Starting frontend..."
	cd frontend && npm run dev

# Check health of all services
health:
	@echo "Gateway:"; curl -s http://localhost:8000/api/health | python -m json.tool 2>/dev/null || echo "  DOWN"
	@echo "Orchestrator:"; curl -s http://localhost:8010/health | python -m json.tool 2>/dev/null || echo "  DOWN"
	@echo "Researcher:"; curl -s http://localhost:8011/health | python -m json.tool 2>/dev/null || echo "  DOWN"
	@echo "Writer:"; curl -s http://localhost:8012/health | python -m json.tool 2>/dev/null || echo "  DOWN"
	@echo "Critic:"; curl -s http://localhost:8013/health | python -m json.tool 2>/dev/null || echo "  DOWN"
	@echo "Data Analyst:"; curl -s http://localhost:8014/health | python -m json.tool 2>/dev/null || echo "  DOWN"
