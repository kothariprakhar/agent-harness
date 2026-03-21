"""Centralized configuration for all agents and the gateway."""

import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Rate limits for Gemini free tier
GEMINI_RPM_LIMIT = int(os.getenv("GEMINI_RPM_LIMIT", "10"))
GEMINI_RPD_LIMIT = int(os.getenv("GEMINI_RPD_LIMIT", "250"))

# Agent ports
GATEWAY_PORT = 8000
ORCHESTRATOR_PORT = 8010
RESEARCHER_PORT = 8011
WRITER_PORT = 8012
CRITIC_PORT = 8013
DATA_ANALYST_PORT = 8014

AGENT_PORTS = {
    "orchestrator": ORCHESTRATOR_PORT,
    "researcher": RESEARCHER_PORT,
    "writer": WRITER_PORT,
    "critic": CRITIC_PORT,
    "data_analyst": DATA_ANALYST_PORT,
}

WORKER_AGENT_URLS = {
    name: f"http://localhost:{port}"
    for name, port in AGENT_PORTS.items()
    if name != "orchestrator"
}

# Evaluation thresholds
CITATION_ACCURACY_THRESHOLD = 0.85
CLAIM_GROUNDING_THRESHOLD = 0.80
INTERNAL_CONSISTENCY_THRESHOLD = 1.0
AUDIENCE_ALIGNMENT_THRESHOLD = 0.70
COMPLETENESS_THRESHOLD = 0.60
OVERALL_SCORE_THRESHOLD = 0.80
MAX_REVISION_CYCLES = 3

# Web search config
MAX_SEARCH_RESULTS = 5
MAX_PAGE_CONTENT_LENGTH = 8000  # chars per fetched page
REQUEST_TIMEOUT = 15  # seconds for web requests
