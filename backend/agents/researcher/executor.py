"""Researcher agent executor: search, fetch, extract facts."""

from __future__ import annotations

import json
import logging
from typing import AsyncGenerator

from agents.base_agent import AgentExecutor
from agents.researcher.web_search import search_web, fetch_page_content
from agents.researcher.prompts import (
    RESEARCHER_SYSTEM_PROMPT,
    EXTRACT_FACTS_PROMPT,
    GENERATE_SEARCH_QUERIES_PROMPT,
)
from shared.gemini_client import get_gemini_client
from shared.models import ResearchFinding, ResearchOutput, TaskState, new_id

logger = logging.getLogger(__name__)


class ResearcherExecutor(AgentExecutor):
    async def execute(
        self,
        message_text: str,
        message_data: dict,
        task_id: str,
        context_id: str,
        metadata: dict,
    ) -> dict:
        topic = message_text or message_data.get("topic", "")
        audience = message_data.get("audience", "general")
        num_queries = message_data.get("num_queries", 3)

        if not topic:
            return {
                "status": {"state": "FAILED", "message": "No research topic provided"},
                "artifacts": [],
            }

        client = get_gemini_client()

        # Step 1: Generate search queries
        query_prompt = GENERATE_SEARCH_QUERIES_PROMPT.format(
            topic=topic, audience=audience, num_queries=num_queries
        )
        query_resp = await client.generate(
            prompt=query_prompt,
            system_prompt=RESEARCHER_SYSTEM_PROMPT,
            agent_name="researcher",
            temperature=0.5,
        )
        try:
            queries = json.loads(query_resp.text)
            if not isinstance(queries, list):
                queries = [topic]
        except (json.JSONDecodeError, TypeError):
            queries = [topic]

        # Step 2: Search and fetch pages
        all_findings: list[ResearchFinding] = []
        total_sources = 0

        for query in queries[:num_queries]:
            search_results = await search_web(query, num_results=3)
            for sr in search_results:
                page = await fetch_page_content(sr.url)
                if page is None or len(page.text_content.strip()) < 100:
                    continue
                total_sources += 1

                # Step 3: Extract facts from each page
                extract_prompt = EXTRACT_FACTS_PROMPT.format(
                    url=sr.url,
                    title=page.title,
                    content=page.text_content,
                    query=query,
                )
                try:
                    extract_resp = await client.generate(
                        prompt=extract_prompt,
                        system_prompt=RESEARCHER_SYSTEM_PROMPT,
                        agent_name="researcher",
                        temperature=0.3,
                    )
                    facts = json.loads(extract_resp.text)
                    if isinstance(facts, list):
                        for f in facts:
                            all_findings.append(ResearchFinding(
                                claim=f.get("claim", ""),
                                source_url=sr.url,
                                source_title=page.title or sr.title,
                                supporting_quote=f.get("supporting_quote", ""),
                                confidence=float(f.get("confidence", 0.5)),
                                search_query=query,
                            ))
                except Exception as e:
                    logger.warning(f"Fact extraction failed for {sr.url}: {e}")

        # Deduplicate by claim similarity (simple exact match for now)
        seen_claims: set[str] = set()
        unique_findings: list[ResearchFinding] = []
        for f in all_findings:
            key = f.claim.lower().strip()
            if key not in seen_claims and f.claim and f.supporting_quote:
                seen_claims.add(key)
                unique_findings.append(f)

        output = ResearchOutput(
            findings=unique_findings,
            queries_used=queries[:num_queries],
            total_sources_consulted=total_sources,
        )

        return {
            "status": {
                "state": "COMPLETED",
                "message": f"Found {len(unique_findings)} findings from {total_sources} sources",
            },
            "artifacts": [
                {
                    "parts": [{"kind": "data", "data": output.model_dump()}],
                    "mimeType": "application/json",
                }
            ],
        }

    async def execute_streaming(
        self,
        message_text: str,
        message_data: dict,
        task_id: str,
        context_id: str,
        metadata: dict,
    ) -> AsyncGenerator[dict, None]:
        yield self._make_event(task_id, context_id, TaskState.WORKING, "Generating search queries...")

        topic = message_text or message_data.get("topic", "")
        audience = message_data.get("audience", "general")
        num_queries = message_data.get("num_queries", 3)

        if not topic:
            yield self._make_event(task_id, context_id, TaskState.FAILED, "No topic provided")
            return

        client = get_gemini_client()

        # Generate search queries
        query_prompt = GENERATE_SEARCH_QUERIES_PROMPT.format(
            topic=topic, audience=audience, num_queries=num_queries
        )
        query_resp = await client.generate(
            prompt=query_prompt,
            system_prompt=RESEARCHER_SYSTEM_PROMPT,
            agent_name="researcher",
            temperature=0.5,
        )
        try:
            queries = json.loads(query_resp.text)
            if not isinstance(queries, list):
                queries = [topic]
        except (json.JSONDecodeError, TypeError):
            queries = [topic]

        yield self._make_event(
            task_id, context_id, TaskState.WORKING,
            f"Searching with {len(queries)} queries..."
        )

        all_findings: list[ResearchFinding] = []
        total_sources = 0

        for i, query in enumerate(queries[:num_queries]):
            yield self._make_event(
                task_id, context_id, TaskState.WORKING,
                f"Searching: '{query}' ({i+1}/{min(num_queries, len(queries))})"
            )

            search_results = await search_web(query, num_results=3)
            for sr in search_results:
                page = await fetch_page_content(sr.url)
                if page is None or len(page.text_content.strip()) < 100:
                    continue
                total_sources += 1

                yield self._make_event(
                    task_id, context_id, TaskState.WORKING,
                    f"Extracting facts from: {sr.title or sr.url[:60]}"
                )

                extract_prompt = EXTRACT_FACTS_PROMPT.format(
                    url=sr.url,
                    title=page.title,
                    content=page.text_content,
                    query=query,
                )
                try:
                    extract_resp = await client.generate(
                        prompt=extract_prompt,
                        system_prompt=RESEARCHER_SYSTEM_PROMPT,
                        agent_name="researcher",
                        temperature=0.3,
                    )
                    facts = json.loads(extract_resp.text)
                    if isinstance(facts, list):
                        for f in facts:
                            all_findings.append(ResearchFinding(
                                claim=f.get("claim", ""),
                                source_url=sr.url,
                                source_title=page.title or sr.title,
                                supporting_quote=f.get("supporting_quote", ""),
                                confidence=float(f.get("confidence", 0.5)),
                                search_query=query,
                            ))
                except Exception as e:
                    logger.warning(f"Fact extraction failed: {e}")

        # Deduplicate
        seen: set[str] = set()
        unique: list[ResearchFinding] = []
        for f in all_findings:
            key = f.claim.lower().strip()
            if key not in seen and f.claim and f.supporting_quote:
                seen.add(key)
                unique.append(f)

        output = ResearchOutput(
            findings=unique,
            queries_used=queries[:num_queries],
            total_sources_consulted=total_sources,
        )

        yield {
            "jsonrpc": "2.0",
            "id": new_id(),
            "result": {
                "taskId": task_id,
                "contextId": context_id,
                "status": {
                    "state": "COMPLETED",
                    "message": f"Found {len(unique)} findings from {total_sources} sources",
                },
                "artifacts": [
                    {
                        "parts": [{"kind": "data", "data": output.model_dump()}],
                        "mimeType": "application/json",
                    }
                ],
            },
        }
