# Peer Review Rubric

| Criteria | Evidence in this repo | Score |
|---|---|---:|
| Role clarity | Supervisor routes; Researcher collects sources; Analyst extracts trade-offs; Writer synthesizes answer | 0-2 |
| State design | `ResearchState` stores request, route history, sources, notes, final answer, trace, errors | 0-2 |
| Failure guard | Max iterations, timeout, retry, 39 RPM limit, mock fallback scenarios | 0-2 |
| Benchmark | `scripts/generate_report.py` compares baseline vs multi-agent with latency, token, cost, sources, errors | 0-2 |
| Trace explanation | `reports/benchmark_report.html` shows trace payload and time by step | 0-2 |

## Suggested Score

9/10 for the current implementation.

Missing point: search is still local mock data, not a real web/search provider. This is intentional for cheaper debugging and stable lab runs.

## Feedback Format

```text
Strength:
- Workflow is traceable from supervisor route to final answer.
- Report compares single-agent and multi-agent with token, cost, latency, output, sources, and errors.

Risk / failure mode:
- Estimated cost depends on configured token rates, not provider billing response.
- Search source is local mock, so source coverage is structural rather than live web coverage.

One concrete improvement:
- Add a real search provider behind SearchClient while keeping current mock fallback.

Score:
- 9/10
```
