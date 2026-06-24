"""Benchmark skeleton for single-agent vs multi-agent."""

from time import perf_counter
from typing import Callable

from multi_agent_research_lab.core.schemas import BenchmarkMetrics
from multi_agent_research_lab.core.state import ResearchState


Runner = Callable[[str], ResearchState]


def run_benchmark(run_name: str, query: str, runner: Runner) -> tuple[ResearchState, BenchmarkMetrics]:
    """Measure a runner and return simple lab metrics."""

    started = perf_counter()
    state = runner(query)
    latency = perf_counter() - started
    source_count = len(state.sources)
    has_answer = bool(state.final_answer)
    input_tokens = 0
    output_tokens = 0
    cost = 0.0
    for event in state.trace:
        payload = event.get("payload", {})
        input_tokens += int(payload.get("input_tokens", 0) or 0)
        output_tokens += int(payload.get("output_tokens", 0) or 0)
        cost += float(payload.get("cost_usd", 0) or 0)
    quality = 7.0 if has_answer else 0.0
    if source_count:
        quality += 1.0
    if state.errors:
        quality -= min(2.0, float(len(state.errors)))

    # ponytail: notes carry extra rubric metrics without changing the public schema.
    notes = (
        f"in={input_tokens}; out={output_tokens}; sources={source_count}; "
        f"failures={len(state.errors)}; routes={','.join(state.route_history) or 'baseline'}"
    )
    metrics = BenchmarkMetrics(
        run_name=run_name,
        latency_seconds=latency,
        estimated_cost_usd=cost,
        quality_score=max(0.0, min(10.0, quality)),
        notes=notes,
    )
    return state, metrics
