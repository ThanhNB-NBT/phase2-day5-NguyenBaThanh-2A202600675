"""Writer agent skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.errors import AgentExecutionError
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes."""

    name = "writer"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.final_answer`."""

        source_lines = [f"[{i}] {doc.title} - {doc.url or 'local mock'}" for i, doc in enumerate(state.sources, 1)]
        prompt = (
            f"Query: {state.request.query}\n"
            f"Research:\n{state.research_notes}\n"
            f"Analysis:\n{state.analysis_notes}\n"
            f"Sources:\n{chr(10).join(source_lines) or 'No sources'}\n"
            "Write a concise final answer with source references when available."
        )
        try:
            response = self.llm_client.complete("You are the writer agent producing the final answer.", prompt)
            answer = response.content
            usage = {
                "input_tokens": response.input_tokens or 0,
                "output_tokens": response.output_tokens or 0,
                "cost_usd": response.cost_usd or 0.0,
                "system_prompt": "You are the writer agent producing the final answer.",
                "user_prompt": prompt,
            }
        except AgentExecutionError as exc:
            state.errors.append(f"writer llm failed: {exc}")
            answer = "Fallback answer: the workflow completed with degraded confidence because one API step failed."
            usage = {
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
                "system_prompt": "You are the writer agent producing the final answer.",
                "user_prompt": prompt,
            }

        if source_lines:
            answer = f"{answer}\n\nSources:\n" + "\n".join(source_lines)
        state.final_answer = answer
        state.agent_results.append(AgentResult(agent=AgentName.WRITER, content=state.final_answer, metadata=usage))
        state.add_trace_event(
            self.name,
            {
                "has_final_answer": bool(state.final_answer),
                "input_tokens": usage["input_tokens"],
                "output_tokens": usage["output_tokens"],
                "cost_usd": usage["cost_usd"],
            },
        )
        return state
