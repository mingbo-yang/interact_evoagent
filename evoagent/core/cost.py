"""CostTracker — track token usage and compute cost per model."""

from dataclasses import dataclass, field

# Default pricing per 1k tokens (USD). Update as vendor pricing changes.
DEFAULT_PRICING: dict[str, dict[str, float]] = {
    "deepseek-chat":     {"input": 0.00027, "output": 0.0011},
    "deepseek-reasoner": {"input": 0.00055, "output": 0.00219},
    "gpt-4o":            {"input": 0.005,   "output": 0.015},
    "gpt-4o-mini":       {"input": 0.00015, "output": 0.0006},
}


@dataclass
class CostSnapshot:
    """Accumulated token usage and cost for a single run."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    calls: int = 0
    by_model: dict[str, dict] = field(default_factory=dict)

    def add_call(self, model: str, prompt_tokens: int = 0, completion_tokens: int = 0,
                 input_price: float = 0.0, output_price: float = 0.0) -> None:
        """Record one LLM call and compute its cost.

        If prices are 0, falls back to DEFAULT_PRICING for known models.
        """
        if input_price == 0.0 and output_price == 0.0:
            defaults = DEFAULT_PRICING.get(model, {})
            input_price = defaults.get("input", 0.0)
            output_price = defaults.get("output", 0.0)

        call_cost = (prompt_tokens / 1000) * input_price + (completion_tokens / 1000) * output_price

        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.total_tokens += prompt_tokens + completion_tokens
        self.cost_usd += call_cost
        self.calls += 1

        if model not in self.by_model:
            self.by_model[model] = {"prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0, "calls": 0}
        self.by_model[model]["prompt_tokens"] += prompt_tokens
        self.by_model[model]["completion_tokens"] += completion_tokens
        self.by_model[model]["cost_usd"] += call_cost
        self.by_model[model]["calls"] += 1

    def summary(self) -> dict:
        """Return a summary dict for inclusion in AgentResult.metadata."""
        return {
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "calls": self.calls,
            "by_model": {
                m: {"prompt": d["prompt_tokens"], "completion": d["completion_tokens"],
                    "cost_usd": round(d["cost_usd"], 6), "calls": d["calls"]}
                for m, d in self.by_model.items()
            },
        }
