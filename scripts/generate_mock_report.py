"""Generate benchmark artifacts from mock runs."""

from __future__ import annotations

import argparse
import json
import os
from html import escape
from pathlib import Path
from typing import Any

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import AgentName, AgentResult, BenchmarkMetrics, ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.services.llm_client import LLMClient


QUERY = "Compare single-agent and multi-agent workflows"


def run_baseline(query: str) -> ResearchState:
    state = ResearchState(request=ResearchQuery(query=query))
    system_prompt = "You are a single research agent. Answer directly and mention trade-offs."
    response = LLMClient().complete(
        system_prompt,
        query,
    )
    state.final_answer = response.content
    state.agent_results.append(
        AgentResult(
            agent=AgentName.WRITER,
            content=state.final_answer,
            metadata={
                "input_tokens": response.input_tokens or 0,
                "output_tokens": response.output_tokens or 0,
                "cost_usd": response.cost_usd or 0.0,
                "system_prompt": system_prompt,
                "user_prompt": query,
            },
        )
    )
    state.add_trace_event(
        "baseline",
        {
            "input_tokens": response.input_tokens or 0,
            "output_tokens": response.output_tokens or 0,
            "cost_usd": response.cost_usd or 0.0,
        },
    )
    return state


def run_multi_agent(query: str) -> ResearchState:
    return MultiAgentWorkflow().run(ResearchState(request=ResearchQuery(query=query)))


def usage_from_state(state: ResearchState) -> dict[str, float]:
    input_tokens = 0.0
    output_tokens = 0.0
    cost = 0.0
    for event in state.trace:
        payload = event.get("payload", {})
        input_tokens += float(payload.get("input_tokens", 0) or 0)
        output_tokens += float(payload.get("output_tokens", 0) or 0)
        cost += float(payload.get("cost_usd", 0) or 0)
    return {"input_tokens": input_tokens, "output_tokens": output_tokens, "cost_usd": cost}


def timing_from_state(state: ResearchState) -> list[dict[str, Any]]:
    return [
        event["payload"]
        for event in state.trace
        if event.get("name") == "timing" and "duration_seconds" in event.get("payload", {})
    ]


def state_payload(state: ResearchState, metrics: BenchmarkMetrics) -> dict[str, Any]:
    usage = usage_from_state(state)
    return {
        "run_name": metrics.run_name,
        "latency_seconds": metrics.latency_seconds,
        "quality_score": metrics.quality_score,
        "estimated_cost_usd": usage["cost_usd"],
        "input_tokens": int(usage["input_tokens"]),
        "output_tokens": int(usage["output_tokens"]),
        "query": state.request.query,
        "final_answer": state.final_answer,
        "research_notes": state.research_notes,
        "analysis_notes": state.analysis_notes,
        "route_history": state.route_history,
        "sources": [source.model_dump() for source in state.sources],
        "trace": state.trace,
        "timing": timing_from_state(state),
        "errors": state.errors,
        "agent_results": [result.model_dump() for result in state.agent_results],
    }


def table_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def html_text(value: object) -> str:
    return escape(str(value)).replace("\n", "<br>")


def help_chip(text: str) -> str:
    return f'<span class="help" title="{escape(text)}">?</span>'


def duration_by_step(run: dict[str, Any]) -> dict[str, float]:
    durations: dict[str, float] = {}
    for item in run["timing"]:
        step = item["step"]
        durations[step] = durations.get(step, 0.0) + float(item["duration_seconds"])
    return durations


def agent_usage(run: dict[str, Any], agent: str) -> dict[str, Any]:
    for result in run["agent_results"]:
        if result["agent"] == agent:
            return result.get("metadata", {})
    return {}


def prompt_rows_for(run: dict[str, Any], label: str) -> str:
    rows = []
    for result in run["agent_results"]:
        metadata = result.get("metadata", {})
        system_prompt = metadata.get("system_prompt")
        user_prompt = metadata.get("user_prompt")
        if system_prompt or user_prompt:
            rows.append(
                f"""<tr>
                  <td>{escape(label)}</td>
                  <td>{escape(result["agent"])}</td>
                  <td><code>{html_text(system_prompt or "")}</code></td>
                  <td><code>{html_text(user_prompt or "")}</code></td>
                </tr>"""
            )
    return "\n".join(rows)


def render_html_report(data: dict[str, Any], json_name: str = "benchmark_report.json") -> str:
    runs = data["runs"]
    mode = data["mode"]
    baseline = runs[f"{mode}-baseline"]
    multi = runs[f"{mode}-multi-agent"]
    fallback = runs[f"{mode}-fallback"]
    badge = "Mock data" if mode == "mock" else "Real API data"
    durations = duration_by_step(multi)
    durations["baseline"] = float(baseline["latency_seconds"])

    metric_rows = "\n".join(
        f"""<tr>
          <td>{escape(run["run_name"])}</td>
          <td>{run["latency_seconds"]:.3f}</td>
          <td>{run["input_tokens"]}</td>
          <td>{run["output_tokens"]}</td>
          <td>{run["estimated_cost_usd"]:.6f}</td>
          <td>{run["quality_score"]:.1f}</td>
          <td>{len(run["sources"])}</td>
          <td>{len(run["errors"])}</td>
        </tr>"""
        for run in runs.values()
    )
    prompt_rows = prompt_rows_for(baseline, "Single Agent") + prompt_rows_for(multi, "Multi Agent")
    compare_rows = "\n".join(
        f"""<tr>
          <th>{label}</th>
          <td>{single}</td>
          <td>{multi_value}</td>
        </tr>"""
        for label, single, multi_value in [
            ("Latency", f'{baseline["latency_seconds"]:.3f}s', f'{multi["latency_seconds"]:.3f}s'),
            ("Input tokens", baseline["input_tokens"], multi["input_tokens"]),
            ("Output tokens", baseline["output_tokens"], multi["output_tokens"]),
            ("Estimated cost", f'${baseline["estimated_cost_usd"]:.6f}', f'${multi["estimated_cost_usd"]:.6f}'),
            ("Sources", len(baseline["sources"]), len(multi["sources"])),
            ("Trace steps", len(baseline["trace"]), len(multi["trace"])),
            ("Errors", len(baseline["errors"]), len(multi["errors"])),
            ("Routes", "baseline", ", ".join(multi["route_history"])),
        ]
    )
    timing_rows = "\n".join(
        f"<tr><td>{escape(item['step'])}</td><td>{item['duration_seconds']:.6f}</td></tr>"
        for item in multi["timing"]
    )
    flow_rows = "\n".join(
        f"""<tr>
          <td><b>{step}</b></td>
          <td>{purpose}</td>
          <td>{input_desc}</td>
          <td>{output_desc}</td>
          <td>{durations.get(step_key, 0.0):.6f}s</td>
          <td>{usage.get("input_tokens", 0)}</td>
          <td>{usage.get("output_tokens", 0)}</td>
          <td>${float(usage.get("cost_usd", 0.0) or 0.0):.6f}</td>
        </tr>"""
        for step, step_key, purpose, input_desc, output_desc, usage in [
            (
                "Baseline",
                "baseline",
                "Một agent trả lời trực tiếp, dùng làm mốc so sánh.",
                "Query gốc",
                "Final answer baseline",
                {
                    "input_tokens": baseline["input_tokens"],
                    "output_tokens": baseline["output_tokens"],
                    "cost_usd": baseline["estimated_cost_usd"],
                },
            ),
            (
                "Supervisor",
                "supervisor",
                "Kiểm tra state và chọn agent tiếp theo.",
                "ResearchState hiện tại",
                "Route history: " + ", ".join(multi["route_history"]),
                {},
            ),
            (
                "Researcher",
                "researcher",
                "Tìm nguồn và viết research notes.",
                "Query + max_sources",
                f"{len(multi['sources'])} sources, research_notes",
                {},
            ),
            (
                "Analyst",
                "analyst",
                "Phân tích notes thành insight/trade-off.",
                "research_notes",
                "analysis_notes",
                agent_usage(multi, "analyst"),
            ),
            (
                "Writer",
                "writer",
                "Tổng hợp final answer và gắn source references.",
                "research_notes + analysis_notes + sources",
                "final_answer",
                agent_usage(multi, "writer"),
            ),
        ]
    )
    trace_rows = "\n".join(
        f"<tr><td>{escape(event['name'])}</td><td><code>{escape(json.dumps(event['payload'], ensure_ascii=False))}</code></td></tr>"
        for event in multi["trace"]
    )
    source_items = "\n".join(
        f"<li><a href=\"{escape(source.get('url') or '#')}\">{escape(source['title'])}</a><span>{escape(source['snippet'])}</span></li>"
        for source in multi["sources"]
    )
    fallback_errors = "\n".join(f"<li>{escape(error)}</li>" for error in fallback["errors"])
    fallback_timing_rows = "\n".join(
        f"<tr><td>{escape(item['step'])}</td><td>{item['duration_seconds']:.6f}</td></tr>"
        for item in fallback["timing"]
    )

    return f"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(data.get("title", "Multi-Agent Benchmark Report"))}</title>
  <style>
    :root {{
      --bg: #f6f7f9;
      --panel: #fff;
      --text: #18202a;
      --muted: #657184;
      --line: #d9dee7;
      --accent: #0f766e;
      --bad: #b91c1c;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font: 15px/1.55 Arial, sans-serif; color: var(--text); background: var(--bg); }}
    header, main {{ max-width: 1240px; margin: 0 auto; padding: 24px; }}
    h1, h2 {{ margin: 0 0 12px; }}
    h1 {{ font-size: 30px; }}
    h2 {{ font-size: 20px; }}
    .muted {{ color: var(--muted); }}
    .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }}
    .compare {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
    .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 16px; margin: 14px 0; }}
    .metric strong {{ display: block; font-size: 28px; color: var(--accent); }}
    .lead {{ max-width: 900px; }}
    table {{ width: 100%; border-collapse: collapse; background: var(--panel); }}
    th, td {{ border: 1px solid var(--line); padding: 10px; vertical-align: top; text-align: left; }}
    th {{ background: #eef2f7; }}
    code {{ display: block; white-space: pre-wrap; color: var(--muted); }}
    ul {{ padding-left: 20px; }}
    .sources span {{ display: block; color: var(--muted); }}
    .errors li {{ color: var(--bad); }}
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 999px; background: #e6fffb; color: var(--accent); }}
    .help {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 18px;
      height: 18px;
      margin-left: 6px;
      border-radius: 50%;
      background: #dbeafe;
      color: #1d4ed8;
      font-size: 12px;
      font-weight: 700;
      cursor: help;
    }}
    @media (max-width: 840px) {{ .grid, .compare {{ grid-template-columns: 1fr; }} header, main {{ padding: 16px; }} }}
  </style>
</head>
<body>
  <header>
    <span class="badge">{badge}</span>
    <h1>{escape(data.get("title", "Multi-Agent Research Benchmark"))}</h1>
    <p class="muted lead">Report này chạy cùng một prompt qua hai luồng: baseline một agent và multi-agent có Supervisor, Researcher, Analyst, Writer. HTML render từ <code>reports/{escape(json_name)}</code>. Cost là ước tính từ token usage và rate cấu hình.</p>
  </header>
  <main>
    <section class="grid">
      <div class="panel metric"><span>Multi input tokens {help_chip("Tổng prompt tokens của các LLM call trong multi-agent run.")}</span><strong>{multi["input_tokens"]}</strong></div>
      <div class="panel metric"><span>Multi output tokens {help_chip("Tổng completion tokens do model sinh ra trong multi-agent run.")}</span><strong>{multi["output_tokens"]}</strong></div>
      <div class="panel metric"><span>Multi latency {help_chip("Wall-clock time từ lúc bắt đầu multi-agent run tới khi có final answer.")}</span><strong>{multi["latency_seconds"]:.3f}s</strong></div>
      <div class="panel metric"><span>Multi estimated cost {help_chip("Ước tính từ token usage nhân với LLM_INPUT/OUTPUT_COST_PER_1M_TOKENS.")}</span><strong>${multi["estimated_cost_usd"]:.6f}</strong></div>
    </section>

    <section class="panel">
      <h2>Benchmark Metrics {help_chip("Quality là điểm heuristic: final answer = 7, có sources +1, có errors trừ tối đa 2. Không phải judge LLM.")}</h2>
      <table>
        <thead><tr><th>Run</th><th>Latency {help_chip("Tổng thời gian chạy của run.")}</th><th>Input tokens {help_chip("Prompt tokens.")}</th><th>Output tokens {help_chip("Completion tokens.")}</th><th>Estimated cost {help_chip("Chi phí ước tính, không phải hóa đơn provider.")}</th><th>Quality {help_chip("Heuristic nội bộ để so sánh nhanh.")}</th><th>Sources {help_chip("Số nguồn Researcher thu được.")}</th><th>Errors {help_chip("Số lỗi đã được fallback và ghi lại.")}</th></tr></thead>
        <tbody>{metric_rows}</tbody>
      </table>
    </section>

    <section class="panel">
      <h2>Single vs Multi-Agent</h2>
      <p class="muted">Bảng này là phần đọc nhanh: multi-agent thường tốn thêm token/thời gian nhưng có nguồn, trace và chia vai rõ hơn.</p>
      <table>
        <thead><tr><th>Metric</th><th>Single Agent</th><th>Multi Agent</th></tr></thead>
        <tbody>{compare_rows}</tbody>
      </table>
    </section>

    <section class="panel">
      <h2>Prompts Used {help_chip("Các system/user prompts thực tế đã gửi vào LLM client cho baseline, analyst và writer.")}</h2>
      <table>
        <thead><tr><th>Run</th><th>Agent</th><th>System prompt</th><th>User prompt</th></tr></thead>
        <tbody>{prompt_rows}</tbody>
      </table>
    </section>

    <section class="compare">
      <div class="panel">
        <h2>Single Agent Output</h2>
        <p>{html_text(baseline["final_answer"])}</p>
      </div>
      <div class="panel">
        <h2>Multi Agent Output</h2>
        <p>{html_text(multi["final_answer"])}</p>
      </div>
    </section>

    <section class="panel">
      <h2>Luồng Chạy Dễ Đọc</h2>
      <p class="muted">Mỗi dòng dưới đây giải thích bước đó làm gì, nhận input gì, tạo output gì, tốn bao nhiêu thời gian và token.</p>
      <table>
        <thead>
          <tr>
            <th>Bước</th>
            <th>Làm gì</th>
            <th>Input</th>
            <th>Output</th>
            <th>Thời gian</th>
            <th>Input tokens</th>
            <th>Output tokens</th>
            <th>Cost</th>
          </tr>
        </thead>
        <tbody>{flow_rows}</tbody>
      </table>
    </section>

    <section class="panel">
      <h2>Thời Gian Theo Event</h2>
      <p class="muted">Đây là timing raw theo từng event được ghi trong trace của multi-agent.</p>
      <table><thead><tr><th>Step</th><th>Duration (s)</th></tr></thead><tbody>{timing_rows}</tbody></table>
    </section>

    <section class="panel">
      <h2>Trace Raw Của Multi-Agent</h2>
      <p class="muted">Dùng phần này để debug chi tiết route, token usage, source count và payload nội bộ.</p>
      <table><thead><tr><th>Event</th><th>Payload</th></tr></thead><tbody>{trace_rows}</tbody></table>
    </section>

    <section class="panel">
      <h2>Research Sources</h2>
      <ul class="sources">{source_items}</ul>
    </section>

    <section class="panel">
      <h2>Fallback Run</h2>
      <p class="muted">Run này cố tình dùng query lỗi để chứng minh workflow không chết giữa chừng.</p>
      <p><b>Query:</b> {html_text(fallback["query"])}</p>
      <p><b>Output:</b> {html_text(fallback["final_answer"])}</p>
      <table><thead><tr><th>Step</th><th>Duration (s)</th></tr></thead><tbody>{fallback_timing_rows}</tbody></table>
      <ul class="errors">{fallback_errors}</ul>
    </section>
  </main>
</body>
</html>
"""


def generate_report(
    use_mock: bool,
    query: str = QUERY,
    output_stem: str = "benchmark_report",
    title: str = "Multi-Agent Research Benchmark",
) -> None:
    # ponytail: one switch controls whether this spends real tokens.
    os.environ["USE_MOCK_LLM"] = "1" if use_mock else "0"
    get_settings.cache_clear()
    settings = get_settings()
    if not use_mock and not (settings.nvidia_api_key or settings.openai_api_key):
        raise SystemExit("Missing NVIDIA_API_KEY or OPENAI_API_KEY for --real report run.")
    mode = "mock" if use_mock else "real"

    baseline_state, baseline_metrics = run_benchmark(f"{mode}-baseline", query, run_baseline)
    multi_state, multi_metrics = run_benchmark(f"{mode}-multi-agent", query, run_multi_agent)
    fallback_state, fallback_metrics = run_benchmark(
        f"{mode}-fallback",
        "search-error Compare agent workflows",
        run_multi_agent,
    )

    metrics = [baseline_metrics, multi_metrics, fallback_metrics]
    metric_by_name = {item.run_name: item for item in metrics}
    baseline_key = f"{mode}-baseline"
    multi_key = f"{mode}-multi-agent"
    fallback_key = f"{mode}-fallback"
    data = {
        "mode": mode,
        "title": title,
        "query": query,
        "cost_note": "estimated from token usage and LLM_*_COST_PER_1M_TOKENS env vars",
        "runs": {
            baseline_key: state_payload(baseline_state, metric_by_name[baseline_key]),
            multi_key: state_payload(multi_state, metric_by_name[multi_key]),
            fallback_key: state_payload(fallback_state, metric_by_name[fallback_key]),
        },
    }

    report = render_markdown_report(metrics)
    report += "\n## Answer Comparison\n\n"
    report += "| Item | Single Agent | Multi Agent |\n|---|---|---|\n"
    report += f"| Final answer | {table_cell(baseline_state.final_answer)} | {table_cell(multi_state.final_answer)} |\n"
    report += f"| Input tokens | {data['runs'][baseline_key]['input_tokens']} | {data['runs'][multi_key]['input_tokens']} |\n"
    report += f"| Output tokens | {data['runs'][baseline_key]['output_tokens']} | {data['runs'][multi_key]['output_tokens']} |\n"
    report += f"| Estimated cost | {data['runs'][baseline_key]['estimated_cost_usd']:.6f} | {data['runs'][multi_key]['estimated_cost_usd']:.6f} |\n"
    report += f"| Sources | {len(baseline_state.sources)} | {len(multi_state.sources)} |\n"
    report += f"| Trace steps | {len(baseline_state.trace)} | {len(multi_state.trace)} |\n"
    report += f"| Errors | {len(baseline_state.errors)} | {len(multi_state.errors)} |\n"
    report += "\n## Failure Mode\n\n"
    report += "- `search-error ...` forces search failure and mock LLM failure in analyst/writer.\n"
    report += "- The workflow still returns fallback research notes, fallback analysis, final answer, trace, and visible errors.\n"
    report += f"- Fallback errors captured: {len(fallback_state.errors)}.\n"
    if use_mock:
        report += "- Real NVIDIA API is skipped because this run used `USE_MOCK_LLM=1`.\n"
    else:
        report += "- Real NVIDIA API was used for LLM calls; search data is still local mock data.\n"

    json_path = Path(f"reports/{output_stem}.json")
    md_path = Path(f"reports/{output_stem}.md")
    html_path = Path(f"reports/{output_stem}.html")
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(report, encoding="utf-8")
    html_path.write_text(render_html_report(data, json_path.name), encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    print(f"Wrote {html_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run baseline + multi-agent and generate report artifacts.")
    parser.add_argument("--real", action="store_true", help="Use the configured NVIDIA/OpenAI-compatible API.")
    args = parser.parse_args()
    mode = "real" if args.real else "mock"
    generate_report(use_mock=not args.real, output_stem=f"{mode}_benchmark_report")


if __name__ == "__main__":
    main()
