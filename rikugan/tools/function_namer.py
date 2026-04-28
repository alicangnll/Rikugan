"""Smart function naming tool for Rikugan.

Provides AI-powered function name suggestions based on pattern recognition,
import analysis, string reference analysis, and call graph position.
"""

from __future__ import annotations

from ..core.function_naming import FunctionNamer, extract_function_features
from ..core.logging import log_info
from ..tools.base import Tool, ToolDefinition


class FunctionNamerTool(Tool):
    """Smart function naming suggestion tool."""

    name = "function_namer"
    description = "Suggest meaningful names for anonymous functions (sub_XXX, loc_XXX)"
    parameters = {
        "target_function": {
            "description": "Function address or name to analyze (empty for all unnamed functions)",
            "type": "string",
            "required": False,
        },
        "max_suggestions": {
            "description": "Maximum number of suggestions per function (default: 5)",
            "type": "integer",
            "default": 5,
            "min": 1,
            "max": 10,
        },
        "min_confidence": {
            "description": "Minimum confidence threshold (0.0-1.0, default: 0.4)",
            "type": "float",
            "default": 0.4,
            "min": 0.0,
            "max": 1.0,
        },
        "apply_threshold": {
            "description": "Auto-apply names with confidence >= this value (0.0-1.0, 0 to disable)",
            "type": "float",
            "default": 0.0,
            "min": 0.0,
            "max": 1.0,
        },
    }

    def execute(
        self,
        target_function: str = "",
        max_suggestions: int = 5,
        min_confidence: float = 0.4,
        apply_threshold: float = 0.0,
    ) -> str:
        """Execute function naming analysis.

        Args:
            target_function: Specific function to analyze (empty for all)
            max_suggestions: Max suggestions per function
            min_confidence: Minimum confidence for suggestions
            apply_threshold: Auto-apply names above this confidence

        Returns:
            Naming suggestions report
        """
        # Import host-specific functions
        try:
            if self._is_ida():
                from ..ida.tools.ida_namer import IDAFunctionNamer

                host_namer = IDAFunctionNamer()
            else:
                from ..binja.tools.binja_namer import BinaryNinjaFunctionNamer

                host_namer = BinaryNinjaFunctionNamer()
        except ImportError:
            return "Error: Host-specific function namer not available"

        namer = FunctionNamer()

        # Get functions to analyze
        log_info("Collecting function data...")
        if target_function:
            func_data = host_namer.get_function_data(target_function)
            if not func_data:
                return f"Error: Function '{target_function}' not found"
            functions_to_analyze = [func_data]
        else:
            functions_to_analyze = host_namer.get_unnamed_functions()
            log_info(f"Found {len(functions_to_analyze)} unnamed functions")

        if not functions_to_analyze:
            return "No functions to analyze"

        # Generate suggestions
        lines = []
        lines.append("=== Smart Function Naming Suggestions ===")
        lines.append(f"Analyzing {len(functions_to_analyze)} function(s)...")
        lines.append(f"Min confidence: {min_confidence:.2f}")
        lines.append("")

        applied_count = 0
        for func_data in functions_to_analyze:
            func_addr = func_data.get("address", func_data.get("start", 0))
            current_name = func_data.get("name", f"sub_{func_addr:x}")

            # Extract features
            xref_data = host_namer.get_xref_data(func_addr)
            features = extract_function_features(func_data, xref_data)

            # Get suggestions
            context = {"similar_functions": host_namer.get_similar_function_names(func_addr)}
            suggestions = namer.suggest_name(features, context)

            # Filter by confidence
            filtered = [s for s in suggestions if s.confidence >= min_confidence]

            if not filtered:
                continue

            # Display suggestions
            lines.append(f"Function: {current_name} (0x{func_addr:x})")
            lines.append(f"  Size: {features.size} bytes, Args: {features.num_args}")
            lines.append(f"  Callees: {features.num_callees}, Callers: {features.num_callers}")

            if features.string_refs:
                lines.append(f"  String refs: {features.string_refs[:3]}")

            lines.append("  Suggestions:")
            for i, suggestion in enumerate(filtered[:max_suggestions], 1):
                lines.append(f"    {i}. {suggestion.name} (confidence: {suggestion.confidence:.2f})")
                lines.append(f"       Pattern: {suggestion.pattern.value}")
                lines.append(f"       Reason: {suggestion.reason}")

                # Auto-apply if above threshold
                if apply_threshold > 0 and suggestion.confidence >= apply_threshold:
                    if host_namer.apply_name(func_addr, suggestion.name):
                        lines.append("       ✓ Auto-applied!")
                        applied_count += 1
                    else:
                        lines.append("       ✗ Failed to apply")

            lines.append("")

        # Summary
        lines.append("=== Summary ===")
        lines.append(f"Functions analyzed: {len(functions_to_analyze)}")
        if apply_threshold > 0:
            lines.append(f"Names applied: {applied_count}")

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
        name=FunctionNamerTool.name,
        description=FunctionNamerTool.description,
        parameters=FunctionNamerTool.parameters,
        function=FunctionNamerTool.execute,
    )
