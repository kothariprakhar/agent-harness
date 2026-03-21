"""Researcher agent FastAPI app."""

import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import uvicorn
from agents.base_agent import create_agent_app
from agents.researcher.executor import ResearcherExecutor
from shared.config import RESEARCHER_PORT

app = create_agent_app(
    agent_card_path=Path(__file__).parent / "agent_card.json",
    executor=ResearcherExecutor(),
    agent_name="researcher",
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=RESEARCHER_PORT)
