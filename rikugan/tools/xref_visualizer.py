"""Cross-reference visualizer tool for Rikugan.

Provides interactive call graph visualization, function relationship mapping,
and complexity analysis for both IDA Pro and Binary Ninja.
"""

from __future__ import annotations

import json
from typing import Any, Tuple

from ..core.logging import log_info
from ..core.xref import XRefGraph, build_xref_graph
from ..tools.base import Tool, ToolDefinition


class XRefVisualizerTool(Tool):
    """Interactive cross-reference visualization and analysis tool."""

    name = "xref_visualizer"
    description = "Visualize cross-references, call graphs, and function relationships"
    parameters = {
        "focus_function": {
            "description": "Function address or name to focus analysis on",
            "type": "string",
            "required": False,
        },
        "max_depth": {
            "description": "Maximum depth for call path analysis (default: 10)",
            "type": "integer",
            "default": 10,
            "min": 1,
            "max": 20,
        },
        "similarity_threshold": {
            "description": "Threshold for finding similar functions (0.0-1.0, default: 0.7)",
            "type": "float",
            "default": 0.7,
            "min": 0.0,
            "max": 1.0,
        },
        "format": {
            "description": "Output format: 'text', 'json', 'graphviz', 'html'",
            "type": "string",
            "default": "text",
            "enum": ["text", "json", "graphviz", "html"],
        },
    }

    def execute(
        self, focus_function: str = "", max_depth: int = 10, similarity_threshold: float = 0.7, format: str = "text"
    ) -> str:
        """Execute cross-reference visualization and analysis.

        Args:
            focus_function: Function to focus analysis on
            max_depth: Maximum depth for path finding
            similarity_threshold: Similarity threshold for function matching
            format: Output format

        Returns:
            Formatted xref analysis results
        """
        # Import host-specific functions
        try:
            if self._is_ida():
                from ..ida.tools.ida_xref import IDAXRefCollector

                collector = IDAXRefCollector()
            else:
                from ..binja.tools.binja_xref import BinaryNinjaXRefCollector

                collector = BinaryNinjaXRefCollector()
        except ImportError:
            return "Error: Host-specific xref collector not available"

        # Collect xref data
        log_info("Collecting cross-reference data...")
        host_functions = collector.get_functions()
        host_xrefs = collector.get_xrefs()

        # Build graph
        graph = build_xref_graph(host_functions, host_xrefs)
        log_info(f"Built xref graph: {len(graph.functions)} functions, {len(graph.xrefs)} xrefs")

        # Generate output based on focus and format
        if focus_function:
            return self._analyze_focus_function(graph, focus_function, max_depth, similarity_threshold, format)
        else:
            return self._generate_overview(graph, format)

    def _analyze_focus_function(
        self, graph: XRefGraph, focus_function: str, max_depth: int, similarity_threshold: float, format: str
    ) -> str:
        """Analyze a specific function and its relationships."""
        # Resolve function address
        func_addr = self._resolve_function_address(graph, focus_function)
        if func_addr is None:
            return f"Error: Function '{focus_function}' not found"

        func = graph.functions.get(func_addr)
        if not func:
            return f"Error: Function data not available for '{focus_function}'"

        lines = []
        lines.append(f"=== Cross-Reference Analysis: {func.name} (0x{func_addr:x}) ===")
        lines.append(f"Size: {func.size} bytes")
        lines.append(f"Complexity Score: {func.complexity_score}")
        lines.append("")

        # Callers
        callers = graph.get_callers(func_addr)
        lines.append(f"Callers ({len(callers)}):")
        for caller_addr in callers[:20]:  # Limit output
            caller = graph.functions.get(caller_addr)
            if caller:
                lines.append(f"  - 0x{caller_addr:x}: {caller.name}")

        # Callees
        callees = graph.get_callees(func_addr)
        lines.append(f"\nCallees ({len(callees)}):")
        for callee_addr in callees[:20]:
            callee = graph.functions.get(callee_addr)
            if callee:
                lines.append(f"  - 0x{callee_addr:x}: {callee.name}")

        # Similar functions
        similar = graph.find_similar_functions(func_addr, similarity_threshold)
        lines.append(f"\nSimilar Functions (threshold={similarity_threshold:.2f}):")
        for similar_addr, similarity in similar[:10]:
            similar_func = graph.functions.get(similar_addr)
            if similar_func:
                lines.append(f"  - 0x{similar_addr:x}: {similar_func.name} (similarity={similarity:.2f})")

        # Call paths
        if format in ["graphviz", "html"]:
            lines.append("\n" + self._generate_call_paths_dot(graph, func_addr, max_depth))

        if format == "json":
            return self._to_json(graph, func_addr, callers, callees, similar)
        elif format == "graphviz":
            return "\n".join(lines) + "\n" + self._generate_graphviz_dot(graph)
        else:
            return "\n".join(lines)

    def _generate_overview(self, graph: XRefGraph, format: str) -> str:
        """Generate overview of the entire xref graph."""
        metrics = graph.calculate_complexity_metrics()

        lines = []
        lines.append("=== Cross-Reference Overview ===")
        lines.append(f"Total Functions: {metrics['total_functions']}")
        lines.append(f"Entry Points: {metrics['entry_points']}")
        lines.append(f"Leaf Functions: {metrics['leaf_functions']}")
        lines.append(f"Average Complexity: {metrics['avg_complexity']:.2f}")

        if metrics["most_complex"]:
            most_complex = metrics["most_complex"]
            lines.append("\nMost Complex Function:")
            lines.append(f"  - 0x{most_complex.address:x}: {most_complex.name}")
            lines.append(f"    Complexity: {most_complex.complexity_score}")

        lines.append("\nComplexity Distribution:")
        lines.append(f"  Low (0-10 xrefs): {metrics['complexity_distribution']['low']}")
        lines.append(f"  Medium (11-50): {metrics['complexity_distribution']['medium']}")
        lines.append(f"  High (51-100): {metrics['complexity_distribution']['high']}")
        lines.append(f"  Very High (100+): {metrics['complexity_distribution']['very_high']}")

        if format == "json":
            return self._overview_to_json(graph, metrics)
        elif format == "graphviz":
            return "\n".join(lines) + "\n" + self._generate_overview_dot(graph)
        else:
            return "\n".join(lines)

    def _resolve_function_address(self, graph: XRefGraph, identifier: str) -> int | None:
        """Resolve function address from name or hex address."""
        # Try as hex address first
        try:
            addr = int(identifier, 16)
            if addr in graph.functions:
                return addr
        except ValueError:
            pass

        # Try as function name
        return graph.name_to_address.get(identifier)

    def _generate_call_paths_dot(self, graph: XRefGraph, func_addr: int, max_depth: int) -> str:
        """Generate GraphViz DOT format for call paths."""
        lines = []
        lines.append("digraph call_paths {")
        lines.append('  node [shape=box, style="rounded,filled", fillcolor="#lightblue"];')
        lines.append('  edge [color="#2c3e50"];')

        func = graph.functions.get(func_addr)
        if not func:
            return ""

        # Get all paths
        paths = graph.find_paths(0x0, func_addr, max_depth)
        if not paths:
            return ""

        added_edges = set()

        for path in paths[:10]:  # Limit paths
            prev_name = "entry"
            for i, addr in enumerate(path):
                f = graph.functions.get(addr)
                if f:
                    node_name = f"_{addr:x}"
                    if i == len(path) - 1:
                        lines.append(f'  {node_name} [fillcolor="#ff9999"];')  # Target in red
                    else:
                        lines.append(f'  {node_name} [label="{f.name}"];')

                    if i > 0:
                        edge = f"{prev_name}->{node_name}"
                        if edge not in added_edges:
                            lines.append(f"  {edge};")
                            added_edges.add(edge)

                    prev_name = node_name

        lines.append("}")
        return "\n".join(lines)

    def _generate_graphviz_dot(self, graph: XRefGraph) -> str:
        """Generate GraphViz DOT format for entire graph."""
        lines = []
        lines.append("digraph xref_graph {")
        lines.append("  rankdir=LR;")
        lines.append('  node [shape=box, style="rounded,filled", fillcolor="#lightblue"];')
        lines.append('  edge [color="#2c3e50"];')

        added_edges = set()

        for xref in graph.xrefs[:100]:  # Limit for performance
            source_name = f"_{xref.source_addr:x}"
            target_name = f"_{xref.target_addr:x}"

            if source_name not in added_edges:
                src_func = graph.functions.get(xref.source_addr)
                if src_func:
                    lines.append(f'  {source_name} [label="{src_func.name}"];')
                else:
                    lines.append(f'  {source_name} [label="0x{xref.source_addr:x}"];')
                added_edges.add(source_name)

            if target_name not in added_edges:
                tgt_func = graph.functions.get(xref.target_addr)
                if tgt_func:
                    lines.append(f'  {target_name} [label="{tgt_func.name}"];')
                else:
                    lines.append(f'  {target_name} [label="0x{xref.target_addr:x}"];')
                added_edges.add(target_name)

            edge = f"{source_name}->{target_name}"
            if edge not in added_edges:
                lines.append(f'  {edge} [label="{xref.xref_type.value}"];')
                added_edges.add(edge)

        lines.append("}")
        return "\n".join(lines)

    def _to_json(
        self, graph: XRefGraph, func_addr: int, callers: list[int], callees: list[int], similar: list[Tuple[int, float]]
    ) -> str:
        """Convert analysis results to JSON format."""
        data = {
            "function": {
                "address": f"0x{func_addr:x}",
                "name": graph.functions[func_addr].name,
                "size": graph.functions[func_addr].size,
                "complexity": graph.functions[func_addr].complexity_score,
            },
            "callers": [
                {"address": f"0x{caller:x}", "name": graph.functions[caller].name}
                for caller in callers
                if caller in graph.functions
            ],
            "callees": [
                {"address": f"0x{callee:x}", "name": graph.functions[callee].name}
                for callee in callees
                if callee in graph.functions
            ],
            "similar_functions": [
                {
                    "address": f"0x{similar_addr:x}",
                    "name": graph.functions[similar_addr].name,
                    "similarity": round(similarity, 3),
                }
                for similar_addr, similarity in similar
            ],
            "metrics": graph.calculate_complexity_metrics(),
        }
        return json.dumps(data, indent=2)

    def _overview_to_json(self, graph: XRefGraph, metrics: dict[str, Any]) -> str:
        """Convert overview to JSON format."""
        data = {
            "overview": {
                "total_functions": metrics["total_functions"],
                "entry_points": metrics["entry_points"],
                "leaf_functions": metrics["leaf_functions"],
                "avg_complexity": round(metrics["avg_complexity"], 2),
                "complexity_distribution": metrics["complexity_distribution"],
            },
            "most_complex": {
                "address": f"0x{metrics['most_complex'].address:x}",
                "name": metrics["most_complex"].name,
                "complexity": metrics["most_complex"].complexity_score,
            }
            if metrics["most_complex"]
            else None,
        }
        return json.dumps(data, indent=2)

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
        name=XRefVisualizerTool.name,
        description=XRefVisualizerTool.description,
        parameters=XRefVisualizerTool.parameters,
        function=XRefVisualizerTool.execute,
    )
