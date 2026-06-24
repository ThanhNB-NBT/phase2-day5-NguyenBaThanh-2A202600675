"""Supervisor / router skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.state import ResearchState


class SupervisorAgent(BaseAgent):
    """Decides which worker should run next and when to stop."""

    name = "supervisor"

    def run(self, state: ResearchState) -> ResearchState:
        """Pick the next route from the missing state fields."""

        if state.iteration >= get_settings().max_iterations:
            route = "writer" if not state.final_answer else "done"
            state.errors.append("Max iterations reached; forcing fallback route")
        elif not state.research_notes:
            route = "researcher"
        elif not state.analysis_notes:
            route = "analyst"
        elif not state.final_answer:
            route = "writer"
        else:
            route = "done"

        state.record_route(route)
        state.add_trace_event(self.name, {"route": route, "iteration": state.iteration})
        return state
