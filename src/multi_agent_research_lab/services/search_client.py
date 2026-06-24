"""Search client abstraction for ResearcherAgent."""

from multi_agent_research_lab.core.schemas import SourceDocument


class SearchClient:
    """Mockable search client.

    The lab can run without paid search; real providers can replace this class later.
    """

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        """Search for documents relevant to a query.

        Returns local mock data so tests cover the whole flow before real API calls.
        """

        lowered = query.lower()
        if "search-error" in lowered:
            raise RuntimeError("Mock search failure requested by query")
        if "no-source" in lowered:
            return []

        docs = [
            SourceDocument(
                title="Building Effective Agents",
                url="https://www.anthropic.com/engineering/building-effective-agents",
                snippet="Agent systems work best when workflows are simple, observable, and bounded.",
            ),
            SourceDocument(
                title="OpenAI Agents Orchestration",
                url="https://developers.openai.com/",
                snippet="Handoffs and orchestration help split specialized work across agents.",
            ),
            SourceDocument(
                title="LangGraph Concepts",
                url="https://langchain-ai.github.io/langgraph/concepts/",
                snippet="Stateful graphs make agent routing and trace inspection explicit.",
            ),
        ]
        return docs[:max_results]
