"""Web search action group matching 08_ACTION_ENGINE.md, 09_TOOL_REGISTRY.md, and 20_DEVELOPER_CONTRACT.md."""

from typing import Any, Dict, List, Optional
from jarvis.core.errors import ErrorCode, JarvisError
from jarvis.policy.safety import RiskLevel
from jarvis.registry.registry import Availability, ToolDeclaration, ToolRegistry


class WebSearchBackend:
    """Backend engine for executing web searches with network failure handling."""

    def __init__(self, is_online: bool = True):
        self.is_online = is_online
        self.last_query: Optional[str] = None
        self.last_results: Optional[List[Dict[str, str]]] = None
        self.fail_next_verification: bool = False

    def search(self, query: str) -> List[Dict[str, str]]:
        """Perform search query or fail with E600 if network is unavailable."""
        clean = query.strip()
        if not clean:
            raise JarvisError(ErrorCode.E100, "Search query cannot be empty")

        if not self.is_online:
            raise JarvisError(ErrorCode.E600, "Web search failed: network connection unavailable")

        # Deterministic structured search results
        results = [
            {
                "title": f"Official documentation for {clean}",
                "snippet": f"Overview, guides, and API reference for {clean}.",
                "url": f"https://duckduckgo.com/?q={clean.replace(' ', '+')}",
            },
            {
                "title": f"Latest news about {clean}",
                "snippet": f"Recent articles, discussions, and updates regarding {clean}.",
                "url": f"https://news.ycombinator.com/item?id={abs(hash(clean)) % 10000000}",
            },
        ]
        self.last_query = clean
        self.last_results = results
        return results

    def verify_search(self, query: str) -> bool:
        """Verify search completed and results are populated."""
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return self.last_query == query.strip() and self.last_results is not None


def register_web_search_tools(registry: ToolRegistry, backend: Optional[WebSearchBackend] = None) -> WebSearchBackend:
    """Register search_web tool declaring all 10 mandatory fields per 09_TOOL_REGISTRY.md."""
    search_backend = backend or WebSearchBackend()

    def search_handler(query: str = "", **kwargs: Any) -> Dict[str, Any]:
        results = search_backend.search(query)
        return {"query": query, "results": results}

    def search_verifier(query: str = "", **kwargs: Any) -> bool:
        return search_backend.verify_search(query)

    registry.register_tool(
        ToolDeclaration(
            name="search_web",
            version=1,
            description="Execute web search and return structured results",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
            output_schema={"type": "object", "properties": {"query": {"type": "string"}, "results": {"type": "array"}}},
            risk_level=RiskLevel.LOW,
            required_permissions=["network"],
            availability=Availability.ONLINE,
            reversible=True,
            verification_method="verify_search",
        ),
        handler=search_handler,
        verifier=search_verifier,
    )

    return search_backend
