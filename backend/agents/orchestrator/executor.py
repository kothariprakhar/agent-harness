"""Orchestrator agent executor: decomposes prompts, dispatches to agents, manages quality loop."""

from __future__ import annotations

import json
import logging
import time
from typing import AsyncGenerator, Callable, Optional

from agents.base_agent import AgentExecutor
from agents.orchestrator.prompts import ORCHESTRATOR_SYSTEM_PROMPT, DECOMPOSE_PROMPT
from shared.a2a_helpers import fetch_agent_card, send_a2a_message
from shared.gemini_client import get_gemini_client
from shared.models import (
    AgentCard,
    ArticleDraft,
    CriticReport,
    DataAnalystOutput,
    PipelineEvent,
    PipelineResult,
    ResearchOutput,
    TaskState,
    TokenUsage,
    new_id,
)
from shared.config import WORKER_AGENT_URLS, MAX_REVISION_CYCLES

logger = logging.getLogger(__name__)


def _safe_json_parse(text: str) -> dict | list | None:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _extract_artifact_data(response_result: dict) -> dict:
    """Extract data from the first artifact in a JSON-RPC response."""
    artifacts = response_result.get("result", {}).get("artifacts", [])
    if not artifacts:
        return {}
    parts = artifacts[0].get("parts", [])
    for part in parts:
        if part.get("kind") == "data":
            return part.get("data", {})
    return {}


class OrchestratorExecutor(AgentExecutor):
    def __init__(self, event_callback: Optional[Callable] = None):
        self.event_callback = event_callback
        self.agent_cards: dict[str, AgentCard] = {}

    async def _emit_event(self, event_type: str, agent_name: str, message: str, data: dict = None):
        if self.event_callback:
            event = PipelineEvent(
                type=event_type,
                timestamp=str(time.time()),
                agent_name=agent_name,
                task_id="",
                data={"message": message, **(data or {})},
            )
            await self.event_callback(event)

    async def discover_agents(self) -> dict[str, AgentCard]:
        """Discover worker agents by fetching their Agent Cards."""
        for name, url in WORKER_AGENT_URLS.items():
            card = await fetch_agent_card(url)
            if card:
                self.agent_cards[name] = card
                logger.info(f"Discovered agent: {name} at {url}")
            else:
                logger.warning(f"Failed to discover agent: {name} at {url}")
        return self.agent_cards

    async def execute(
        self,
        message_text: str,
        message_data: dict,
        task_id: str,
        context_id: str,
        metadata: dict,
    ) -> dict:
        start_time = time.time()
        client = get_gemini_client()

        prompt = message_text or message_data.get("prompt", "")
        audience = message_data.get("audience", "general")
        tone = message_data.get("tone", "informative")
        style_guide = message_data.get("style_guide")  # CompositeStyleGuide dict or None

        if not prompt:
            return {
                "status": {"state": "FAILED", "message": "No prompt provided"},
                "artifacts": [],
            }

        # Discover agents
        await self._emit_event("task_status", "orchestrator", "Discovering agents...")
        await self.discover_agents()

        # Step 1: Decompose the prompt
        await self._emit_event("task_status", "orchestrator", "Decomposing prompt into tasks...")
        decompose_resp = await client.generate(
            prompt=DECOMPOSE_PROMPT.format(prompt=prompt, audience=audience, tone=tone),
            system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
            agent_name="orchestrator",
            temperature=0.5,
        )
        plan = _safe_json_parse(decompose_resp.text)
        if not isinstance(plan, dict):
            plan = {
                "research_queries": [prompt],
                "article_outline": ["Introduction", "Main Content", "Conclusion"],
                "audience_level": "intermediate",
                "key_concepts_to_visualize": [],
            }

        # Step 2: Research
        await self._emit_event("message_sent", "orchestrator", f"Dispatching research task to researcher")
        research_response = await send_a2a_message(
            agent_url=WORKER_AGENT_URLS["researcher"],
            message_data={
                "topic": prompt,
                "audience": audience,
                "num_queries": len(plan.get("research_queries", [prompt])),
            },
            context_id=context_id,
            metadata={"parentTaskId": task_id},
        )
        research_data = _extract_artifact_data(research_response.model_dump())
        research_output = ResearchOutput.model_validate(research_data) if research_data else ResearchOutput(findings=[], queries_used=[])

        await self._emit_event(
            "message_received", "researcher",
            f"Research complete: {len(research_output.findings)} findings",
            {"findings_count": len(research_output.findings)},
        )

        if not research_output.findings:
            return {
                "status": {"state": "FAILED", "message": "Research found no findings"},
                "artifacts": [],
            }

        # Step 3: Data Analysis (charts + artifacts)
        await self._emit_event("message_sent", "orchestrator", "Dispatching visualization task")
        da_response = await send_a2a_message(
            agent_url=WORKER_AGENT_URLS["data_analyst"],
            message_data={
                "topic": prompt,
                "research_findings": [f.model_dump() for f in research_output.findings],
                "sections": plan.get("article_outline", []),
                "audience": audience,
            },
            context_id=context_id,
            metadata={"parentTaskId": task_id},
        )
        da_data = _extract_artifact_data(da_response.model_dump())
        da_output = DataAnalystOutput.model_validate(da_data) if da_data else DataAnalystOutput()

        await self._emit_event(
            "message_received", "data_analyst",
            f"Generated {len(da_output.charts)} charts, {len(da_output.artifacts)} artifacts",
        )

        # Step 4: Writing + Quality Loop
        revision_count = 0
        article_draft: Optional[ArticleDraft] = None
        critic_report: Optional[CriticReport] = None
        previous_draft: Optional[str] = None

        for cycle in range(MAX_REVISION_CYCLES + 1):
            # Write
            write_data: dict = {
                "topic": prompt,
                "audience": audience,
                "tone": tone,
                "research_findings": [f.model_dump() for f in research_output.findings],
                "chart_specs": [c.model_dump() for c in da_output.charts],
                "concept_artifacts": [a.model_dump() for a in da_output.artifacts],
            }
            if style_guide:
                write_data["style_guide"] = style_guide
            if critic_report and previous_draft:
                write_data["revision_feedback"] = critic_report.model_dump()
                write_data["previous_draft"] = previous_draft
                await self._emit_event(
                    "message_sent", "orchestrator",
                    f"Revision {revision_count}: sending feedback to writer",
                )
            else:
                await self._emit_event("message_sent", "orchestrator", "Dispatching writing task")

            writer_response = await send_a2a_message(
                agent_url=WORKER_AGENT_URLS["writer"],
                message_data=write_data,
                context_id=context_id,
                metadata={"parentTaskId": task_id},
            )
            writer_data = _extract_artifact_data(writer_response.model_dump())
            article_draft = ArticleDraft.model_validate(writer_data) if writer_data else None

            if not article_draft or not article_draft.markdown:
                return {
                    "status": {"state": "FAILED", "message": "Writer produced empty output"},
                    "artifacts": [],
                }

            await self._emit_event(
                "message_received", "writer",
                f"Draft received: {article_draft.word_count} words",
            )

            # Critique
            await self._emit_event("message_sent", "orchestrator", "Dispatching evaluation task")
            critic_data_msg: dict = {
                    "article_markdown": article_draft.markdown,
                    "citations": [c.model_dump() for c in article_draft.citations],
                    "research_findings": [f.model_dump() for f in research_output.findings],
                    "topic": prompt,
                    "audience": audience,
                    "sections": article_draft.sections,
                    "word_count": article_draft.word_count,
            }
            if style_guide:
                critic_data_msg["style_guide"] = style_guide

            critic_response = await send_a2a_message(
                agent_url=WORKER_AGENT_URLS["critic"],
                message_data=critic_data_msg,
                context_id=context_id,
                metadata={"parentTaskId": task_id},
            )
            critic_data = _extract_artifact_data(critic_response.model_dump())
            critic_report = CriticReport.model_validate(critic_data) if critic_data else CriticReport()

            status = critic_response.model_dump().get("result", {}).get("status", {})
            await self._emit_event(
                "message_received", "critic",
                f"Evaluation: {status.get('message', 'done')}",
                {"scores": critic_report.model_dump()},
            )

            if critic_report.passed:
                break

            if cycle < MAX_REVISION_CYCLES:
                revision_count += 1
                previous_draft = article_draft.markdown
                await self._emit_event(
                    "task_status", "orchestrator",
                    f"Revision {revision_count}/{MAX_REVISION_CYCLES} — quality threshold not met",
                )

        # Assemble final result
        elapsed = time.time() - start_time
        result = PipelineResult(
            article=article_draft,
            research=research_output,
            charts=da_output.charts,
            artifacts=da_output.artifacts,
            evaluation=critic_report,
            token_usage=client.token_log.copy(),
            revision_count=revision_count,
            total_time_seconds=round(elapsed, 2),
        )

        passed_str = "PASSED" if critic_report.passed else "BELOW THRESHOLD"
        await self._emit_event(
            "pipeline_complete", "orchestrator",
            f"Pipeline complete in {elapsed:.1f}s — Quality: {passed_str}",
        )

        return {
            "status": {
                "state": "COMPLETED",
                "message": (
                    f"Article generated ({article_draft.word_count} words, "
                    f"{revision_count} revisions, {elapsed:.1f}s). "
                    f"Quality: {critic_report.overall_score:.1%}"
                ),
            },
            "artifacts": [
                {
                    "parts": [{"kind": "data", "data": result.model_dump()}],
                    "mimeType": "application/json",
                }
            ],
        }
