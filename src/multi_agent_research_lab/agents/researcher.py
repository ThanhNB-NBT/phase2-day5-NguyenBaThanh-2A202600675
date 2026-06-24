"""Researcher agent skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.search_client import SearchClient


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = "researcher"

    def __init__(self, search_client: SearchClient | None = None) -> None:
        self.search_client = search_client or SearchClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.sources` and `state.research_notes`."""

        try:
            state.sources = self.search_client.search(state.request.query, state.request.max_sources)
        except Exception as exc:
            # Mock error path: keep the workflow alive and make the failure visible.
            state.errors.append(f"researcher search failed: {exc}")
            state.sources = []

        if state.sources:
            bullets = [f"- {doc.title}: {doc.snippet}" for doc in state.sources]
            state.research_notes = "\n".join(bullets)
        else:
            state.research_notes = "No external sources found; continue with general knowledge and mark low confidence."

        state.agent_results.append(AgentResult(agent=AgentName.RESEARCHER, content=state.research_notes))
        state.add_trace_event(self.name, {"sources": len(state.sources), "errors": len(state.errors)})
        return state
