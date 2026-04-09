# AgentHarness: Product Walkthrough

A multi-agent orchestration system that transforms a single research prompt into a well-researched, citation-verified article with interactive charts and concept visualizations — powered by five specialized AI agents communicating via the A2A protocol.

---

## Table of Contents

1. [What This Is](#what-this-is)
2. [Architecture Overview](#architecture-overview)
3. [The Five Agents](#the-five-agents)
4. [Pipeline: From Prompt to Published Article](#pipeline-from-prompt-to-published-article)
5. [Anti-Hallucination System](#anti-hallucination-system)
6. [Knowledge Base: Style Training](#knowledge-base-style-training)
7. [Interactive Visualizations](#interactive-visualizations)
8. [Frontend Dashboard](#frontend-dashboard)
9. [Technical Deep Dive](#technical-deep-dive)
10. [Setup & Running](#setup--running)
11. [API Reference](#api-reference)

---

## What This Is

AgentHarness is **not** a typical chatbot wrapper or a single-model RAG pipeline. It is a distributed system of five independently running AI agents, each with a distinct role, communicating over a standardized protocol (A2A / JSON-RPC 2.0) to produce research articles that are:

- **Factually grounded**: Every claim is traced back to a web source with a verbatim supporting quote
- **Quality-evaluated**: Five distinct metrics scored by a dedicated Critic agent
- **Self-correcting**: A feedback loop where the Critic sends the Writer back to revise until quality thresholds are met
- **Visually rich**: Plotly data charts and interactive HTML concept explainers embedded inline
- **Style-adaptive**: A Knowledge Base lets you upload example articles so the pipeline mimics your preferred writing style

The system runs on Gemini 2.5 Flash (free tier: 10 requests/minute, 250 requests/day) with built-in rate limiting and token tracking.

---

## Architecture Overview

```
Browser (Next.js on port 3000)
    |
    |  WebSocket (Socket.IO) + REST
    v
Gateway (FastAPI on port 8000)  ---------- /api/kb/* (Knowledge Base CRUD)
    |
    |  A2A JSON-RPC 2.0
    v
Orchestrator (port 8010)  -------- discovers agents via /.well-known/agent-card.json
    |
    |--- Researcher   (port 8011)  --- web search, page fetch, fact extraction
    |--- Writer       (port 8012)  --- article drafting and revision
    |--- Critic       (port 8013)  --- quality scoring, hallucination detection
    '--- Data Analyst (port 8014)  --- Plotly charts + interactive HTML artifacts
```

**Key design decisions:**
- Each agent is a **separate FastAPI process** with its own port, agent card, and A2A-compliant JSON-RPC endpoint
- The Gateway is a **thin relay** (not an agent) — it accepts browser requests and forwards them to the Orchestrator
- All LLM calls route through a **shared GeminiClient** with a TokenBucket rate limiter (per-process)
- The Orchestrator **never generates content** — it only decomposes, dispatches, and quality-gates

---

## The Five Agents

### Orchestrator (port 8010)
**Role**: Pipeline coordinator and quality gatekeeper.

On startup, the Orchestrator fetches Agent Cards from all worker agents at `/.well-known/agent-card.json` to discover their capabilities. When a request arrives, it:

1. Uses Gemini to decompose the prompt into research queries, an article outline, and visualization targets
2. Dispatches tasks to each agent in sequence: Researcher -> Data Analyst -> Writer -> Critic
3. Manages the **revision loop**: if the Critic fails the article, the Orchestrator sends feedback back to the Writer (up to 3 cycles)
4. Assembles the final `PipelineResult` with article, research, charts, artifacts, evaluation scores, and token usage

The Orchestrator itself uses only one LLM call (for decomposition). The rest is pure orchestration logic.

### Researcher (port 8011)
**Role**: Strictly extractive fact-finding. Never invents claims.

The Researcher operates under a hard constraint: every claim it outputs must include a **verbatim quote** from a web source. Its workflow:

1. Generates 3-5 diverse search queries from the topic via Gemini
2. Searches the web using `googlesearch-python` (no API key needed)
3. Fetches the top results with `httpx`, extracts clean text with `BeautifulSoup`
4. Sends each page's content to Gemini with a strict extraction prompt: "Extract facts with verbatim quotes only"
5. Deduplicates findings and returns `ResearchOutput` with each finding's claim, source URL, supporting quote, and confidence score

**Output schema**:
```
ResearchFinding {
  claim: str               # "GPT-4 has 1.8 trillion parameters"
  source_url: str           # "https://arxiv.org/..."
  source_title: str         # "GPT-4 Technical Report"
  supporting_quote: str     # Verbatim text from the source
  confidence: 0.0-1.0       # Based on source quality
  search_query: str         # Which query found this
}
```

### Writer (port 8012)
**Role**: Drafts and revises articles from research findings.

The Writer receives research findings, chart specs, and concept artifact metadata. It operates in two modes:

**First draft mode**: Takes the full research package and produces a Markdown article with:
- Inline `[n]` citations for every factual claim
- `{{chart:id}}` placeholders where data charts belong
- `{{artifact:id}}` placeholders where interactive concept explainers belong
- A "Sources" section at the end
- `[UNGROUNDED]` markers on any claim it cannot ground in the research

**Revision mode**: Receives the Critic's issue list and suggestions alongside the previous draft, and rewrites to address each flagged problem while maintaining the same structure.

When the Knowledge Base is active, the Writer's system prompt is augmented with a pre-computed style guide (tone, structure, formatting patterns, and exemplary passages from uploaded reference articles).

### Critic (port 8013)
**Role**: Hallucination prevention engine. The most LLM-intensive agent.

The Critic evaluates every article across five distinct quality dimensions, each measured with separate Gemini calls:

| Step | Metric | Method | Gemini Calls |
|------|--------|--------|-------------|
| 1 | Claim Extraction | Parse all factual claims from the article | 1 |
| 2 | Citation Accuracy | For each cited claim, verify the source quote supports it | 1 per claim (cap: 15) |
| 3 | Claim Grounding | Check what % of factual claims have citations | 0 (computed from step 1) |
| 4 | Internal Consistency | Check quantitative claim pairs for contradictions | 1 per pair (cap: 5) |
| 5 | Audience Alignment | Evaluate vocabulary, explanation depth, engagement | 1 |
| 6 | Completeness | Assess topic coverage, depth, breadth | 1 |
| 7 | Style Match | (KB only) Evaluate against reference style guide | 1 |

**Thresholds** (must all pass for the article to be accepted):
- Citation Accuracy >= 85%
- Claim Grounding >= 80%
- Internal Consistency = 100% (zero tolerance for contradictions)
- Audience Alignment >= 70%
- Completeness >= 60%
- Overall (weighted average) >= 80%

Style Match is informational only — it appears in the report but doesn't block publication.

If the article fails, the Critic returns `INPUT_REQUIRED` state with a detailed issue list, and the Orchestrator sends it back to the Writer.

### Data Analyst (port 8014)
**Role**: Produces two types of visual content.

**Type A — Data Charts (Plotly.js)**:
Standard interactive charts (bar, line, scatter, pie, Sankey) where every data point traces back to a `ResearchFinding`. The agent identifies visualization opportunities from the research, then generates complete Plotly.js JSON specs that the frontend renders with react-plotly.js.

**Type B — Concept Artifacts (Interactive HTML)**:
Self-contained HTML/CSS/JS visualizations that *teach concepts* through interaction. These are the key differentiator — similar to Claude's artifacts but generated by the Data Analyst agent. Examples:
- Animated step-by-step walkthrough of an algorithm with play/pause
- Interactive slider showing how changing a parameter affects results
- Draggable node diagram where users trace data flow
- Side-by-side comparison tool with toggleable inputs

Each artifact is a complete HTML document with inline CSS and JS (no external dependencies), rendered in sandboxed `<iframe>` elements in the article.

---

## Pipeline: From Prompt to Published Article

Here is the complete request lifecycle:

```
User enters: "Write a deep dive on how transformer attention mechanisms
              actually work, aimed at CS undergraduates"

1. GATEWAY receives POST /api/generate
   |-- Checks if Knowledge Base is enabled
   |-- If yes: loads pre-computed CompositeStyleGuide from filesystem
   |-- Forwards to Orchestrator via A2A JSON-RPC

2. ORCHESTRATOR decomposes prompt
   |-- Gemini call #1: generate research queries + article outline
   |   Returns: ["how does self-attention work", "Q K V matrices explained", ...]
   |
   |-- Dispatches to RESEARCHER
   |   |-- Gemini call #2: generate search queries from topic
   |   |-- For each query: Google search -> fetch top 3-5 pages
   |   |-- Gemini calls #3-7: extract facts with verbatim quotes from each page
   |   |-- Returns: 15-30 ResearchFindings with sources
   |
   |-- Dispatches to DATA ANALYST
   |   |-- Gemini call #8: identify visualization opportunities
   |   |-- Gemini calls #9-10: generate Plotly chart JSON specs
   |   |-- Gemini calls #11-13: generate interactive HTML concept artifacts
   |   |-- Returns: 1-2 charts + 2-3 concept artifacts
   |
   |-- REVISION LOOP (max 3 cycles):
   |   |
   |   |-- Dispatches to WRITER
   |   |   |-- Gemini call: draft article from findings + charts + artifacts
   |   |   |-- (If KB active: system prompt includes style guide)
   |   |   |-- Returns: Markdown article with [n] citations, {{chart:id}}, {{artifact:id}}
   |   |
   |   |-- Dispatches to CRITIC
   |   |   |-- Gemini calls (5-15): extract claims, verify citations, check consistency,
   |   |   |   evaluate audience, assess completeness, (optional: score style match)
   |   |   |-- Returns: CriticReport with 5-6 scores + issue list
   |   |
   |   |-- If PASSED: break loop
   |   |-- If FAILED: send CriticReport to Writer for revision
   |
   |-- Assembles PipelineResult

3. GATEWAY returns result to browser via REST
   |-- Simultaneously streams events via WebSocket for live dashboard
```

**Total Gemini calls per article**: ~40-80 (varies with research depth and revision cycles)
**Capacity on free tier**: 3-6 articles per day

---

## Anti-Hallucination System

The system uses a layered defense against hallucination:

**Layer 1 — Researcher constraints**:
The Researcher agent's system prompt forbids generating facts from its own knowledge. Every output `ResearchFinding` must include a `supporting_quote` that is verbatim text from a fetched web page. The Researcher will return an empty findings list rather than fabricate.

**Layer 2 — Writer constraints**:
The Writer's system prompt mandates that every factual claim must have an `[n]` citation. Claims without research backing must be flagged with `[UNGROUNDED]` markers.

**Layer 3 — Critic verification**:
The Critic independently re-verifies each citation by asking Gemini: "Does this quote from this source support this claim?" with three possible verdicts: SUPPORTS, CONTRADICTS, or INSUFFICIENT. The Citation Accuracy score is the ratio of SUPPORTS verdicts to total cited claims.

**Layer 4 — Consistency checking**:
The Critic pairs up quantitative claims from different sections and checks for contradictions (e.g., "the model has 175B parameters" in one section vs "the 1.8T parameter model" in another).

**Layer 5 — Revision loop**:
Failed articles get sent back with specific issue lists. The Writer addresses each issue while keeping the article grounded in research findings. Up to 3 revision cycles ensure progressive quality improvement.

**Layer 6 — Transparency**:
If the article still fails after 3 revisions, it's published with a quality warning banner and all scores visible. Nothing is hidden from the reader.

### Evaluation Weights

```
Overall Score = Citation Accuracy  x 0.30
              + Claim Grounding    x 0.30
              + Consistency        x 0.20
              + Audience Alignment x 0.10
              + Completeness       x 0.10
```

The heavy weighting on Citation Accuracy (30%) and Claim Grounding (30%) reflects the system's primary goal: factual reliability over style.

---

## Knowledge Base: Style Training

The Knowledge Base solves this problem: "I want the pipeline to write articles that sound like *my* articles."

### How It Works

**Upload phase** (1 Gemini call per article):
1. User uploads an example article (MD, TXT, HTML, PDF, or DOCX)
2. Text is extracted using format-specific parsers (BeautifulSoup for HTML, PyPDF2 for PDF, python-docx for DOCX)
3. Structural metrics are computed in Python: sentence count, average length, heading count, list usage
4. One Gemini call analyzes the writing style and returns a `StyleProfile`:
   - Tone descriptors (e.g., "analytical", "conversational")
   - Sentence style pattern description
   - Vocabulary level (technical / accessible / academic / casual)
   - Formatting patterns (e.g., "uses bullet lists", "bold key terms")
   - Structural template (section flow pattern)
   - 2-3 exemplary passages copied verbatim
5. Everything is saved to `backend/knowledge_base/data/articles/{uuid}/`

**Composite aggregation** (zero LLM calls):
When multiple articles are uploaded, a `CompositeStyleGuide` is built using pure Python:
- Tone descriptors ranked by frequency across all articles
- Vocabulary level by majority vote
- Structural templates merged with a 30% occurrence threshold
- Best exemplary passages selected across all articles
- A pre-rendered `full_style_prompt` text block ready for injection

**Generation phase** (zero extra LLM calls for writer, one for critic):
When the user toggles "Use Knowledge Base" and clicks Generate:
- The Gateway loads the composite style guide from disk
- It's passed through: Gateway -> pipeline_runner -> Orchestrator -> Writer + Critic
- The Writer's system prompt gets the style guide appended — no additional API call needed
- The Critic evaluates `style_match` (one extra Gemini call) but it's informational only
- Tag filtering lets users maintain separate style profiles (e.g., "blog" vs "newsletter")

### Rate Limit Impact
- 50 article uploads = 50 Gemini calls (20% of daily budget)
- Article generation throughput is completely unaffected
- The style guide adds ~500-1000 tokens to the Writer's system prompt

---

## Interactive Visualizations

### Data Charts
The Data Analyst generates Plotly.js JSON specifications. The frontend renders them with `react-plotly.js`, giving users hover tooltips, zoom, pan, and export. Every data point in a chart must trace back to a `ResearchFinding` — the Critic verifies the `data_sources` field.

### Concept Artifacts
These are the signature feature. Instead of static diagrams, the Data Analyst generates complete interactive HTML applications:

```html
<!-- Example: Self-Attention Weight Visualizer -->
<!DOCTYPE html>
<html>
<head><style>/* inline CSS */</style></head>
<body>
  <h2>How Self-Attention Computes Weights</h2>
  <canvas id="viz" width="600" height="400"></canvas>
  <input type="range" id="temperature" min="0.1" max="2.0" step="0.1">
  <script>
    // Complete interactive visualization using Canvas API
    // Responds to slider input, animates attention patterns
  </script>
</body>
</html>
```

The frontend renders these in sandboxed `<iframe srcDoc={html}>` elements, positioned inline where the Writer placed `{{artifact:id}}` placeholders.

---

## Frontend Dashboard

The frontend is a Next.js 14 app with three views:

### Pipeline View
A real-time visualization of the agent orchestration:
- **DAG Graph** (React Flow): Nodes for each agent, color-coded by status (idle/working/completed/failed), with animated edges showing data flow
- **Message Stream**: Auto-scrolling log of every inter-agent message, color-coded by agent
- **Token Tracker**: Per-agent token usage, estimated cost, and execution time
- **Quality Scores**: Gauge bars for each evaluation metric

### Article View
The rendered output:
- **Markdown article** rendered with `react-markdown` + `remark-gfm`
- **Plotly charts** embedded inline where `{{chart:id}}` placeholders appear
- **Interactive artifacts** in sandboxed iframes where `{{artifact:id}}` placeholders appear
- **Clickable citations** with source links
- **Quality score sidebar** with the Critic's evaluation

### Evaluation View
Detailed quality analysis:
- All five metric gauges with pass/fail indicators
- Style Match score (when Knowledge Base is active)
- Full list of Critic issues with severity and suggestions
- Research findings browser with confidence scores and source links

### Knowledge Base Panel
A collapsible panel above the prompt input:
- Drag-and-drop file upload with title and tag inputs
- List of uploaded articles with metadata (word count, format, tags)
- Click to expand and view the Style Profile (tone, structure, exemplary passages)
- Delete articles with automatic composite recomputation

---

## Technical Deep Dive

### A2A Protocol Compliance
Every agent implements the Agent-to-Agent protocol:
- **Agent Card** served at `GET /.well-known/agent-card.json` — declares capabilities, skills, supported input/output modes
- **JSON-RPC 2.0** endpoint at `POST /` — accepts `SendMessage` and `SendStreamingMessage` methods
- **Task States**: `SUBMITTED -> WORKING -> COMPLETED | FAILED | INPUT_REQUIRED`
- **Message Parts**: `text` (string) + `data` (structured dict) in each message
- The Orchestrator discovers agents by fetching their cards on startup

### Rate Limiting
The `GeminiClient` implements a `TokenBucket` with per-minute and per-day limits:
```python
TokenBucket(capacity=10, refill_rate=10/60)  # 10 RPM
daily_limit = 250                             # 250 RPD
```
All agents in the same process share one client instance. Multi-process deployment gives each agent its own bucket.

### Token Tracking
Every Gemini call logs `TokenUsage(agent, input_tokens, output_tokens)`. The Orchestrator collects these into the final `PipelineResult`, which the frontend displays as per-agent breakdowns with estimated cost.

### File Storage (Knowledge Base)
```
backend/knowledge_base/data/
  index.json                    # Master article index (list of metadata)
  articles/
    {uuid}/
      original.{ext}           # Uploaded file
      extracted.md             # Extracted plain text
      style_profile.json       # Gemini-analyzed style profile
```
No database. No vector store. JSON files on disk. This is intentional — the system is a single-user demo, and pre-computation eliminates the need for runtime retrieval.

---

## Setup & Running

### Prerequisites
- Python 3.11+
- Node.js 18+
- A Gemini API key ([get one free](https://aistudio.google.com/apikey))

### Installation

```bash
# Clone
git clone git@github.com:kothariprakhar/agent-harness.git
cd agent-harness

# Backend
cd backend
cp .env.example .env        # Add your GEMINI_API_KEY
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### Running

**Option A — All at once:**
```bash
make start-all
```

**Option B — Separate terminals:**
```bash
# Terminal 1: Backend (all 6 services)
make run

# Terminal 2: Frontend
make frontend
```

**Option C — Manual:**
```bash
# Start worker agents
cd backend
python -m agents.researcher.main &   # port 8011
python -m agents.writer.main &       # port 8012
python -m agents.critic.main &       # port 8013
python -m agents.data_analyst.main & # port 8014
sleep 3

# Start orchestrator (needs workers available)
python -m agents.orchestrator.main & # port 8010
sleep 2

# Start gateway
python -m gateway.main &             # port 8000

# Start frontend
cd ../frontend && npm run dev        # port 3000
```

### Health Check
```bash
make health
# Checks all 6 services: Gateway, Orchestrator, Researcher, Writer, Critic, Data Analyst
```

### Test Run
```bash
make test
# Sends a test prompt: "Write a deep dive on how transformer attention mechanisms
#   actually work, aimed at CS undergraduates"
```

Or open http://localhost:3000 in your browser.

---

## API Reference

### Article Generation

**POST /api/generate**
```json
{
  "prompt": "Write a deep dive on quantum computing",
  "audience": "general",
  "tone": "informative",
  "use_knowledge_base": true,
  "kb_tags": ["technical-blog"]
}
```
Returns: `PipelineResult` with article, research, charts, artifacts, evaluation, token usage.

**GET /api/results/{id}** — Retrieve a previously generated result.

**GET /api/health** — Gateway health check.

### Knowledge Base

**POST /api/kb/upload** (multipart form)
- `file`: The article file (MD, TXT, HTML, PDF, DOCX)
- `title`: Optional title
- `tags`: Comma-separated tag string

**GET /api/kb/articles?tags=blog,technical** — List articles, optionally filtered by tags.

**GET /api/kb/articles/{id}** — Get article detail with style profile.

**DELETE /api/kb/articles/{id}** — Remove an article.

**PUT /api/kb/articles/{id}/tags** — Update tags (JSON body: `["tag1", "tag2"]`).

**GET /api/kb/style-guide?tags=blog** — Get the composite style guide.

### Agent Endpoints (A2A)

Each agent exposes:
- **GET /.well-known/agent-card.json** — Agent capabilities and metadata
- **GET /health** — Health check
- **POST /** — JSON-RPC 2.0 (`SendMessage` / `SendStreamingMessage`)

---

## Project Structure

```
AgentHarness/
  backend/
    shared/               # Shared infrastructure
      config.py           # Ports, thresholds, rate limits
      models.py           # All Pydantic schemas (30+ models)
      gemini_client.py    # Rate-limited Gemini wrapper + TokenBucket
      a2a_helpers.py      # A2A protocol: agent card fetch, JSON-RPC messaging
      token_tracker.py    # Token usage aggregation
    agents/
      base_agent.py       # Abstract A2A-compliant FastAPI base class
      orchestrator/       # Pipeline coordinator
      researcher/         # Web search + fact extraction
      writer/             # Article drafting + revision
      critic/             # Quality evaluation + hallucination detection
      data_analyst/       # Plotly charts + interactive HTML artifacts
    gateway/
      main.py             # FastAPI + Socket.IO entry point
      routes.py           # REST endpoints (generate, KB CRUD, health)
      pipeline_runner.py  # Orchestrator invocation + event relay
      websocket_manager.py # Socket.IO broadcast
    knowledge_base/
      store.py            # Filesystem CRUD for articles
      extractor.py        # Text extraction (PDF, DOCX, MD, HTML, TXT)
      style_analyzer.py   # Gemini-powered style profiling (1 call/article)
      composite_builder.py # Pure-Python style guide aggregation
      data/               # Article storage (index.json + per-article dirs)
  frontend/
    src/app/              # Next.js App Router (page.tsx, layout.tsx)
    src/components/       # 10 React components (DAG, article, charts, KB panel, etc.)
    src/hooks/            # usePipeline, useWebSocket
    src/lib/              # Types, API client, constants
  scripts/
    start_all.sh          # Launches all 6 backend services
    seed_test.sh          # Curl-based test harness
  Makefile                # setup, run, test, health, frontend targets
```
