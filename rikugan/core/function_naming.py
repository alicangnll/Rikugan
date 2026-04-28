"""Smart function naming system with pattern recognition.

Analyzes function characteristics to suggest meaningful names for
automatically generated functions (e.g., sub_1234, loc_5678).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FunctionPattern(str, Enum):
    """Common function patterns in binary code."""

    INIT = "init"  # Initialization/constructor
    CLEANUP = "cleanup"  # Destructor/cleanup
    GETTER = "getter"  # Get property/value
    SETTER = "setter"  # Set property/value
    VALIDATOR = "validator"  # Validate input
    PARSER = "parser"  # Parse data
    SERIALIZER = "serializer"  # Serialize data
    COMPARATOR = "comparator"  # Compare two values
    CALLBACK = "callback"  # Callback/handler
    WRAPPER = "wrapper"  # Wrapper around another function
    FACTORY = "factory"  # Create new objects
    SINGLETON = "singleton"  # Get singleton instance
    ITERATOR = "iterator"  # Iterate over collection
    HASH = "hash"  # Calculate hash
    CRYPTO = "crypto"  # Cryptographic operation
    COMPRESS = "compress"  # Compression/decompression
    ENCODE = "encode"  # Encode/decode
    NETWORK = "network"  # Network operation
    FILE_IO = "file_io"  # File I/O
    STRING = "string"  # String manipulation
    MATH = "math"  # Mathematical operation
    MEMORY = "memory"  # Memory allocation/management
    THREAD = "thread"  # Threading/synchronization
    LOG = "log"  # Logging
    ERROR = "error"  # Error handling
    UNKNOWN = "unknown"


@dataclass
class NamingSuggestion:
    """A suggested name for a function."""

    name: str
    confidence: float  # 0.0 to 1.0
    pattern: FunctionPattern
    reason: str  # Why this name was suggested


@dataclass
class FunctionFeatures:
    """Extracted features from a function for naming."""

    address: int
    size: int
    num_args: int
    num_callees: int
    num_callers: int
    num_strings: int
    num_imports: int
    string_refs: list[str] = field(default_factory=list)
    import_names: list[str] = field(default_factory=list)
    callee_names: list[str] = field(default_factory=list)
    has_loops: bool = False
    has_switch: bool = False
    has_recursion: bool = False
    cyclomatic_complexity: int = 0


class FunctionNamer:
    """Analyzes functions and suggests meaningful names."""

    # Common API patterns
    API_PATTERNS = {
        # Windows API
        "create": FunctionPattern.FACTORY,
        "open": FunctionPattern.FACTORY,
        "close": FunctionPattern.CLEANUP,
        "read": FunctionPattern.GETTER,
        "write": FunctionPattern.SETTER,
        "get": FunctionPattern.GETTER,
        "set": FunctionPattern.SETTER,
        "init": FunctionPattern.INIT,
        "free": FunctionPattern.CLEANUP,
        "destroy": FunctionPattern.CLEANUP,
        "validate": FunctionPattern.VALIDATOR,
        "check": FunctionPattern.VALIDATOR,
        "parse": FunctionPattern.PARSER,
        "serialize": FunctionPattern.SERIALIZER,
        "compare": FunctionPattern.COMPARATOR,
        "encrypt": FunctionPattern.CRYPTO,
        "decrypt": FunctionPattern.CRYPTO,
        "hash": FunctionPattern.HASH,
        "compress": FunctionPattern.COMPRESS,
        "decompress": FunctionPattern.COMPRESS,
        "encode": FunctionPattern.ENCODE,
        "decode": FunctionPattern.ENCODE,
        "send": FunctionPattern.NETWORK,
        "recv": FunctionPattern.NETWORK,
        "connect": FunctionPattern.NETWORK,
        "accept": FunctionPattern.NETWORK,
        "bind": FunctionPattern.NETWORK,
        "listen": FunctionPattern.NETWORK,
        # libc
        "malloc": FunctionPattern.MEMORY,
        "calloc": FunctionPattern.MEMORY,
        "realloc": FunctionPattern.MEMORY,
        "memcpy": FunctionPattern.MEMORY,
        "memset": FunctionPattern.MEMORY,
        "strlen": FunctionPattern.STRING,
        "strcpy": FunctionPattern.STRING,
        "strcmp": FunctionPattern.COMPARATOR,
        "sprintf": FunctionPattern.STRING,
        "printf": FunctionPattern.LOG,
        "fprintf": FunctionPattern.LOG,
        "fopen": FunctionPattern.FILE_IO,
        "fclose": FunctionPattern.FILE_IO,
        "fread": FunctionPattern.FILE_IO,
        "fwrite": FunctionPattern.FILE_IO,
        "pthread": FunctionPattern.THREAD,
        "mutex": FunctionPattern.THREAD,
        "lock": FunctionPattern.THREAD,
        "unlock": FunctionPattern.THREAD,
    }

    # String patterns
    STRING_PATTERNS = {
        r"http[s]?://": "url",
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}": "ip",
        r"[a-f0-9]{32}": "md5",
        r"[a-f0-9]{40}": "sha1",
        r"[a-f0-9]{64}": "sha256",
        r"%[sdnx]": "format",
        r"error": "error",
        r"failed": "error",
        r"success": "success",
        r"config": "config",
        r"password": "password",
        r"username": "username",
        r"token": "token",
        r"key": "key",
    }

    def __init__(self):
        self._custom_patterns: dict[str, FunctionPattern] = {}

    def add_custom_pattern(self, pattern: str, func_type: FunctionPattern) -> None:
        """Add a custom naming pattern."""
        self._custom_patterns[pattern] = func_type

    def suggest_name(self, features: FunctionFeatures, context: dict[str, Any] | None = None) -> list[NamingSuggestion]:
        """Generate name suggestions for a function.

        Args:
            features: Extracted function features
            context: Additional context (e.g., surrounding function names)

        Returns:
            List of naming suggestions sorted by confidence
        """
        suggestions = []

        # Analyze imports
        if features.import_names:
            import_suggestions = self._analyze_imports(features)
            suggestions.extend(import_suggestions)

        # Analyze strings
        if features.string_refs:
            string_suggestions = self._analyze_strings(features)
            suggestions.extend(string_suggestions)

        # Analyze callees
        if features.callee_names:
            callee_suggestions = self._analyze_callees(features)
            suggestions.extend(callee_suggestions)

        # Analyze structure
        structure_suggestions = self._analyze_structure(features)
        suggestions.extend(structure_suggestions)

        # Analyze call graph position
        if context:
            graph_suggestions = self._analyze_graph_position(features, context)
            suggestions.extend(graph_suggestions)

        # Sort by confidence and deduplicate
        suggestions.sort(key=lambda s: s.confidence, reverse=True)
        seen = set()
        unique_suggestions = []
        for s in suggestions:
            if s.name not in seen:
                seen.add(s.name)
                unique_suggestions.append(s)

        return unique_suggestions[:5]  # Return top 5

    def _analyze_imports(self, features: FunctionFeatures) -> list[NamingSuggestion]:
        """Analyze imported functions to determine purpose."""
        suggestions = []

        for import_name in features.import_names:
            import_lower = import_name.lower()

            # Check against known API patterns
            for pattern, func_type in self.API_PATTERNS.items():
                if pattern in import_lower:
                    # Extract base name from import
                    base = self._extract_base_name(import_name)
                    suggestions.append(
                        NamingSuggestion(
                            name=f"{func_type.value}_{base}",
                            confidence=0.8,
                            pattern=func_type,
                            reason=f"Uses {import_name}",
                        )
                    )
                    break

        return suggestions

    def _analyze_strings(self, features: FunctionFeatures) -> list[NamingSuggestion]:
        """Analyze string references to determine purpose."""
        suggestions = []

        for string_ref in features.string_refs[:10]:  # Limit to 10 strings
            # Check against string patterns
            for pattern, name in self.STRING_PATTERNS.items():
                if re.search(pattern, string_ref, re.IGNORECASE):
                    suggestions.append(
                        NamingSuggestion(
                            name=f"handle_{name}",
                            confidence=0.7,
                            pattern=FunctionPattern.UNKNOWN,
                            reason=f"References string matching pattern: {pattern}",
                        )
                    )
                    break

            # Check for error messages
            if any(word in string_ref.lower() for word in ["error", "failed", "invalid"]):
                suggestions.append(
                    NamingSuggestion(
                        name="handle_error",
                        confidence=0.6,
                        pattern=FunctionPattern.ERROR,
                        reason=f"References error string: {string_ref[:30]}",
                    )
                )

            # Check for format strings
            if "%" in string_ref and any(c in string_ref for c in "sdnx"):
                suggestions.append(
                    NamingSuggestion(
                        name="format_string",
                        confidence=0.5,
                        pattern=FunctionPattern.STRING,
                        reason=f"Contains format string: {string_ref[:30]}",
                    )
                )

        return suggestions

    def _analyze_callees(self, features: FunctionFeatures) -> list[NamingSuggestion]:
        """Analyze called functions to determine purpose."""
        suggestions = []

        # Wrapper detection: single callee with similar signature
        if len(features.callee_names) == 1:
            callee_name = features.callee_names[0]
            if not callee_name.startswith("sub_"):
                suggestions.append(
                    NamingSuggestion(
                        name=f"wrapper_{callee_name}",
                        confidence=0.6,
                        pattern=FunctionPattern.WRAPPER,
                        reason=f"Only calls {callee_name}",
                    )
                )

        # Getter pattern: calls get/read + returns
        if features.num_callees <= 3:
            for callee in features.callee_names:
                if any(pattern in callee.lower() for pattern in ["get", "read", "fetch"]):
                    suggestions.append(
                        NamingSuggestion(
                            name=f"get_{self._infer_target(features)}",
                            confidence=0.5,
                            pattern=FunctionPattern.GETTER,
                            reason=f"Calls getter function {callee}",
                        )
                    )
                    break

        # Setter pattern: calls set/write + no return
        if features.num_callees <= 3:
            for callee in features.callee_names:
                if any(pattern in callee.lower() for pattern in ["set", "write", "store"]):
                    suggestions.append(
                        NamingSuggestion(
                            name=f"set_{self._infer_target(features)}",
                            confidence=0.5,
                            pattern=FunctionPattern.SETTER,
                            reason=f"Calls setter function {callee}",
                        )
                    )
                    break

        return suggestions

    def _analyze_structure(self, features: FunctionFeatures) -> list[NamingSuggestion]:
        """Analyze function structure to determine purpose."""
        suggestions = []

        # Validation pattern: lots of comparisons + error checking
        if features.cyclomatic_complexity > 10 and features.has_switch:
            suggestions.append(
                NamingSuggestion(
                    name="validate_input",
                    confidence=0.4,
                    pattern=FunctionPattern.VALIDATOR,
                    reason=f"High complexity ({features.cyclomatic_complexity}) with switch statement",
                )
            )

        # Iterator pattern: loop + calls next/advance
        if features.has_loops and features.num_callees > 0:
            if any("next" in c.lower() or "advance" in c.lower() for c in features.callee_names):
                suggestions.append(
                    NamingSuggestion(
                        name="iterate_collection",
                        confidence=0.5,
                        pattern=FunctionPattern.ITERATOR,
                        reason="Contains loop and calls next/advance functions",
                    )
                )

        # Initialization pattern: calls many constructors/setters
        init_keywords = ["init", "create", "setup", "start", "begin"]
        if features.num_callees > 5:
            if any(keyword in c.lower() for c in features.callee_names for keyword in init_keywords):
                suggestions.append(
                    NamingSuggestion(
                        name="initialize",
                        confidence=0.5,
                        pattern=FunctionPattern.INIT,
                        reason=f"Calls {features.num_callees} functions with init-like names",
                    )
                )

        return suggestions

    def _analyze_graph_position(self, features: FunctionFeatures, context: dict[str, Any]) -> list[NamingSuggestion]:
        """Analyze function's position in call graph."""
        suggestions = []

        # Entry point: no callers, has callees
        if features.num_callers == 0 and features.num_callees > 0:
            suggestions.append(
                NamingSuggestion(
                    name="entry_point",
                    confidence=0.7,
                    pattern=FunctionPattern.INIT,
                    reason=f"No callers, calls {features.num_callees} functions",
                )
            )

        # Leaf function: has callers, no callees
        if features.num_callers > 0 and features.num_callees == 0:
            suggestions.append(
                NamingSuggestion(
                    name="leaf_function",
                    confidence=0.4,
                    pattern=FunctionPattern.UNKNOWN,
                    reason=f"Called by {features.num_callers} functions but calls nothing",
                )
            )

        return suggestions

    def _extract_base_name(self, import_name: str) -> str:
        """Extract meaningful base name from import."""
        # Remove common prefixes
        for prefix in ["_", "dll_", "api_", "sys_"]:
            if import_name.lower().startswith(prefix):
                import_name = import_name[len(prefix) :]

        # Remove common suffixes
        for suffix in ["a", "w", "ex", "internal"]:
            if import_name.lower().endswith(suffix):
                import_name = import_name[: -len(suffix)]

        return import_name

    def _infer_target(self, features: FunctionFeatures) -> str:
        """Infer target object/property from context."""
        if features.string_refs:
            # Use first string as hint
            return "data"

        if features.callee_names:
            # Use first callee name as hint
            return self._extract_base_name(features.callee_names[0])

        return "value"


def extract_function_features(func_data: dict[str, Any], xref_data: dict[str, Any] | None = None) -> FunctionFeatures:
    """Extract features from function data for naming analysis.

    Args:
        func_data: Function data from host (IDA/Binary Ninja)
        xref_data: Optional cross-reference data

    Returns:
        Extracted function features
    """
    # Basic info
    address = func_data.get("address", func_data.get("start", 0))
    size = func_data.get("size", 0)
    num_args = func_data.get("arg_count", 0)

    # Cross-reference info
    num_callees = 0
    num_callers = 0
    callee_names = []
    string_refs = []
    import_names = []

    if xref_data:
        num_callees = len(xref_data.get("callees", []))
        num_callers = len(xref_data.get("callers", []))
        callee_names = [c.get("name", "") for c in xref_data.get("callees", []) if c.get("name")]
        string_refs = xref_data.get("strings", [])
        import_names = [i.get("name", "") for i in xref_data.get("imports", []) if i.get("name")]

    # Structural analysis
    has_loops = func_data.get("has_loops", False)
    has_switch = func_data.get("has_switch", False)
    has_recursion = func_data.get("has_recursion", False)
    cyclomatic_complexity = func_data.get("cyclomatic_complexity", 0)

    return FunctionFeatures(
        address=address,
        size=size,
        num_args=num_args,
        num_callees=num_callees,
        num_callers=num_callers,
        num_strings=len(string_refs),
        num_imports=len(import_names),
        string_refs=string_refs,
        import_names=import_names,
        callee_names=callee_names,
        has_loops=has_loops,
        has_switch=has_switch,
        has_recursion=has_recursion,
        cyclomatic_complexity=cyclomatic_complexity,
    )
