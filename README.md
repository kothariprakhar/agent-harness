# AgentHarness

A multi-agent orchestration system that turns a single research prompt into a well-researched, citation-verified article with interactive charts — built on the A2A protocol with quantified anti-hallucination evaluation.

```
Prompt → [Researcher → Data Analyst → Writer ⇄ Critic] → Article + Charts + Evaluation
```

**Key differentiators vs typical multi-agent demos:**
- Every factual claim traces to a verbatim web source quote — the Researcher never invents
- Five distinct quality metrics scored by a dedicated Critic agent, not self-reported
- Visible Writer → Critic → Writer revision loop (up to 3 cycles) with per-issue feedback
- Genuine A2A protocol compliance: agent cards, JSON-RPC 2.0, SSE streaming, task states
- Two types of interactive visuals: Plotly data charts + self-contained HTML concept explainers
- Knowledge Base: upload example articles, pipeline adapts to your writing style

---

## Architecture

```
Browser (Next.js :3000)
       │  WebSocket (Socket.IO) + REST
       ▼
Gateway (FastAPI :8000) ─── /api/kb/* Knowledge Base
       │
       │  A2A JSON-RPC 2.0
       ▼
Orchestrator (:8010) ─── discovers agents via /.well-known/agent-card.json
       │
       ├──▶ Researcher  (:8011)  web search + verbatim-quote fact extraction
       ├──▶ Writer      (:8012)  article drafting + revision
       ├──▶ Critic      (:8013)  5-metric quality evaluation + hallucination detection
       └──▶ Data Analyst(:8014)  Plotly charts + interactive HTML artifacts
```

Each agent is a **separate FastAPI process** with its own port and agent card. The Orchestrator discovers workers on startup, then coordinates the pipeline.

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- [Gemini API key](https://aistudio.google.com/apikey) (free tier: 10 RPM, 250 RPD)

### Install

```bash
git clone git@github.com:kothariprakhar/agent-harness.git
cd agent-harness

# Backend
cd backend
cp .env.example .env          # paste your GEMINI_API_KEY
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### Run

```bash
# Option A: all at once (two terminals)
make run          # Terminal 1: all 6 backend services
make frontend     # Terminal 2: Next.js on :3000

# Option B: everything in one command
make start-all

# Verify all services are up
make health
```

Open **http://localhost:3000** and enter a research topic.

### Test Without the UI

```bash
make test
# Sends: "Write a deep dive on transformer attention mechanisms, for CS undergraduates"
# Returns JSON with article, research, charts, evaluation scores
```

---

## The Pipeline

```
1. User submits prompt
2. Orchestrator decomposes → research queries + article outline (1 Gemini call)
3. Researcher: search → fetch → extract facts with verbatim quotes (5–10 calls)
4. Data Analyst: identify + generate Plotly charts + interactive HTML artifacts (4–6 calls)
5. Writer: draft article with [n] citations + {{chart:id}} placeholders (1 call)
6. Critic: extract claims → verify citations → check consistency →
          evaluate audience + completeness (5–15 calls)
7. If score < 0.80: send feedback to Writer → revise (max 3 cycles)
8. Return: article + research + charts + artifacts + evaluation + token usage
```

**Free-tier capacity**: ~40–80 Gemini calls per article → 3–6 articles/day.

---

## Anti-Hallucination System

| Metric | Method | Threshold |
|--------|--------|-----------|
| Citation Accuracy | Gemini verifies each cited claim against the source quote | ≥ 85% |
| Claim Grounding | % of factual claims that have any citation | ≥ 80% |
| Internal Consistency | Cross-check quantitative claims for contradictions | 100% |
| Audience Alignment | Vocabulary, depth, engagement for target audience | ≥ 70% |
| Completeness | Topic coverage, depth, source breadth | ≥ 60% |
| **Overall** | Weighted average (citations 30% + grounding 30% + consistency 20% + audience 10% + completeness 10%) | **≥ 80%** |

Failed articles are revised up to 3 times. If still below threshold, published with a quality warning banner and all scores visible.

---

## Knowledge Base

Upload example articles to make the pipeline match your writing style:

```bash
# Via API
curl -X POST http://localhost:8000/api/kb/upload \
  -F "file=@my_article.md" \
  -F "tags=technical-blog"

# Via UI: click the Knowledge Base panel above the prompt input
```

**How it works:**
- Upload: 1 Gemini call per article analyzes tone, structure, vocabulary, exemplary passages
- Generate: 0 extra calls — pre-computed style guide is injected into the Writer's system prompt
- Tag filtering: maintain separate style profiles (e.g., "newsletter" vs "deep-dive")

Supported formats: `.md`, `.txt`, `.html`, `.pdf`, `.docx`

---

## Project Structure

```
backend/
  shared/          config, Pydantic models, Gemini client (rate limiting), A2A helpers
  agents/          orchestrator, researcher, writer, critic, data_analyst + base_agent
  gateway/         FastAPI + Socket.IO hub, REST routes, pipeline runner
  knowledge_base/  file store, text extractor, style analyzer, composite builder
  tests/           unit + integration tests

frontend/src/
  app/             Next.js App Router (page.tsx = main dashboard)
  components/      PipelineDAG, ArticleRenderer, ChartEmbed, ArtifactEmbed,
                   QualityScores, TokenTracker, KnowledgeBasePanel, StyleProfileViewer
  hooks/           usePipeline, useWebSocket
  lib/             types.ts, api.ts, constants.ts

scripts/
  start_all.sh     launches all 6 backend services in correct order
  seed_test.sh     curl test harness
```

---

## API

### Generate Article
```
POST /api/generate
{
  "prompt": "...",
  "audience": "general",
  "tone": "informative",
  "use_knowledge_base": false,
  "kb_tags": []
}
```

### Knowledge Base
```
POST   /api/kb/upload              multipart: file, title, tags
GET    /api/kb/articles?tags=...   list articles
GET    /api/kb/articles/{id}       article + style profile
DELETE /api/kb/articles/{id}
PUT    /api/kb/articles/{id}/tags  body: ["tag1", "tag2"]
GET    /api/kb/style-guide?tags=   composite guide
```

### Agent Endpoints (A2A)
Each agent exposes `GET /.well-known/agent-card.json`, `GET /health`, `POST /` (JSON-RPC 2.0).

---

## Tech Stack

| Layer | Stack |
|-------|-------|
| LLM | Gemini 2.5 Flash (`google-genai`) |
| Agent protocol | A2A — JSON-RPC 2.0, SSE streaming |
| Backend | FastAPI, uvicorn, Pydantic v2 |
| Web search | `googlesearch-python` (no API key) |
| Page fetch | `httpx` + `BeautifulSoup4` |
| Frontend | Next.js 14, React 18, TypeScript |
| Styling | Tailwind CSS |
| DAG viz | React Flow |
| Charts | Plotly.js + react-plotly.js |
| WebSocket | Socket.IO |
| KB extraction | PyPDF2, python-docx, BeautifulSoup4 |

---

## Configuration

```env
# backend/.env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash       # optional
GEMINI_RPM_LIMIT=10                 # optional (default: free tier)
GEMINI_RPD_LIMIT=250                # optional
```

---

## Makefile

```bash
make setup          # pip install backend deps
make frontend-setup # npm install frontend deps
make run            # start all 6 backend services
make frontend       # start Next.js dev server
make start-all      # backend + frontend together
make health         # curl all 6 service health endpoints
make test           # fire a test prompt, print JSON result
```

---

## Detailed Docs

See [WALKTHROUGH.md](./WALKTHROUGH.md) for a full technical walkthrough: agent internals, pipeline lifecycle, anti-hallucination layers, knowledge base architecture, and frontend component breakdown.
