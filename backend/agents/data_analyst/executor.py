"""Data Analyst agent executor: generates Plotly charts and interactive concept artifacts."""

from __future__ import annotations

import json
import logging

from agents.base_agent import AgentExecutor
from agents.data_analyst.prompts import (
    DATA_ANALYST_SYSTEM_PROMPT,
    IDENTIFY_VISUALIZATIONS_PROMPT,
    GENERATE_PLOTLY_CHART_PROMPT,
    GENERATE_CONCEPT_ARTIFACT_PROMPT,
)
from shared.gemini_client import get_gemini_client
from shared.models import ChartSpec, ConceptArtifact, DataAnalystOutput, new_id

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


class DataAnalystExecutor(AgentExecutor):
    async def execute(
        self,
        message_text: str,
        message_data: dict,
        task_id: str,
        context_id: str,
        metadata: dict,
    ) -> dict:
        client = get_gemini_client()

        topic = message_data.get("topic", message_text)
        findings = message_data.get("research_findings", [])
        sections = message_data.get("sections", [])
        audience = message_data.get("audience", "general")

        # Summarize findings for the identification prompt
        findings_summary = "\n".join(
            f"[{i}] {f.get('claim', '')}" for i, f in enumerate(findings)
        )

        # Step 1: Identify visualization opportunities
        identify_resp = await client.generate(
            prompt=IDENTIFY_VISUALIZATIONS_PROMPT.format(
                topic=topic,
                sections=json.dumps(sections),
                findings_summary=findings_summary or "(No findings provided)",
            ),
            system_prompt=DATA_ANALYST_SYSTEM_PROMPT,
            agent_name="data_analyst",
            temperature=0.5,
        )
        plan = _safe_json_parse(identify_resp.text)
        if not isinstance(plan, dict):
            plan = {"charts": [], "artifacts": []}

        charts: list[ChartSpec] = []
        artifacts: list[ConceptArtifact] = []

        # Step 2: Generate Plotly charts
        for chart_plan in plan.get("charts", [])[:2]:
            source_indices = chart_plan.get("source_finding_indices", [])
            source_data = "\n".join(
                f"- {findings[i].get('claim', '')} (Source: {findings[i].get('source_title', '')})"
                for i in source_indices
                if i < len(findings)
            ) or "(No specific data points)"

            source_urls = [
                findings[i].get("source_url", "")
                for i in source_indices
                if i < len(findings)
            ]

            chart_resp = await client.generate(
                prompt=GENERATE_PLOTLY_CHART_PROMPT.format(
                    title=chart_plan.get("title", "Chart"),
                    chart_type=chart_plan.get("chart_type", "bar"),
                    data_description=chart_plan.get("data_description", ""),
                    source_data=source_data,
                ),
                system_prompt=DATA_ANALYST_SYSTEM_PROMPT,
                agent_name="data_analyst",
                temperature=0.3,
            )
            plotly_json = _safe_json_parse(chart_resp.text)
            if isinstance(plotly_json, dict) and "data" in plotly_json:
                charts.append(ChartSpec(
                    chart_id=new_id(),
                    title=chart_plan.get("title", "Chart"),
                    chart_type=chart_plan.get("chart_type", "bar"),
                    plotly_json=plotly_json,
                    data_sources=source_urls,
                    caption=chart_plan.get("data_description", ""),
                    placement_hint=chart_plan.get("target_section", ""),
                ))

        # Step 3: Generate concept artifacts
        for artifact_plan in plan.get("artifacts", [])[:3]:
            artifact_resp = await client.generate(
                prompt=GENERATE_CONCEPT_ARTIFACT_PROMPT.format(
                    concept=artifact_plan.get("concept_explained", artifact_plan.get("title", "")),
                    interactivity=artifact_plan.get("interactivity", "click and hover interactions"),
                    audience=audience,
                ),
                system_prompt=DATA_ANALYST_SYSTEM_PROMPT,
                agent_name="data_analyst",
                temperature=0.7,
            )

            html_content = artifact_resp.text.strip()
            # Clean up if wrapped in code fences
            if html_content.startswith("```"):
                lines = html_content.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                html_content = "\n".join(lines)

            if "<!DOCTYPE html>" in html_content or "<html" in html_content:
                artifacts.append(ConceptArtifact(
                    artifact_id=new_id(),
                    title=artifact_plan.get("title", "Interactive Visualization"),
                    html_content=html_content,
                    concept_explained=artifact_plan.get("concept_explained", ""),
                    interactivity_description=artifact_plan.get("interactivity", ""),
                    placement_hint=artifact_plan.get("target_section", ""),
                ))

        output = DataAnalystOutput(charts=charts, artifacts=artifacts)

        return {
            "status": {
                "state": "COMPLETED",
                "message": f"Generated {len(charts)} charts and {len(artifacts)} interactive artifacts",
            },
            "artifacts": [
                {
                    "parts": [{"kind": "data", "data": output.model_dump()}],
                    "mimeType": "application/json",
                }
            ],
        }
