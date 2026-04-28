"""Advanced search tool for Rikugan.

Provides sophisticated search capabilities including function similarity,
code pattern matching, string reference search, and combined criteria search.
"""

from __future__ import annotations

from typing import Any

from ..core.advanced_search import AdvancedSearchEngine, SearchCriteria
from ..core.logging import log_info
from ..tools.base import Tool, ToolDefinition


class AdvancedSearchTool(Tool):
    """Advanced search with function similarity detection."""

    name = "advanced_search"
    description = "Search functions by similarity, patterns, strings, imports, and more"
    parameters = {
        "criteria": {
            "description": "Search criteria type",
            "type": "string",
            "default": "similarity",
            "enum": [
                "similarity",
                "pattern",
                "strings",
                "imports",
                "callees",
                "callers",
                "size",
                "complexity",
                "name",
                "combined",
            ],
        },
        "query": {
            "description": "Search query (function name/address, pattern, string, etc.)",
            "type": "string",
            "required": False,
        },
        "min_score": {
            "description": "Minimum relevance score (0.0-1.0, default: 0.3)",
            "type": "float",
            "default": 0.3,
            "min": 0.0,
            "max": 1.0,
        },
        "max_results": {
            "description": "Maximum results to return (default: 50)",
            "type": "integer",
            "default": 50,
            "min": 1,
            "max": 500,
        },
        "threshold": {
            "description": "Similarity threshold for similarity search (0.0-1.0, default: 0.3)",
            "type": "float",
            "default": 0.3,
            "min": 0.0,
            "max": 1.0,
        },
        "min_size": {
            "description": "Minimum function size for size search",
            "type": "integer",
            "default": 0,
        },
        "max_size": {
            "description": "Maximum function size for size search",
            "type": "integer",
            "default": 0,
        },
        "min_complexity": {
            "description": "Minimum complexity for complexity search",
            "type": "integer",
            "default": 0,
        },
        "max_complexity": {
            "description": "Maximum complexity for complexity search",
            "type": "integer",
            "default": 0,
        },
    }

    def execute(
        self,
        criteria: str = "similarity",
        query: str = "",
        min_score: float = 0.3,
        max_results: int = 50,
        threshold: float = 0.3,
        min_size: int = 0,
        max_size: int = 0,
        min_complexity: int = 0,
        max_complexity: int = 0,
    ) -> str:
        """Execute advanced search.

        Args:
            criteria: Type of search
            query: Search query
            min_score: Minimum relevance score
            max_results: Maximum results
            threshold: Similarity threshold
            min_size: Minimum size
            max_size: Maximum size
            min_complexity: Minimum complexity
            max_complexity: Maximum complexity

        Returns:
            Search results
        """
        # Import host-specific functions
        try:
            if self._is_ida():
                from ..ida.tools.ida_search import IDASearchCollector

                host_collector = IDASearchCollector()
            else:
                from ..binja.tools.binja_search import BinaryNinjaSearchCollector

                host_collector = BinaryNinjaSearchCollector()
        except ImportError:
            return "Error: Host-specific search collector not available"

        # Build search index
        log_info("Building search index...")
        engine = AdvancedSearchEngine()

        functions = host_collector.get_functions()
        for func in functions:
            engine.index_function(func)

        log_info(f"Indexed {len(functions)} functions")

        # Execute search
        search_criteria = SearchCriteria(criteria)
        kwargs = {}

        if criteria == "similarity":
            kwargs["threshold"] = threshold
        elif criteria == "size":
            kwargs["min_size"] = min_size
            kwargs["max_size"] = max_size
        elif criteria == "complexity":
            kwargs["min_complexity"] = min_complexity
            kwargs["max_complexity"] = max_complexity

        results = engine.search(
            criteria=search_criteria, query=query, min_score=min_score, max_results=max_results, **kwargs
        )

        # Format results
        return self._format_results(results, criteria, query)

    def _format_results(self, results: list[Any], criteria: str, query: str) -> str:
        """Format search results for display."""
        lines = []
        lines.append("=== Advanced Search Results ===")
        lines.append(f"Criteria: {criteria}")
        if query:
            lines.append(f"Query: {query}")
        lines.append(f"Found: {len(results)} result(s)")
        lines.append("")

        if not results:
            lines.append("No matching functions found")
            return "\n".join(lines)

        for i, result in enumerate(results, 1):
            lines.append(f"{i}. {result.name} (0x{result.address:x})")
            lines.append(f"   Score: {result.score:.2f}")
            lines.append(f"   Reason: {result.reason}")

            if result.metadata:
                metadata_items = []
                for key, value in result.metadata.items():
                    if isinstance(value, list):
                        value_str = ", ".join(str(v) for v in value[:5])
                        if len(value) > 5:
                            value_str += f" ... ({len(value)} total)"
                    else:
                        value_str = str(value)
                    metadata_items.append(f"{key}: {value_str}")

                if metadata_items:
                    lines.append(f"   Details: {', '.join(metadata_items)}")

            lines.append("")

        return "\n".join(lines)

    def _is_ida(self) -> bool:
        """Check if running in IDA Pro environment."""
        try:
            import ida_kernwin

            return True
        except ImportError:
            return False


def get_tool_definition() -> ToolDefinition:
    """Return tool definition for Rikugan tool registry."""
    return ToolDefinition(
        name=AdvancedSearchTool.name,
        description=AdvancedSearchTool.description,
        parameters=AdvancedSearchTool.parameters,
        function=AdvancedSearchTool.execute,
    )
