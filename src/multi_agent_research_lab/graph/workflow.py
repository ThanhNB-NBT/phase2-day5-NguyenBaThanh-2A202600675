"""LangGraph workflow skeleton."""

from time import perf_counter

from multi_agent_research_lab.agents import AnalystAgent, ResearcherAgent, SupervisorAgent, WriterAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.state import ResearchState


class MultiAgentWorkflow:
    """Builds and runs the multi-agent graph.

    Keep orchestration here; keep agent internals in `agents/`.
    """

    def __init__(self) -> None:
        self.supervisor = SupervisorAgent()
        self.agents = {
            "researcher": ResearcherAgent(),
            "analyst": AnalystAgent(),
            "writer": WriterAgent(),
        }

    def build(self) -> object:
        """Return the local graph shape used by `run`."""

        return {"supervisor": list(self.agents)}

    def run(self, state: ResearchState) -> ResearchState:
        """Execute the workflow and return final state."""

        self.build()
        max_iterations = get_settings().max_iterations
        while state.iteration < max_iterations:
            started = perf_counter()
            state = self.supervisor.run(state)
            state.add_trace_event("timing", {"step": "supervisor", "duration_seconds": perf_counter() - started})
            route = state.route_history[-1]
            if route == "done":
                return state
            started = perf_counter()
            state = self.agents[route].run(state)
            state.add_trace_event("timing", {"step": route, "duration_seconds": perf_counter() - started})

        # ponytail: one final writer pass is cheaper than a second routing system.
        if not state.final_answer:
            state.errors.append("Workflow hit max iterations; writer fallback executed")
            started = perf_counter()
            state = self.agents["writer"].run(state)
            state.add_trace_event("timing", {"step": "writer", "duration_seconds": perf_counter() - started})
        return state
