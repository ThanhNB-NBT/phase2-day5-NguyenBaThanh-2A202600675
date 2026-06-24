from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow


def test_benchmark_records_quality_and_failure_notes() -> None:
    def runner(query: str) -> ResearchState:
        return MultiAgentWorkflow().run(ResearchState(request=ResearchQuery(query=query)))

    _, metrics = run_benchmark("mock-multi", "search-error Compare agent workflows", runner)
    assert metrics.quality_score is not None
    assert "failures=" in metrics.notes
