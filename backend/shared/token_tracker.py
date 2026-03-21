"""Token usage tracking and cost estimation."""

from __future__ import annotations

from dataclasses import dataclass, field
from shared.models import TokenUsage


# Gemini 2.5 Flash pricing (for display purposes — free tier costs $0)
GEMINI_FLASH_INPUT_PRICE_PER_M = 0.15   # $/M input tokens
GEMINI_FLASH_OUTPUT_PRICE_PER_M = 0.60  # $/M output tokens


@dataclass
class TokenTracker:
    """Aggregates token usage across pipeline runs."""

    entries: list[TokenUsage] = field(default_factory=list)

    def record(self, usage: TokenUsage) -> None:
        self.entries.append(usage)

    def total_input_tokens(self) -> int:
        return sum(e.input_tokens for e in self.entries)

    def total_output_tokens(self) -> int:
        return sum(e.output_tokens for e in self.entries)

    def estimated_cost(self) -> float:
        """What this would cost at paid Gemini rates (for demo display)."""
        input_cost = self.total_input_tokens() / 1_000_000 * GEMINI_FLASH_INPUT_PRICE_PER_M
        output_cost = self.total_output_tokens() / 1_000_000 * GEMINI_FLASH_OUTPUT_PRICE_PER_M
        return input_cost + output_cost

    def by_agent(self) -> dict[str, dict[str, int]]:
        result: dict[str, dict[str, int]] = {}
        for e in self.entries:
            if e.agent not in result:
                result[e.agent] = {"input_tokens": 0, "output_tokens": 0, "calls": 0}
            result[e.agent]["input_tokens"] += e.input_tokens
            result[e.agent]["output_tokens"] += e.output_tokens
            result[e.agent]["calls"] += 1
        return result

    def to_dict(self) -> dict:
        return {
            "total_input_tokens": self.total_input_tokens(),
            "total_output_tokens": self.total_output_tokens(),
            "estimated_cost_usd": round(self.estimated_cost(), 6),
            "by_agent": self.by_agent(),
        }
