"""Pydantic models shared across all agents."""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


def new_id() -> str:
    return str(uuid.uuid4())


# ── Task lifecycle ──────────────────────────────────────────────────────────

class TaskState(str, Enum):
    SUBMITTED = "SUBMITTED"
    WORKING = "WORKING"
    INPUT_REQUIRED = "INPUT_REQUIRED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class TaskStatus(BaseModel):
    state: TaskState
    message: str = ""


# ── Research ────────────────────────────────────────────────────────────────

class ResearchFinding(BaseModel):
    claim: str
    source_url: str
    source_title: str
    supporting_quote: str
    confidence: float = Field(ge=0.0, le=1.0)
    search_query: str = ""


class ResearchOutput(BaseModel):
    findings: list[ResearchFinding]
    queries_used: list[str]
    total_sources_consulted: int = 0


# ── Writing ─────────────────────────────────────────────────────────────────

class Citation(BaseModel):
    index: int
    source_url: str
    source_title: str
    claim_text: str = ""


class WritingBrief(BaseModel):
    topic: str
    audience: str = "general"
    tone: str = "informative"
    research_findings: list[ResearchFinding] = []
    chart_specs: list[ChartSpec] = []
    concept_artifacts: list[ConceptArtifact] = []
    revision_feedback: Optional[CriticReport] = None
    previous_draft: Optional[str] = None


class ArticleDraft(BaseModel):
    markdown: str
    citations: list[Citation] = []
    word_count: int = 0
    sections: list[str] = []


# ── Evaluation ──────────────────────────────────────────────────────────────

class CriticIssue(BaseModel):
    severity: str = "warning"  # "error" | "warning" | "info"
    location: str = ""  # section or paragraph reference
    description: str = ""
    suggestion: str = ""


class CriticReport(BaseModel):
    passed: bool = False
    citation_accuracy: float = Field(default=0.0, ge=0.0, le=1.0)
    claim_grounding_score: float = Field(default=0.0, ge=0.0, le=1.0)
    internal_consistency: float = Field(default=0.0, ge=0.0, le=1.0)
    audience_alignment: float = Field(default=0.0, ge=0.0, le=1.0)
    completeness: float = Field(default=0.0, ge=0.0, le=1.0)
    overall_score: float = Field(default=0.0, ge=0.0, le=1.0)
    issues: list[CriticIssue] = []
    suggestions: list[str] = []
    revision_required: bool = False


# ── Data Visualization ──────────────────────────────────────────────────────

class ChartSpec(BaseModel):
    chart_id: str = Field(default_factory=new_id)
    title: str = ""
    chart_type: str = ""  # "bar", "line", "scatter", "sankey", etc.
    plotly_json: dict = {}
    data_sources: list[str] = []
    caption: str = ""
    placement_hint: str = ""


class ConceptArtifact(BaseModel):
    artifact_id: str = Field(default_factory=new_id)
    title: str = ""
    html_content: str = ""
    concept_explained: str = ""
    interactivity_description: str = ""
    placement_hint: str = ""


class DataAnalystOutput(BaseModel):
    charts: list[ChartSpec] = []
    artifacts: list[ConceptArtifact] = []


# ── Pipeline ────────────────────────────────────────────────────────────────

class PipelineRequest(BaseModel):
    prompt: str
    audience: str = "general"
    tone: str = "informative"


class TokenUsage(BaseModel):
    agent: str
    input_tokens: int = 0
    output_tokens: int = 0


class PipelineResult(BaseModel):
    article: ArticleDraft = Field(default_factory=ArticleDraft)
    research: ResearchOutput = Field(default_factory=ResearchOutput)
    charts: list[ChartSpec] = []
    artifacts: list[ConceptArtifact] = []
    evaluation: CriticReport = Field(default_factory=CriticReport)
    token_usage: list[TokenUsage] = []
    revision_count: int = 0
    total_time_seconds: float = 0.0


# ── A2A Protocol ────────────────────────────────────────────────────────────

class AgentSkill(BaseModel):
    id: str
    name: str
    description: str
    tags: list[str] = []
    examples: list[str] = []


class AgentCapabilities(BaseModel):
    streaming: bool = True
    pushNotifications: bool = False
    stateTransitionHistory: bool = True


class AgentCard(BaseModel):
    name: str
    description: str
    url: str
    version: str = "1.0.0"
    protocolVersion: str = "0.3"
    capabilities: AgentCapabilities = Field(default_factory=AgentCapabilities)
    defaultInputModes: list[str] = ["text/plain", "application/json"]
    defaultOutputModes: list[str] = ["application/json"]
    skills: list[AgentSkill] = []


class MessagePart(BaseModel):
    kind: str = "text"  # "text" | "data"
    text: str = ""
    data: dict = {}


class A2AMessage(BaseModel):
    role: str = "user"
    parts: list[MessagePart] = []
    contextId: str = Field(default_factory=new_id)
    taskId: str = ""


class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: str = Field(default_factory=new_id)
    method: str = "SendMessage"
    params: dict = {}


class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: str = ""
    result: Optional[dict] = None
    error: Optional[dict] = None


# ── WebSocket Events (Gateway → Frontend) ──────────────────────────────────

class PipelineEvent(BaseModel):
    type: str  # task_created, task_status, message_sent, message_received, token_usage, pipeline_complete
    timestamp: str = ""
    agent_name: str = ""
    task_id: str = ""
    data: dict = {}


# Forward references
WritingBrief.model_rebuild()
