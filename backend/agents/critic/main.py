"""Critic agent FastAPI app."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import uvicorn
from agents.base_agent import create_agent_app
from agents.critic.executor import CriticExecutor
from shared.config import CRITIC_PORT

app = create_agent_app(
    agent_card_path=Path(__file__).parent / "agent_card.json",
    executor=CriticExecutor(),
    agent_name="critic",
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=CRITIC_PORT)
