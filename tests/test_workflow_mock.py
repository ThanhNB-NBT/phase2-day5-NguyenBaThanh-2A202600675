from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow


def test_mock_workflow_reaches_final_answer() -> None:
    state = ResearchState(request=ResearchQuery(query="Compare single-agent and multi-agent workflows"))
    result = MultiAgentWorkflow().run(state)
    assert result.final_answer
    assert result.research_notes
    assert result.analysis_notes
    assert "researcher" in result.route_history


def test_mock_workflow_falls_back_when_search_fails() -> None:
    state = ResearchState(request=ResearchQuery(query="search-error Compare agent workflows"))
    result = MultiAgentWorkflow().run(state)
    assert result.final_answer
    assert result.errors
    assert "No external sources found" in (result.research_notes or "")
