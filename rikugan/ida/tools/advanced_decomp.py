"""Advanced decompilation integration tools for IDA Pro.

Provides IDA-specific implementations for:
- Cross-reference visualization
- Smart function naming
- Type recovery
- Code bookmarking
- Advanced search
"""

from __future__ import annotations

import importlib
from typing import Annotated

from ...tools.base import parse_addr, tool

# Import IDA APIs
ida_funcs = ida_name = ida_xref = idautils = ida_struct = ida_bytes = idaapi = None
try:
    ida_funcs = importlib.import_module("ida_funcs")
    ida_name = importlib.import_module("ida_name")
    ida_xref = importlib.import_module("ida_xref")
    idautils = importlib.import_module("idautils")
    ida_struct = importlib.import_module("ida_struct")
    ida_bytes = importlib.import_module("ida_bytes")
    idaapi = importlib.import_module("idaapi")
except ImportError:
    pass  # IDA not available


@tool(category="decompilation")
def analyze_function_xrefs(
    address: Annotated[str, "Function address (hex string)"],
    max_depth: Annotated[int, "Maximum depth for analysis"] = 10,
    format: Annotated[str, "Output format"] = "text",
) -> str:
    """Analyze cross-references for a function with call paths and complexity metrics."""

    from ...core.xref import build_xref_graph

    ea = parse_addr(address)
    func = ida_funcs.get_func(ea)
    if not func:
        return f"No function at 0x{ea:x}"

    # Collect function data
    functions = []
    for func_ea in idautils.Functions():
        curr_func = ida_funcs.get_func(func_ea)
        if curr_func:
            functions.append(
                {
                    "address": func_ea,
                    "name": ida_name.get_name(func_ea) or f"sub_{func_ea:x}",
                    "size": curr_func.end_ea - curr_func.start_ea,
                }
            )

    # Collect xref data
    xrefs = []
    for func_ea in idautils.Functions():
        curr_func = ida_funcs.get_func(func_ea)
        if curr_func:
            # Get callees
            for item in idautils.FuncItems(func_ea):
                for xref in idautils.CodeRefsFrom(item, 0):
                    target_func = ida_funcs.get_func(xref.to)
                    if target_func and target_func.start_ea != func_ea:
                        xrefs.append({"source": func_ea, "target": target_func.start_ea, "type": "call"})

    # Build graph
    graph = build_xref_graph(functions, xrefs)

    # Get function info
    func_addr = func.start_ea
    func_info = graph.functions.get(func_addr)
    if not func_info:
        return f"Function not in graph: 0x{func_addr:x}"

    lines = []
    lines.append(f"=== XRef Analysis: {func_info.name} (0x{func_addr:x}) ===")
    lines.append(f"Size: {func_info.size} bytes")
    lines.append(f"Complexity: {func_info.complexity_score}")
    lines.append("")

    # Callers
    callers = graph.get_callers(func_addr)
    lines.append(f"Callers ({len(callers)}):")
    for caller_addr in callers[:20]:
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

    return "\n".join(lines)


@tool(category="decompilation")
def suggest_function_name(
    address: Annotated[str, "Function address (hex string)"],
) -> str:
    """Suggest meaningful names for anonymous functions using pattern recognition."""

    from ...core.function_naming import FunctionNamer, extract_function_features

    ea = parse_addr(address)
    func = ida_funcs.get_func(ea)
    if not func:
        return f"No function at 0x{ea:x}"

    # Collect function data
    func_data = {
        "address": func.start_ea,
        "name": ida_name.get_name(func.start_ea) or f"sub_{func.start_ea:x}",
        "size": func.end_ea - func.start_ea,
        "arg_count": 0,  # Would need decompiler for accurate count
    }

    # Collect xref data
    xref_data = {
        "callees": [],
        "callers": [],
        "strings": [],
        "imports": [],
    }

    # Get callees
    for item in idautils.FuncItems(func.start_ea):
        for xref in idautils.CodeRefsFrom(item, 0):
            target_func = ida_funcs.get_func(xref.to)
            if target_func and target_func.start_ea != func.start_ea:
                callee_name = ida_name.get_name(target_func.start_ea)
                if callee_name:
                    xref_data["callees"].append({"name": callee_name})

    # Get string refs
    for item in idautils.FuncItems(func.start_ea):
        for xref in idautils.DataRefsFrom(item):
            string_type = idaapi.get_type(xref.to) or idaapi.get_type(idaapi.get_full_flags(xref.to))
            if string_type and "char" in str(string_type).lower():
                try:
                    str_val = ida_bytes.get_strlit_contents(xref.to)
                    if str_val:
                        xref_data["strings"].append(str_val.decode("utf-8", errors="ignore"))
                except:
                    pass

    # Extract features and get suggestions
    features = extract_function_features(func_data, xref_data)
    namer = FunctionNamer()
    suggestions = namer.suggest_name(features)

    if not suggestions:
        return f"No suggestions for {func_data['name']}"

    lines = []
    lines.append(f"=== Name Suggestions for {func_data['name']} ===")
    lines.append(f"Address: 0x{func.start_ea:x}")
    lines.append("")

    for i, suggestion in enumerate(suggestions, 1):
        lines.append(f"{i}. {suggestion.name}")
        lines.append(f"   Confidence: {suggestion.confidence:.2f}")
        lines.append(f"   Pattern: {suggestion.pattern.value}")
        lines.append(f"   Reason: {suggestion.reason}")
        lines.append("")

    return "\n".join(lines)


@tool(category="decompilation")
def search_similar_functions(
    address: Annotated[str, "Function address (hex string)"],
    threshold: Annotated[float, "Similarity threshold (0.0-1.0)"] = 0.3,
    max_results: Annotated[int, "Maximum results"] = 20,
) -> str:
    """Find functions similar to the target using Jaccard similarity."""

    from ...core.xref import build_xref_graph

    ea = parse_addr(address)
    func = ida_funcs.get_func(ea)
    if not func:
        return f"No function at 0x{ea:x}"

    # Build xref graph
    functions = []
    for func_ea in idautils.Functions():
        curr_func = ida_funcs.get_func(func_ea)
        if curr_func:
            functions.append(
                {
                    "address": func_ea,
                    "name": ida_name.get_name(func_ea) or f"sub_{func_ea:x}",
                    "size": curr_func.end_ea - curr_func.start_ea,
                }
            )

    xrefs = []
    for func_ea in idautils.Functions():
        curr_func = ida_funcs.get_func(func_ea)
        if curr_func:
            for item in idautils.FuncItems(func_ea):
                for xref in idautils.CodeRefsFrom(item, 0):
                    target_func = ida_funcs.get_func(xref.to)
                    if target_func and target_func.start_ea != func_ea:
                        xrefs.append({"source": func_ea, "target": target_func.start_ea, "type": "call"})

    graph = build_xref_graph(functions, xrefs)

    # Find similar functions
    target_addr = func.start_ea
    similar = graph.find_similar_functions(target_addr, threshold)

    if not similar:
        return f"No functions found with similarity >= {threshold}"

    lines = []
    lines.append(f"=== Functions Similar to {ida_name.get_name(target_addr)} ===")
    lines.append(f"Address: 0x{target_addr:x}")
    lines.append("")

    for i, (sim_addr, similarity) in enumerate(similar[:max_results], 1):
        sim_func = graph.functions.get(sim_addr)
        if sim_func:
            lines.append(f"{i}. {sim_func.name} (0x{sim_addr:x})")
            lines.append(f"   Similarity: {similarity:.2f}")

            # Show shared callees
            target_callees = set(graph.get_callees(target_addr))
            sim_callees = set(graph.get_callees(sim_addr))
            shared = target_callees & sim_callees

            if shared:
                shared_names = [graph.functions[addr].name for addr in shared if addr in graph.functions]
                lines.append(f"   Shared callees: {', '.join(shared_names[:5])}")

            lines.append("")

    return "\n".join(lines)


@tool(category="decompilation")
def detect_types_platform() -> str:
    """Auto-detect platform types and apply standard type libraries."""

    from ...core.type_recovery import PlatformType, TypeRecoveryEngine

    # Detect platform from imports
    imports = []
    for func_ea in idautils.Functions():
        func_name = ida_name.get_name(func_ea)
        if func_name and not func_name.startswith("sub_"):
            imports.append(func_name)

    engine = TypeRecoveryEngine()
    detected = engine.detect_platform(imports)

    lines = []
    lines.append("=== Platform Detection ===")
    lines.append(f"Detected Platform: {detected}")
    lines.append(f"Analyzed {len(imports)} imports")
    lines.append("")

    if detected != PlatformType.CUSTOM:
        lines.append(f"Standard types available for {detected}:")
        library = engine.library
        for type_name, type_info in sorted(library.types.items())[:20]:
            lines.append(f"  - {type_name}: {type_info.category.value} ({type_info.size} bytes)")

    return "\n".join(lines)
