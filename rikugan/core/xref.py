"""Cross-reference analysis and visualization for reverse engineering.

Provides comprehensive call graph analysis, data flow tracking, and
relationship mapping between functions, variables, and data structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class XRefType(str, Enum):
    """Types of cross-references."""

    CALL = "call"
    DATA = "data"
    READ = "read"
    WRITE = "write"
    REF = "ref"
    IMPORT = "import"
    EXPORT = "export"
    STRING = "string"


@dataclass
class XRef:
    """A single cross-reference entry."""

    source_addr: int
    target_addr: int
    xref_type: XRefType
    function_name: str = ""
    context: str = ""  # Additional context about the reference


@dataclass
class FunctionInfo:
    """Information about a function for xref analysis."""

    address: int
    name: str
    size: int
    callers: set[int] = field(default_factory=set)
    callees: set[int] = field(default_factory=set)
    data_refs: set[int] = field(default_factory=set)
    string_refs: set[int] = field(default_factory=set)
    imported_funcs: set[int] = field(default_factory=set)
    exported_funcs: set[int] = field(default_factory=set)

    @property
    def complexity_score(self) -> int:
        """Calculate cyclomatic complexity based on xrefs."""
        return len(self.callers) * 1 + len(self.callees) * 2 + len(self.data_refs) * 1 + len(self.string_refs) * 1


@dataclass
class XRefGraph:
    """Cross-reference graph for call analysis and visualization."""

    functions: dict[int, FunctionInfo] = field(default_factory=dict)
    xrefs: list[XRef] = field(default_factory=list)
    address_to_name: dict[int, str] = field(default_factory=dict)
    name_to_address: dict[str, int] = field(default_factory=dict)

    def add_function(self, address: int, name: str, size: int = 0) -> None:
        """Add a function to the graph."""
        if address not in self.functions:
            self.functions[address] = FunctionInfo(address=address, name=name, size=size)
        self.address_to_name[address] = name
        self.name_to_address[name] = address

    def add_xref(self, source: int, target: int, xref_type: XRefType, context: str = "") -> None:
        """Add a cross-reference entry."""
        xref = XRef(source_addr=source, target_addr=target, xref_type=xref_type, context=context)
        self.xrefs.append(xref)

        # Update function relationships
        if source in self.functions and target in self.functions:
            if xref_type == XRefType.CALL:
                self.functions[source].callees.add(target)
                self.functions[target].callers.add(source)
            elif xref_type in (XRefType.DATA, XRefType.READ, XRefType.WRITE):
                self.functions[source].data_refs.add(target)
            elif xref_type == XRefType.STRING:
                self.functions[source].string_refs.add(target)

    def get_callers(self, func_addr: int) -> list[int]:
        """Get all functions that call the given function."""
        if func_addr in self.functions:
            return list(self.functions[func_addr].callers)
        return []

    def get_callees(self, func_addr: int) -> list[int]:
        """Get all functions called by the given function."""
        if func_addr in self.functions:
            return list(self.functions[func_addr].callees)
        return []

    def get_entry_points(self) -> list[int]:
        """Get functions that are never called (potential entry points)."""
        entry_points = []
        for addr, func in self.functions.items():
            if not func.callers and func.imported_funcs:
                # Function is imported but never called internally
                entry_points.append(addr)
            elif not func.callers and not func.callees:
                # Standalone function with no xrefs
                entry_points.append(addr)
        return entry_points

    def get_leaf_functions(self) -> list[int]:
        """Get functions that call other functions but are never called."""
        leaves = []
        for addr, func in self.functions.items():
            if func.callees and not func.callers:
                leaves.append(addr)
        return leaves

    def find_paths(self, source: int, target: int, max_depth: int = 10) -> list[list[int]]:
        """Find all call paths from source to target using BFS."""
        if source not in self.functions or target not in self.functions:
            return []

        paths: list[list[int]] = []
        queue = [(source, [source])]  # (current, path_so_far)
        visited = set()

        while queue and len(paths) < 100:  # Limit paths
            current, path = queue.pop(0)

            if current == target:
                paths.append(path)
                continue

            if len(path) >= max_depth:
                continue

            if current in visited:
                continue
            visited.add(current)

            # Explore callees
            for callee in self.get_callees(current):
                if callee not in path:  # Avoid cycles
                    queue.append((callee, path + [callee]))

        return paths

    def calculate_complexity_metrics(self) -> dict[str, Any]:
        """Calculate complexity metrics for all functions."""
        complexity_distribution: dict[str, int] = {
            "low": 0,  # 0-10 xrefs
            "medium": 0,  # 11-50 xrefs
            "high": 0,  # 51-100 xrefs
            "very_high": 0,  # 100+ xrefs
        }

        metrics: dict[str, Any] = {
            "total_functions": len(self.functions),
            "entry_points": len(self.get_entry_points()),
            "leaf_functions": len(self.get_leaf_functions()),
            "avg_complexity": 0,
            "most_complex": None,
            "complexity_distribution": complexity_distribution,
        }

        if not self.functions:
            return metrics

        complexities = []
        for func in self.functions.values():
            comp = func.complexity_score
            complexities.append(comp)

            if comp <= 10:
                complexity_distribution["low"] += 1
            elif comp <= 50:
                complexity_distribution["medium"] += 1
            elif comp <= 100:
                complexity_distribution["high"] += 1
            else:
                complexity_distribution["very_high"] += 1

        metrics["avg_complexity"] = sum(complexities) / len(complexities) if complexities else 0
        metrics["most_complex"] = max(self.functions.values(), key=lambda f: f.complexity_score)

        return metrics

    def find_similar_functions(self, func_addr: int, threshold: float = 0.7) -> list[tuple[int, float]]:
        """Find functions with similar calling patterns (Jaccard similarity)."""
        if func_addr not in self.functions:
            return []

        target_func = self.functions[func_addr]
        target_callees = target_func.callees

        similarities = []

        for addr, func in self.functions.items():
            if addr == func_addr:
                continue

            # Calculate Jaccard similarity
            union = len(target_callees.union(func.callees))
            intersection = len(target_callees.intersection(func.callees))

            if union > 0:
                similarity = intersection / union
                if similarity >= threshold:
                    similarities.append((addr, similarity))

        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities


def build_xref_graph(host_functions: list[dict[str, Any]], host_xrefs: list[dict[str, Any]]) -> XRefGraph:
    """Build a cross-reference graph from host-provided data.

    Args:
        host_functions: List of function info dicts from host (IDA/Binary Ninja)
        host_xrefs: List of xref info dicts from host

    Returns:
        Populated XRefGraph
    """
    graph = XRefGraph()

    # Add all functions
    for func_info in host_functions:
        addr = func_info.get("address", func_info.get("start", 0))
        name = func_info.get("name", f"sub_{addr:x}")
        size = func_info.get("size", 0)
        graph.add_function(addr, name, size)

    # Add all xrefs
    for xref_info in host_xrefs:
        source = xref_info.get("source", 0)
        target = xref_info.get("target", 0)
        xref_type = XRefType.CALL  # Default

        # Try to determine type from context
        if "type" in xref_info:
            try:
                xref_type = XRefType(xref_info["type"])
            except ValueError:
                pass

        graph.add_xref(source, target, xref_type)

    return graph
