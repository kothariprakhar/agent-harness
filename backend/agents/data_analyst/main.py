"""Data Analyst agent FastAPI app."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import uvicorn
from agents.base_agent import create_agent_app
from agents.data_analyst.executor import DataAnalystExecutor
from shared.config import DATA_ANALYST_PORT

app = create_agent_app(
    agent_card_path=Path(__file__).parent / "agent_card.json",
    executor=DataAnalystExecutor(),
    agent_name="data_analyst",
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=DATA_ANALYST_PORT)
