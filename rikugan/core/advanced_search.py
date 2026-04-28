"""Advanced search with function similarity detection.

Provides sophisticated search capabilities including:
- Function similarity search based on structure and calling patterns
- Code pattern matching
- String reference search
- Import/usage search
- Combined criteria search
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SearchCriteria(str, Enum):
    """Types of search criteria."""

    SIMILARITY = "similarity"  # Find functions similar to a target
    PATTERN = "pattern"  # Search by code pattern
    STRINGS = "strings"  # Search by string references
    IMPORTS = "imports"  # Search by import usage
    CALLEES = "callees"  # Search by called functions
    CALLERS = "callers"  # Search by caller functions
    SIZE = "size"  # Search by function size
    COMPLEXITY = "complexity"  # Search by complexity
    NAME = "name"  # Search by name pattern
    COMBINED = "combined"  # Combine multiple criteria


@dataclass
class SearchResult:
    """A search result."""

    address: int
    name: str
    score: float  # Relevance score 0.0 to 1.0
    reason: str  # Why this result matched
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FunctionSearchData:
    """Search-indexed function data."""

    address: int
    name: str
    size: int
    complexity: int
    strings: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    callees: list[int] = field(default_factory=list)
    callers: list[int] = field(default_factory=list)
    instructions: list[str] = field(default_factory=list)  # Normalized instructions
    bytes_hash: str = ""  # Hash of function bytes


class AdvancedSearchEngine:
    """Advanced search engine for binary code."""

    def __init__(self):
        self._functions: dict[int, FunctionSearchData] = {}
        self._name_index: dict[str, int] = {}
        self._string_index: dict[str, set[int]] = {}  # string -> function addresses
        self._import_index: dict[str, set[int]] = {}  # import -> function addresses
        self._size_index: dict[int, set[int]] = {}  # size -> function addresses

    def index_function(self, func_data: dict[str, Any]) -> None:
        """Index a function for searching.

        Args:
            func_data: Function data with address, name, size, etc.
        """
        address = func_data.get("address", func_data.get("start", 0))
        name = func_data.get("name", f"sub_{address:x}")

        search_data = FunctionSearchData(
            address=address,
            name=name,
            size=func_data.get("size", 0),
            complexity=func_data.get("complexity", 0),
            strings=func_data.get("strings", []),
            imports=func_data.get("imports", []),
            callees=func_data.get("callees", []),
            callers=func_data.get("callers", []),
            instructions=func_data.get("instructions", []),
            bytes_hash=func_data.get("bytes_hash", ""),
        )

        self._functions[address] = search_data
        self._name_index[name.lower()] = address

        # Index strings
        for string_ref in search_data.strings:
            if string_ref not in self._string_index:
                self._string_index[string_ref] = set()
            self._string_index[string_ref].add(address)

        # Index imports
        for imp in search_data.imports:
            if imp not in self._import_index:
                self._import_index[imp] = set()
            self._import_index[imp].add(address)

        # Index size
        size = search_data.size
        if size not in self._size_index:
            self._size_index[size] = set()
        self._size_index[size].add(address)

    def search(
        self, criteria: SearchCriteria, query: str = "", min_score: float = 0.0, max_results: int = 50, **kwargs
    ) -> list[SearchResult]:
        """Execute a search query.

        Args:
            criteria: Type of search
            query: Search query string
            min_score: Minimum relevance score
            max_results: Maximum results to return
            **kwargs: Additional criteria-specific parameters

        Returns:
            List of search results sorted by score
        """
        if criteria == SearchCriteria.SIMILARITY:
            return self._search_similarity(query, min_score, max_results, **kwargs)
        elif criteria == SearchCriteria.PATTERN:
            return self._search_pattern(query, min_score, max_results, **kwargs)
        elif criteria == SearchCriteria.STRINGS:
            return self._search_strings(query, min_score, max_results)
        elif criteria == SearchCriteria.IMPORTS:
            return self._search_imports(query, min_score, max_results)
        elif criteria == SearchCriteria.CALLEES:
            return self._search_callees(query, min_score, max_results)
        elif criteria == SearchCriteria.CALLERS:
            return self._search_callers(query, min_score, max_results)
        elif criteria == SearchCriteria.SIZE:
            return self._search_size(**kwargs, min_score=min_score, max_results=max_results)
        elif criteria == SearchCriteria.COMPLEXITY:
            return self._search_complexity(**kwargs, min_score=min_score, max_results=max_results)
        elif criteria == SearchCriteria.NAME:
            return self._search_name(query, min_score, max_results)
        elif criteria == SearchCriteria.COMBINED:
            return self._search_combined(query, min_score, max_results, **kwargs)
        else:
            return []

    def _search_similarity(self, target_func: str, min_score: float, max_results: int, **kwargs) -> list[SearchResult]:
        """Find functions similar to a target function.

        Uses Jaccard similarity on callees, strings, and imports.
        """
        # Resolve target function
        target_addr = self._resolve_function(target_func)
        if target_addr is None:
            return []

        target_data = self._functions.get(target_addr)
        if not target_data:
            return []

        results = []
        threshold = kwargs.get("threshold", 0.3)

        for addr, func_data in self._functions.items():
            if addr == target_addr:
                continue

            # Calculate Jaccard similarity
            similarity = self._calculate_similarity(target_data, func_data)

            if similarity >= threshold:
                results.append(
                    SearchResult(
                        address=addr,
                        name=func_data.name,
                        score=similarity,
                        reason=f"Similar to {target_data.name} (Jaccard: {similarity:.2f})",
                        metadata={
                            "shared_callees": len(set(target_data.callees) & set(func_data.callees)),
                            "shared_strings": len(set(target_data.strings) & set(func_data.strings)),
                            "shared_imports": len(set(target_data.imports) & set(func_data.imports)),
                        },
                    )
                )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:max_results]

    def _search_pattern(self, pattern: str, min_score: float, max_results: int, **kwargs) -> list[SearchResult]:
        """Search by instruction pattern regex."""
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error:
            return []

        results = []

        for addr, func_data in self._functions.items():
            # Check if pattern matches any instruction
            matches = 0
            for instr in func_data.instructions:
                if regex.search(instr):
                    matches += 1

            if matches > 0:
                score = min(matches / 10.0, 1.0)  # Normalize to 0-1
                if score >= min_score:
                    results.append(
                        SearchResult(
                            address=addr,
                            name=func_data.name,
                            score=score,
                            reason=f"Pattern matched {matches} instruction(s)",
                            metadata={"matches": matches},
                        )
                    )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:max_results]

    def _search_strings(self, query: str, min_score: float, max_results: int) -> list[SearchResult]:
        """Search by string references."""
        query_lower = query.lower()
        results = []

        for string_ref, addrs in self._string_index.items():
            if query_lower in string_ref.lower():
                for addr in addrs:
                    func_data = self._functions[addr]
                    results.append(
                        SearchResult(
                            address=addr,
                            name=func_data.name,
                            score=1.0,
                            reason=f"References string: {string_ref[:50]}",
                            metadata={"string": string_ref},
                        )
                    )

        results.sort(key=lambda r: r.address)
        return results[:max_results]

    def _search_imports(self, query: str, min_score: float, max_results: int) -> list[SearchResult]:
        """Search by import usage."""
        query_lower = query.lower()
        results = []

        for imp, addrs in self._import_index.items():
            if query_lower in imp.lower():
                for addr in addrs:
                    func_data = self._functions[addr]
                    results.append(
                        SearchResult(
                            address=addr,
                            name=func_data.name,
                            score=1.0,
                            reason=f"Uses import: {imp}",
                            metadata={"import": imp},
                        )
                    )

        results.sort(key=lambda r: r.address)
        return results[:max_results]

    def _search_callees(self, query: str, min_score: float, max_results: int) -> list[SearchResult]:
        """Search by called functions."""
        target_addr = self._resolve_function(query)
        if target_addr is None:
            return []

        results = []

        for addr, func_data in self._functions.items():
            if target_addr in func_data.callees:
                results.append(
                    SearchResult(
                        address=addr,
                        name=func_data.name,
                        score=1.0,
                        reason=f"Calls {self._functions[target_addr].name}",
                        metadata={"callee": target_addr},
                    )
                )

        results.sort(key=lambda r: r.address)
        return results[:max_results]

    def _search_callers(self, query: str, min_score: float, max_results: int) -> list[SearchResult]:
        """Search by caller functions."""
        target_addr = self._resolve_function(query)
        if target_addr is None:
            return []

        results = []

        for addr, func_data in self._functions.items():
            if target_addr in func_data.callers:
                results.append(
                    SearchResult(
                        address=addr,
                        name=func_data.name,
                        score=1.0,
                        reason=f"Called by {self._functions[target_addr].name}",
                        metadata={"caller": target_addr},
                    )
                )

        results.sort(key=lambda r: r.address)
        return results[:max_results]

    def _search_size(
        self, min_size: int = 0, max_size: int = 0, min_score: float = 0.0, max_results: int = 50
    ) -> list[SearchResult]:
        """Search by function size range."""
        results = []

        for addr, func_data in self._functions.items():
            size = func_data.size
            if (min_size == 0 or size >= min_size) and (max_size == 0 or size <= max_size):
                results.append(
                    SearchResult(
                        address=addr,
                        name=func_data.name,
                        score=1.0,
                        reason=f"Size: {size} bytes",
                        metadata={"size": size},
                    )
                )

        results.sort(key=lambda r: r.metadata.get("size", 0))
        return results[:max_results]

    def _search_complexity(
        self, min_complexity: int = 0, max_complexity: int = 0, min_score: float = 0.0, max_results: int = 50
    ) -> list[SearchResult]:
        """Search by complexity range."""
        results = []

        for addr, func_data in self._functions.items():
            complexity = func_data.complexity
            if (min_complexity == 0 or complexity >= min_complexity) and (
                max_complexity == 0 or complexity <= max_complexity
            ):
                results.append(
                    SearchResult(
                        address=addr,
                        name=func_data.name,
                        score=1.0,
                        reason=f"Complexity: {complexity}",
                        metadata={"complexity": complexity},
                    )
                )

        results.sort(key=lambda r: r.metadata.get("complexity", 0), reverse=True)
        return results[:max_results]

    def _search_name(self, query: str, min_score: float, max_results: int) -> list[SearchResult]:
        """Search by function name pattern."""
        query_lower = query.lower()
        results = []

        for addr, func_data in self._functions.items():
            if query_lower in func_data.name.lower():
                results.append(
                    SearchResult(
                        address=addr,
                        name=func_data.name,
                        score=1.0,
                        reason=f"Name matches pattern: {query}",
                        metadata={},
                    )
                )

        results.sort(key=lambda r: r.address)
        return results[:max_results]

    def _search_combined(self, query: str, min_score: float, max_results: int, **kwargs) -> list[SearchResult]:
        """Combine multiple search criteria."""
        all_results: dict[int, SearchResult] = {}

        # Get criteria to combine
        criteria_list = kwargs.get("criteria", [])
        weights = kwargs.get("weights", {})

        if not criteria_list:
            return []

        # Execute each search and combine scores
        for i, criteria_item in enumerate(criteria_list):
            criteria_type = SearchCriteria(criteria_item.get("type", "name"))
            criteria_query = criteria_item.get("query", "")
            weight = weights.get(i, 1.0)

            results = self.search(criteria_type, criteria_query, min_score=0.0, max_results=max_results * 2)

            for result in results:
                if result.address not in all_results:
                    all_results[result.address] = SearchResult(
                        address=result.address, name=result.name, score=0.0, reason="Combined search", metadata={}
                    )

                all_results[result.address].score += result.score * weight

        # Normalize scores
        for result in all_results.values():
            result.score = min(result.score / len(criteria_list), 1.0)

        # Filter by min_score and sort
        filtered = [r for r in all_results.values() if r.score >= min_score]
        filtered.sort(key=lambda r: r.score, reverse=True)

        return filtered[:max_results]

    def _calculate_similarity(self, func1: FunctionSearchData, func2: FunctionSearchData) -> float:
        """Calculate Jaccard similarity between two functions."""
        # Callee similarity
        callee_union = len(set(func1.callees) | set(func2.callees))
        callee_intersect = len(set(func1.callees) & set(func2.callees))
        callee_sim = callee_intersect / callee_union if callee_union > 0 else 0.0

        # String similarity
        string_union = len(set(func1.strings) | set(func2.strings))
        string_intersect = len(set(func1.strings) & set(func2.strings))
        string_sim = string_intersect / string_union if string_union > 0 else 0.0

        # Import similarity
        import_union = len(set(func1.imports) | set(func2.imports))
        import_intersect = len(set(func1.imports) & set(func2.imports))
        import_sim = import_intersect / import_union if import_union > 0 else 0.0

        # Weighted average
        return callee_sim * 0.5 + string_sim * 0.3 + import_sim * 0.2

    def _resolve_function(self, identifier: str) -> int | None:
        """Resolve function identifier to address."""
        # Try as hex address
        try:
            addr = int(identifier, 16)
            if addr in self._functions:
                return addr
        except ValueError:
            pass

        # Try as name
        return self._name_index.get(identifier.lower())
