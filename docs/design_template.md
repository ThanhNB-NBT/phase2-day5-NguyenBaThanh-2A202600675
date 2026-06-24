# Design: Multi-Agent Research System

## Problem

Hệ thống nhận một câu hỏi nghiên cứu, chạy hai hướng xử lý để so sánh:

- Single-agent baseline: một LLM trả lời trực tiếp.
- Multi-agent workflow: Supervisor điều phối Researcher, Analyst, Writer.

Kết quả được ghi vào `reports/benchmark_report.json`, `reports/benchmark_report.md`, và `reports/benchmark_report.html`.

## Why Multi-Agent?

Single-agent nhanh và ít token hơn, nhưng khó trace từng bước và không có bước thu thập nguồn riêng. Multi-agent hữu ích khi câu hỏi cần:

- nguồn tham khảo rõ ràng,
- phân tích trước khi viết,
- trace để debug agent nào làm gì,
- fallback khi search hoặc LLM call lỗi.

## Agent Roles

| Agent | Responsibility | Input | Output | Failure mode |
|---|---|---|---|---|
| Supervisor | Chọn route tiếp theo và stop khi đủ dữ liệu | `ResearchState` | `route_history`, trace route | Max iterations thì ép writer fallback |
| Researcher | Lấy mock sources và viết research notes | query, `max_sources` | `sources`, `research_notes` | Search lỗi thì ghi `errors`, dùng notes low-confidence |
| Analyst | Tóm claim, điểm yếu evidence, trade-off | `research_notes` | `analysis_notes`, token usage | LLM lỗi thì dùng fallback analysis |
| Writer | Viết final answer và source references | notes, analysis, sources | `final_answer`, token usage | LLM lỗi thì dùng fallback answer |

## Shared State

`ResearchState` là nguồn dữ liệu chung:

- `request`: query, audience, max_sources.
- `iteration`: số lần supervisor route.
- `route_history`: đường đi thực tế của workflow.
- `sources`: tài liệu Researcher tìm được.
- `research_notes`, `analysis_notes`, `final_answer`: output từng stage.
- `agent_results`: output từng agent kèm metadata token/cost.
- `trace`: event route, usage, timing.
- `errors`: lỗi đã fallback được.

## Routing Policy

```text
supervisor
  -> researcher nếu chưa có research_notes
  -> analyst nếu chưa có analysis_notes
  -> writer nếu chưa có final_answer
  -> done nếu đã có final_answer
```

Nếu quá `MAX_ITERATIONS`, workflow ghi lỗi và ép writer fallback.

## Guardrails

- Max iterations: `MAX_ITERATIONS`, mặc định 6.
- Timeout: `TIMEOUT_SECONDS`, mặc định 60 giây cho API call.
- Rate limit: `LLM_REQUESTS_PER_MINUTE`, mặc định 39 request/phút.
- Retry: mỗi LLM request thử tối đa 2 lần.
- Fallback: search lỗi, analyst lỗi, writer lỗi vẫn tạo output.
- Validation: Pydantic schemas cho query, source, agent result, benchmark metrics.

## Benchmark Plan

Query chính:

```text
Compare single-agent and multi-agent workflows
```

Runs:

- `mock-baseline` hoặc `real-baseline`
- `mock-multi-agent` hoặc `real-multi-agent`
- `mock-fallback` hoặc `real-fallback`

Metrics:

- latency,
- input tokens,
- output tokens,
- estimated cost,
- quality score heuristic,
- number of sources,
- number of errors,
- route history,
- trace timing by step.

Cost được ước tính từ token usage:

```text
cost = (input_tokens * LLM_INPUT_COST_PER_1M_TOKENS
      + output_tokens * LLM_OUTPUT_COST_PER_1M_TOKENS) / 1_000_000
```
