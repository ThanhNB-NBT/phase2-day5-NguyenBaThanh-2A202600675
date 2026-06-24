# Lab Guide: Multi-Agent Research System

## Goal

Lab này so sánh single-agent baseline với multi-agent workflow cho cùng một câu hỏi nghiên cứu. Một lệnh report sẽ chạy cả hai bên, tạo dữ liệu thống kê và HTML để xem trace.

## What Was Implemented

- Single-agent baseline trong `src/multi_agent_research_lab/cli.py`.
- NVIDIA/OpenAI-compatible LLM client trong `src/multi_agent_research_lab/services/llm_client.py`.
- Mock search client trong `src/multi_agent_research_lab/services/search_client.py`.
- Supervisor, Researcher, Analyst, Writer agents trong `src/multi_agent_research_lab/agents/`.
- Workflow route trong `src/multi_agent_research_lab/graph/workflow.py`.
- Benchmark/report generator trong `scripts/generate_report.py`.

## Run Mock Report

Mock mode không tốn token và dùng để test luồng, fallback, trace.

```powershell
$env:UV_CACHE_DIR='E:\AI20K-lab\phase2-day5-NguyenBaThanh-2A202600675\.uv-cache'
uv run python scripts\generate_report.py
```

## Run Real API Report

Lệnh này chạy cả baseline, multi-agent, fallback test và generate report.

```powershell
$env:UV_CACHE_DIR='E:\AI20K-lab\phase2-day5-NguyenBaThanh-2A202600675\.uv-cache'
$env:NVIDIA_API_KEY='YOUR_NVIDIA_KEY'
$env:USE_MOCK_LLM='0'
$env:OPENAI_BASE_URL='https://integrate.api.nvidia.com/v1'
$env:OPENAI_MODEL='meta/llama-3.1-8b-instruct'
$env:LLM_REQUESTS_PER_MINUTE='39'
$env:LLM_INPUT_COST_PER_1M_TOKENS='0.15'
$env:LLM_OUTPUT_COST_PER_1M_TOKENS='0.15'

uv run python scripts\generate_report.py --real
```

Nếu model NVIDIA bạn dùng có giá khác, đổi hai biến `LLM_INPUT_COST_PER_1M_TOKENS` và `LLM_OUTPUT_COST_PER_1M_TOKENS`.

## Report Files

Sau khi chạy, mở:

- `reports/benchmark_report.html`: xem dashboard HTML.
- `reports/benchmark_report.json`: dữ liệu gốc của report.
- `reports/benchmark_report.md`: bản Markdown nộp nhanh.

HTML hiển thị:

- input/output tokens,
- estimated cost,
- latency,
- output thực tế của single-agent và multi-agent,
- sources,
- trace payload,
- time by step,
- errors và fallback output.

## Baseline vs Multi-Agent

Baseline:

- một LLM call,
- ít bước hơn,
- nhanh và rẻ hơn,
- ít trace hơn.

Multi-agent:

- Researcher tạo sources và notes,
- Analyst tạo analysis,
- Writer tạo final answer kèm references,
- có route history, timing, trace,
- thường tốn token hơn.

## Failure Scenarios

Report luôn chạy thêm fallback query:

```text
search-error Compare agent workflows
```

Case này ép search lỗi. Workflow vẫn phải:

- ghi lỗi vào `errors`,
- tạo fallback research notes,
- tạo fallback analysis nếu LLM lỗi,
- tạo fallback final answer,
- giữ trace để debug.

## Exit Ticket

1. Nên dùng multi-agent khi task cần nguồn, phân tích, synthesis, trace và fallback rõ ràng.
2. Không nên dùng multi-agent cho câu hỏi ngắn hoặc tác vụ đơn giản vì overhead token, latency và orchestration cao hơn baseline.
