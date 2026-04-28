"""Type library auto-detection tool for Rikugan.

Automatically detects and applies standard type libraries (Windows, Linux, etc.)
to recover structure definitions and function signatures.
"""

from __future__ import annotations

from ..core.logging import log_info
from ..core.type_recovery import PlatformType, TypeRecoveryEngine
from ..tools.base import Tool, ToolDefinition


class TypeRecoveryTool(Tool):
    """Automatic type detection and structure recovery tool."""

    name = "type_recovery"
    description = "Auto-detect types and recover structure definitions"
    parameters = {
        "platform": {
            "description": "Target platform (auto, windows_x86, windows_x64, linux_x86, linux_x64)",
            "type": "string",
            "default": "auto",
            "enum": ["auto", "windows_x86", "windows_x64", "linux_x86", "linux_x64", "macos", "android", "ios"],
        },
        "detect_platform": {
            "description": "Automatically detect platform from imports",
            "type": "boolean",
            "default": True,
        },
        "match_structures": {
            "description": "Match data references to known structures",
            "type": "boolean",
            "default": True,
        },
        "match_signatures": {
            "description": "Match functions to known signatures",
            "type": "boolean",
            "default": True,
        },
        "apply_types": {
            "description": "Auto-apply detected types (experimental)",
            "type": "boolean",
            "default": False,
        },
        "min_confidence": {
            "description": "Minimum confidence for auto-apply (0.0-1.0, default: 0.7)",
            "type": "float",
            "default": 0.7,
            "min": 0.0,
            "max": 1.0,
        },
    }

    def execute(
        self,
        platform: str = "auto",
        detect_platform: bool = True,
        match_structures: bool = True,
        match_signatures: bool = True,
        apply_types: bool = False,
        min_confidence: float = 0.7,
    ) -> str:
        """Execute type recovery analysis.

        Args:
            platform: Target platform
            detect_platform: Auto-detect platform from imports
            match_structures: Match structures
            match_signatures: Match function signatures
            apply_types: Auto-apply detected types
            min_confidence: Min confidence for auto-apply

        Returns:
            Type recovery report
        """
        # Import host-specific functions
        try:
            if self._is_ida():
                from ..ida.tools.ida_types import IDATypeCollector

                host_collector = IDATypeCollector()
            else:
                from ..binja.tools.binja_types import BinaryNinjaTypeCollector

                host_collector = BinaryNinjaTypeCollector()
        except ImportError:
            return "Error: Host-specific type collector not available"

        # Detect or set platform
        detected_platform = PlatformType.CUSTOM
        if detect_platform:
            imports = host_collector.get_imports()
            engine = TypeRecoveryEngine()
            detected_platform = engine.detect_platform(imports)
            log_info(f"Detected platform: {detected_platform}")
        elif platform != "auto":
            detected_platform = PlatformType(platform)

        engine = TypeRecoveryEngine(detected_platform)

        lines = []
        lines.append("=== Type Library Auto-Detection ===")
        lines.append(f"Platform: {detected_platform}")
        lines.append("")

        # Match structures
        if match_structures:
            log_info("Matching structures...")
            data_refs = host_collector.get_data_references()
            struct_matches = engine.match_structures(data_refs)

            lines.append(f"Structure Matches: {len(struct_matches)}")
            for addr, type_info in struct_matches[:20]:  # Limit output
                lines.append(f"  0x{addr:x}: {type_info.name} ({type_info.size} bytes)")
                if type_info.members:
                    lines.append(f"    Members: {', '.join(type_info.members.keys())}")

                if apply_types and type_info.confidence >= min_confidence:
                    if engine.apply_type_to_address(addr, type_info.name):
                        lines.append("    ✓ Applied")

            lines.append("")

        # Match signatures
        if match_signatures:
            log_info("Matching function signatures...")
            functions = host_collector.get_functions()
            imports = host_collector.get_imports()

            signature_matches = []
            for func in functions:
                match = engine.match_function_signature(func, imports)
                if match:
                    signature_matches.append(match)

            lines.append(f"Signature Matches: {len(signature_matches)}")
            for match in signature_matches[:20]:  # Limit output
                lines.append(f"  {match.function_name} (0x{match.address:x})")
                lines.append(f"    Confidence: {match.confidence:.2f}")
                lines.append(f"    Library: {match.library_name}")
                lines.append(f"    Reason: {match.reason}")
                lines.append(f"    Signature: {match.signature}")

                if apply_types and match.confidence >= min_confidence:
                    if engine.apply_signature_to_function(match.address, match.signature):
                        lines.append("    ✓ Applied")

            lines.append("")

        # Summary
        lines.append("=== Summary ===")
        lines.append(f"Platform detected: {detected_platform}")
        if match_structures:
            lines.append(f"Structures matched: {len(engine.match_structures(host_collector.get_data_references()))}")
        if match_signatures:
            lines.append(
                f"Signatures matched: {len([m for m in [engine.match_function_signature(f, host_collector.get_imports()) for f in host_collector.get_functions()] if m])}"
            )

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
        name=TypeRecoveryTool.name,
        description=TypeRecoveryTool.description,
        parameters=TypeRecoveryTool.parameters,
        function=TypeRecoveryTool.execute,
    )
