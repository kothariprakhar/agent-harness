"""Orchestrator agent FastAPI app."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import uvicorn
from agents.base_agent import create_agent_app
from agents.orchestrator.executor import OrchestratorExecutor
from shared.config import ORCHESTRATOR_PORT

app = create_agent_app(
    agent_card_path=Path(__file__).parent / "agent_card.json",
    executor=OrchestratorExecutor(),
    agent_name="orchestrator",
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=ORCHESTRATOR_PORT)
