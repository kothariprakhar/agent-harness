"""Writer agent FastAPI app."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import uvicorn
from agents.base_agent import create_agent_app
from agents.writer.executor import WriterExecutor
from shared.config import WRITER_PORT

app = create_agent_app(
    agent_card_path=Path(__file__).parent / "agent_card.json",
    executor=WriterExecutor(),
    agent_name="writer",
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=WRITER_PORT)
