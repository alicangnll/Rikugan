"""Anti-debugging detection tool for IDA Pro.

Detects common anti-debugging techniques used in malware:
- Windows API checks (IsDebuggerPresent, CheckRemoteDebuggerPresent, etc.)
- PEB (Process Environment Block) checks
- Timing checks (RDTSC)
- Hardware breakpoint checks
- Exception-based anti-debug
- INT 2D/INT 3 checks
"""

from __future__ import annotations

import re
from typing import Any

# Try to import IDA API
try:
    import idaapi
    import idc
    import idautils
    IDA_AVAILABLE = True
except ImportError:
    IDA_AVAILABLE = False


# Anti-debugging API patterns
ANTI_DEBUG_APIS = {
    "IsDebuggerPresent": {
        "category": "windows_api",
        "severity": "high",
        "description": "Checks if debugger is present via Windows API"
    },
    "CheckRemoteDebuggerPresent": {
        "category": "windows_api",
        "severity": "high",
        "description": "Checks if process is being debugged remotely"
    },
    "OutputDebugStringA": {
        "category": "windows_api",
        "severity": "medium",
        "description": "Can detect debugger by DebugBreak behavior"
    },
    "OutputDebugStringW": {
        "category": "windows_api",
        "severity": "medium",
        "description": "Can detect debugger by DebugBreak behavior"
    },
    "DebugBreak": {
        "category": "windows_api",
        "severity": "medium",
        "description": "Triggers breakpoint to detect debugger"
    },
    "ContinueDebugEvent": {
        "category": "windows_api",
        "severity": "medium",
        "description": "Can be used for anti-debugging"
    },
    "WaitForDebugEvent": {
        "category": "windows_api",
        "severity": "medium",
        "description": "Can be used for anti-debugging"
    },
    "UnhandledExceptionFilter": {
        "category": "exception",
        "severity": "high",
        "description": "Exception-based anti-debugging"
    },
    "SetUnhandledExceptionFilter": {
        "category": "exception",
        "severity": "high",
        "description": "Sets up exception-based anti-debug"
    },
    "AddVectoredExceptionHandler": {
        "category": "exception",
        "severity": "high",
        "description": "Vectored exception handler for anti-debug"
    },
    "RaiseException": {
        "category": "exception",
        "severity": "medium",
        "description": "Can trigger anti-debug via exceptions"
    },
    "NtQueryInformationProcess": {
        "category": "nt_api",
        "severity": "high",
        "description": "Queries ProcessDebugPort/ProcessDebugObjectHandle"
    },
    "NtSetInformationThread": {
        "category": "nt_api",
        "severity": "high",
        "description": "Can hide thread from debugger"
    },
    "NtQueryObject": {
        "category": "nt_api",
        "severity": "medium",
        "description": "Can detect debugger via object namespaces"
    },
    "NtClose": {
        "category": "nt_api",
        "severity": "medium",
        "description": "Invalid handle close to detect debugger"
    },
    "GetTickCount": {
        "category": "timing",
        "severity": "low",
        "description": "Timing check via tick count"
    },
    "QueryPerformanceCounter": {
        "category": "timing",
        "severity": "medium",
        "description": "High-resolution timing check"
    },
    "timeGetTime": {
        "category": "timing",
        "severity": "low",
        "description": "Timing check via multimedia timer"
    },
}

# Assembly instruction patterns for anti-debug
ANTI_DEBUG_INSTRUCTIONS = {
    "rdtsc": {
        "category": "timing",
        "severity": "medium",
        "description": "Read Time-Stamp Counter for timing checks"
    },
    "int 2d": {
        "category": "exception",
        "severity": "high",
        "description": "INT 2D exception-based anti-debug"
    },
    "int 3": {
        "category": "exception",
        "severity": "medium",
        "description": "Software breakpoint (can be anti-debug)"
    },
    "icebp": {
        "category": "exception",
        "severity": "high",
        "description": "ICEBP instruction (F1 byte) for anti-debug"
    },
    "str": {
        "category": "hardware",
        "severity": "medium",
        "description": "Store Task Register - detects hardware debug registers"
    },
    "sidt": {
        "category": "hardware",
        "severity": "medium",
        "description": "Store IDT - can detect debugger patches"
    },
    "sgdt": {
        "category": "hardware",
        "severity": "medium",
        "description": "Store GDT - can detect debugger modifications"
    },
    "smsw": {
        "category": "hardware",
        "severity": "low",
        "description": "Store Machine Status Word"
    },
}


def detect_anti_debug_apis() -> list[dict[str, Any]]:
    """Detect anti-debugging API calls in the binary.

    Returns:
        List of dicts with API name, address, and info
    """
    if not IDA_AVAILABLE:
        return []

    results = []

    # Search for anti-debug API imports
    for func_ea in idautils.Functions():
        func_name = idc.get_func_name(func_ea)

        # Check if function name matches anti-debug APIs
        for api_name, api_info in ANTI_DEBUG_APIS.items():
            if api_name.lower() in func_name.lower():
                results.append({
                    "address": func_ea,
                    "function": func_name,
                    "api": api_name,
                    "category": api_info["category"],
                    "severity": api_info["severity"],
                    "description": api_info["description"],
                })

    return results


def detect_anti_debug_instructions() -> list[dict[str, Any]]:
    """Detect anti-debugging assembly instructions.

    Returns:
        List of dicts with address, instruction, and info
    """
    if not IDA_AVAILABLE:
        return []

    results = []

    # Scan code segments for suspicious instructions
    for seg_ea in idautils.Segments():
        seg_name = idc.get_segm_name(seg_ea)
        if not seg_name.startswith((".text", ".code", "CODE")):
            continue

        for func_ea in idautils.Functions(seg_ea, seg_ea + idc.get_segm_end(seg_ea)):
            # Scan instructions in function
            for instr_ea in idautils.Heads(func_ea, idc.get_func_end(func_ea)):
                disasm = idc.generate_disasm_text(instr_ea)
                if not disasm:
                    continue

                disasm_lower = disasm.lower()

                # Check for anti-debug instructions
                for instr_name, instr_info in ANTI_DEBUG_INSTRUCTIONS.items():
                    if instr_name in disasm_lower:
                        results.append({
                            "address": instr_ea,
                            "instruction": disasm,
                            "category": instr_info["category"],
                            "severity": instr_info["severity"],
                            "description": instr_info["description"],
                        })
                        break

    return results


def detect_peb_checks() -> list[dict[str, Any]]:
    """Detect PEB (Process Environment Block) anti-debug checks.

    Returns:
        List of PEB check locations
    """
    if not IDA_AVAILABLE:
        return []

    results = []

    # PEB BeingDebugged check patterns
    # fs:[30h] on x86, gs:[60h] on x64
    peb_patterns = [
        r"mov.*\[.*0x30\]",  # x86 PEB access
        r"mov.*\[.*0x60\]",  # x64 PEB access
        r"mov.*\[.*48\]",    # x64 PEB+2 offset
        r"fs:\[30\]",       # Direct x86 PEB
        r"gs:\[60\]",       # Direct x64 PEB
    ]

    for func_ea in idautils.Functions():
        func_name = idc.get_func_name(func_ea)

        # Check function for PEB access patterns
        func_text = ""
        for instr_ea in idautils.Heads(func_ea, idc.get_func_end(func_ea)):
            disasm = idc.generate_disasm_text(instr_ea)
            if disasm:
                func_text += disasm.lower() + "\n"

        for pattern in peb_patterns:
            if re.search(pattern, func_text, re.IGNORECASE):
                results.append({
                    "address": func_ea,
                    "function": func_name,
                    "category": "peb_check",
                    "severity": "high",
                    "description": "PEB BeingDebugged check",
                })
                break

    return results


def scan_all_anti_debug() -> dict[str, list[dict[str, Any]]]:
    """Run all anti-debug detection scans.

    Returns:
        Dict with categories as keys and results as values
    """
    return {
        "api_calls": detect_anti_debug_apis(),
        "instructions": detect_anti_debug_instructions(),
        "peb_checks": detect_peb_checks(),
    }


def format_anti_debug_report(results: dict[str, list[dict[str, Any]]]) -> str:
    """Format anti-debug results as markdown report.

    Args:
        results: Results from scan_all_anti_debug()

    Returns:
        Formatted markdown report
    """
    if not results:
        return "No anti-debugging techniques detected."

    report_lines = ["## 🔍 Anti-Debugging Detection Report\n"]

    total_count = sum(len(v) for v in results.values())
    report_lines.append(f"**Total findings:** {total_count}\n")

    # API calls
    if results["api_calls"]:
        report_lines.append("### 📡 Anti-Debug API Calls\n")
        for item in results["api_calls"]:
            severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(item["severity"], "⚪")
            report_lines.append(
                f"- {severity_icon} **{item['function']}** at `{item['address']:X}`\n"
                f"  - *{item['description']}*\n"
            )

    # Instructions
    if results["instructions"]:
        report_lines.append("\n### ⚠️ Suspicious Instructions\n")
        for item in results["instructions"]:
            severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(item["severity"], "⚪")
            report_lines.append(
                f"- {severity_icon} `{item['instruction']}` at `{item['address']:X}`\n"
                f"  - *{item['description']}*\n"
            )

    # PEB checks
    if results["peb_checks"]:
        report_lines.append("\n### 🧠 PEB Checks\n")
        for item in results["peb_checks"]:
            report_lines.append(
                f"- 🔴 **{item['function']}** at `{item['address']:X}`\n"
                f"  - *{item['description']}*\n"
            )

    return "\n".join(report_lines)


if __name__ == "__main__":
    # Test detection (requires IDA)
    if IDA_AVAILABLE:
        results = scan_all_anti_debug()
        report = format_anti_debug_report(results)
        print(report)
    else:
        print("IDA Pro API not available")
