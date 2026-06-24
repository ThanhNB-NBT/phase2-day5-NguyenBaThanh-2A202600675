"""Analyst agent skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.errors import AgentExecutionError
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = "analyst"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.analysis_notes`."""

        prompt = (
            f"Query: {state.request.query}\n"
            f"Research notes:\n{state.research_notes or 'No notes'}\n"
            "Extract key claims, weak evidence, and when multi-agent is useful."
        )
        try:
            response = self.llm_client.complete("You are the analyst agent.", prompt)
            state.analysis_notes = response.content
            usage = {
                "input_tokens": response.input_tokens or 0,
                "output_tokens": response.output_tokens or 0,
                "cost_usd": response.cost_usd or 0.0,
                "system_prompt": "You are the analyst agent.",
                "user_prompt": prompt,
            }
        except AgentExecutionError as exc:
            state.errors.append(f"analyst llm failed: {exc}")
            state.analysis_notes = "Fallback analysis: compare quality, latency, cost, citation coverage, and failure rate."
            usage = {
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
                "system_prompt": "You are the analyst agent.",
                "user_prompt": prompt,
            }

        state.agent_results.append(AgentResult(agent=AgentName.ANALYST, content=state.analysis_notes, metadata=usage))
        state.add_trace_event(
            self.name,
            {
                "has_analysis": bool(state.analysis_notes),
                "input_tokens": usage["input_tokens"],
                "output_tokens": usage["output_tokens"],
                "cost_usd": usage["cost_usd"],
            },
        )
        return state
