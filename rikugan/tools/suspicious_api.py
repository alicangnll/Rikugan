"""Suspicious API call detection and highlighting for malware analysis.

Detects and categorizes potentially dangerous API calls:
- Process injection APIs
- Code injection APIs
- Memory manipulation APIs
- Registry manipulation APIs
- File system APIs
- Network APIs
- Crypto APIs
- Anti-analysis APIs
"""

from __future__ import annotations

from typing import Any

# Try to import IDA API
try:
    import idaapi
    import idc
    import idautils
    IDA_AVAILABLE = True
except ImportError:
    IDA_AVAILABLE = False


# Suspicious API categories and patterns
SUSPICIOUS_APIS = {
    # Process Injection
    "CreateRemoteThread": {
        "category": "process_injection",
        "severity": "critical",
        "description": "Injects code into remote process",
        "mitre": "T1055"
    },
    "WriteProcessMemory": {
        "category": "process_injection",
        "severity": "critical",
        "description": "Writes to remote process memory",
        "mitre": "T1055"
    },
    "ReadProcessMemory": {
        "category": "process_injection",
        "severity": "high",
        "description": "Reads from remote process memory",
        "mitre": "T1005"
    },
    "VirtualAllocEx": {
        "category": "process_injection",
        "severity": "critical",
        "description": "Allocates memory in remote process",
        "mitre": "T1055"
    },
    "NtAllocateVirtualMemory": {
        "category": "process_injection",
        "severity": "critical",
        "description": "Allocates memory in remote process",
        "mitre": "T1055"
    },
    "NtWriteVirtualMemory": {
        "category": "process_injection",
        "severity": "critical",
        "description": "Writes to remote process memory",
        "mitre": "T1055"
    },
    "NtReadVirtualMemory": {
        "category": "process_injection",
        "severity": "high",
        "description": "Reads from remote process memory",
        "mitre": "T1005"
    },
    "NtCreateThreadEx": {
        "category": "process_injection",
        "severity": "critical",
        "description": "Creates thread in remote process",
        "mitre": "T1055"
    },
    "RtlCreateUserThread": {
        "category": "process_injection",
        "severity": "critical",
        "description": "Creates thread in remote process",
        "mitre": "T1055"
    },
    "QueueUserAPC": {
        "category": "process_injection",
        "severity": "high",
        "description": "Queues APC to remote thread",
        "mitre": "T1055"
    },
    "NtQueueApcThread": {
        "category": "process_injection",
        "severity": "high",
        "description": "Queues APC to remote thread",
        "mitre": "T1055"
    },

    # Code Injection
    "SetWindowsHookEx": {
        "category": "code_injection",
        "severity": "high",
        "description": "Sets Windows hook for code injection",
        "mitre": "T1055"
    },
    "SetWindowsHookExA": {
        "category": "code_injection",
        "severity": "high",
        "description": "Sets Windows hook for code injection",
        "mitre": "T1055"
    },
    "SetWindowsHookExW": {
        "category": "code_injection",
        "severity": "high",
        "description": "Sets Windows hook for code injection",
        "mitre": "T1055"
    },

    # Memory Manipulation
    "VirtualProtect": {
        "category": "memory_manipulation",
        "severity": "high",
        "description": "Changes memory protection (RWX)",
        "mitre": "T1055"
    },
    "VirtualProtectEx": {
        "category": "memory_manipulation",
        "severity": "high",
        "description": "Changes remote memory protection",
        "mitre": "T1055"
    },
    "NtProtectVirtualMemory": {
        "category": "memory_manipulation",
        "severity": "high",
        "description": "Changes memory protection",
        "mitre": "T1055"
    },

    # Process Manipulation
    "CreateProcess": {
        "category": "process_manipulation",
        "severity": "medium",
        "description": "Creates new process",
        "mitre": "T1059"
    },
    "CreateProcessA": {
        "category": "process_manipulation",
        "severity": "medium",
        "description": "Creates new process",
        "mitre": "T1059"
    },
    "CreateProcessW": {
        "category": "process_manipulation",
        "severity": "medium",
        "description": "Creates new process",
        "mitre": "T1059"
    },
    "ShellExecute": {
        "category": "process_manipulation",
        "severity": "medium",
        "description": "Executes program/file",
        "mitre": "T1059"
    },
    "ShellExecuteA": {
        "category": "process_manipulation",
        "severity": "medium",
        "description": "Executes program/file",
        "mitre": "T1059"
    },
    "ShellExecuteW": {
        "category": "process_manipulation",
        "severity": "medium",
        "description": "Executes program/file",
        "mitre": "T1059"
    },
    "WinExec": {
        "category": "process_manipulation",
        "severity": "medium",
        "description": "Executes program",
        "mitre": "T1059"
    },
    "NtCreateProcess": {
        "category": "process_manipulation",
        "severity": "medium",
        "description": "Creates new process",
        "mitre": "T1059"
    },
    "NtCreateProcessEx": {
        "category": "process_manipulation",
        "severity": "medium",
        "description": "Creates new process",
        "mitre": "T1059"
    },
    "NtCreateThread": {
        "category": "process_manipulation",
        "severity": "high",
        "description": "Creates new thread",
        "mitre": "T1055"
    },

    # Registry
    "RegCreateKey": {
        "category": "registry",
        "severity": "medium",
        "description": "Creates registry key",
        "mitre": "T1547"
    },
    "RegCreateKeyA": {
        "category": "registry",
        "severity": "medium",
        "description": "Creates registry key",
        "mitre": "T1547"
    },
    "RegCreateKeyW": {
        "category": "registry",
        "severity": "medium",
        "description": "Creates registry key",
        "mitre": "T1547"
    },
    "RegSetValue": {
        "category": "registry",
        "severity": "medium",
        "description": "Sets registry value",
        "mitre": "T1547"
    },
    "RegSetValueEx": {
        "category": "registry",
        "severity": "medium",
        "description": "Sets registry value",
        "mitre": "T1547"
    },
    "RegOpenKey": {
        "category": "registry",
        "severity": "low",
        "description": "Opens registry key",
        "mitre": "T1012"
    },
    "RegOpenKeyA": {
        "category": "registry",
        "severity": "low",
        "description": "Opens registry key",
        "mitre": "T1012"
    },
    "RegOpenKeyW": {
        "category": "registry",
        "severity": "low",
        "description": "Opens registry key",
        "mitre": "T1012"
    },
    "RegCloseKey": {
        "category": "registry",
        "severity": "low",
        "description": "Closes registry key",
        "mitre": "T1012"
    },

    # File System
    "CreateFile": {
        "category": "file_system",
        "severity": "medium",
        "description": "Creates/opens file",
        "mitre": "T1005"
    },
    "CreateFileA": {
        "category": "file_system",
        "severity": "medium",
        "description": "Creates/opens file",
        "mitre": "T1005"
    },
    "CreateFileW": {
        "category": "file_system",
        "severity": "medium",
        "description": "Creates/opens file",
        "mitre": "T1005"
    },
    "DeleteFile": {
        "category": "file_system",
        "severity": "medium",
        "description": "Deletes file",
        "mitre": "T1005"
    },
    "DeleteFileA": {
        "category": "file_system",
        "severity": "medium",
        "description": "Deletes file",
        "mitre": "T1005"
    },
    "DeleteFileW": {
        "category": "file_system",
        "severity": "medium",
        "description": "Deletes file",
        "mitre": "T1005"
    },
    "CopyFile": {
        "category": "file_system",
        "severity": "medium",
        "description": "Copies file",
        "mitre": "T1005"
    },
    "CopyFileA": {
        "category": "file_system",
        "severity": "medium",
        "description": "Copies file",
        "mitre": "T1005"
    },
    "CopyFileW": {
        "category": "file_system",
        "severity": "medium",
        "description": "Copies file",
        "mitre": "T1005"
    },
    "MoveFile": {
        "category": "file_system",
        "severity": "medium",
        "description": "Moves file",
        "mitre": "T1005"
    },
    "MoveFileA": {
        "category": "file_system",
        "severity": "medium",
        "description": "Moves file",
        "mitre": "T1005"
    },
    "MoveFileW": {
        "category": "file_system",
        "severity": "medium",
        "description": "Moves file",
        "mitre": "T1005"
    },
    "FindFirstFile": {
        "category": "file_system",
        "severity": "low",
        "description": "Searches for files",
        "mitre": "T1083"
    },
    "FindNextFile": {
        "category": "file_system",
        "severity": "low",
        "description": "Continues file search",
        "mitre": "T1083"
    },

    # Network
    "InternetOpen": {
        "category": "network",
        "severity": "medium",
        "description": "Initializes WinINet",
        "mitre": "T1071"
    },
    "InternetOpenA": {
        "category": "network",
        "severity": "medium",
        "description": "Initializes WinINet",
        "mitre": "T1071"
    },
    "InternetOpenW": {
        "category": "network",
        "severity": "medium",
        "description": "Initializes WinINet",
        "mitre": "T1071"
    },
    "InternetConnect": {
        "category": "network",
        "severity": "high",
        "description": "Establishes HTTP/FTP connection",
        "mitre": "T1071"
    },
    "InternetConnectA": {
        "category": "network",
        "severity": "high",
        "description": "Establishes HTTP/FTP connection",
        "mitre": "T1071"
    },
    "InternetConnectW": {
        "category": "network",
        "severity": "high",
        "description": "Establishes HTTP/FTP connection",
        "mitre": "T1071"
    },
    "HttpOpenRequest": {
        "category": "network",
        "severity": "high",
        "description": "Opens HTTP request",
        "mitre": "T1071"
    },
    "HttpSendRequest": {
        "category": "network",
        "severity": "high",
        "description": "Sends HTTP request",
        "mitre": "T1071"
    },
    "HttpSendRequestA": {
        "category": "network",
        "severity": "high",
        "description": "Sends HTTP request",
        "mitre": "T1071"
    },
    "HttpSendRequestW": {
        "category": "network",
        "severity": "high",
        "description": "Sends HTTP request",
        "mitre": "T1071"
    },
    "socket": {
        "category": "network",
        "severity": "medium",
        "description": "Creates socket",
        "mitre": "T1071"
    },
    "connect": {
        "category": "network",
        "severity": "medium",
        "description": "Connects to remote host",
        "mitre": "T1071"
    },
    "send": {
        "category": "network",
        "severity": "medium",
        "description": "Sends data over socket",
        "mitre": "T1071"
    },
    "recv": {
        "category": "network",
        "severity": "medium",
        "description": "Receives data from socket",
        "mitre": "T1071"
    },
    "WSAStartup": {
        "category": "network",
        "severity": "low",
        "description": "Initializes Winsock",
        "mitre": "T1071"
    },

    # Crypto
    "CryptAcquireContext": {
        "category": "crypto",
        "severity": "medium",
        "description": "Acquires crypto context",
        "mitre": "T1020"
    },
    "CryptCreateHash": {
        "category": "crypto",
        "severity": "medium",
        "description": "Creates hash object",
        "mitre": "T1020"
    },
    "CryptHashData": {
        "category": "crypto",
        "severity": "medium",
        "description": "Hashes data",
        "mitre": "T1020"
    },
    "CryptEncrypt": {
        "category": "crypto",
        "severity": "high",
        "description": "Encrypts data",
        "mitre": "T1020"
    },
    "CryptDecrypt": {
        "category": "crypto",
        "severity": "high",
        "description": "Decrypts data",
        "mitre": "T1020"
    },
    "CryptGenKey": {
        "category": "crypto",
        "severity": "medium",
        "description": "Generates crypto key",
        "mitre": "T1020"
    },
    "CryptImportKey": {
        "category": "crypto",
        "severity": "high",
        "description": "Imports crypto key",
        "mitre": "T1020"
    },
    "CryptExportKey": {
        "category": "crypto",
        "severity": "high",
        "description": "Exports crypto key",
        "mitre": "T1020"
    },
    "CryptDeriveKey": {
        "category": "crypto",
        "severity": "medium",
        "description": "Derives crypto key",
        "mitre": "T1020"
    },
    "CryptDestroyKey": {
        "category": "crypto",
        "severity": "low",
        "description": "Destroys crypto key",
        "mitre": "T1020"
    },

    # Anti-Analysis
    "GetModuleHandle": {
        "category": "anti_analysis",
        "severity": "low",
        "description": "Gets module handle (can detect analysis)",
        "mitre": "T1014"
    },
    "GetModuleHandleA": {
        "category": "anti_analysis",
        "severity": "low",
        "description": "Gets module handle",
        "mitre": "T1014"
    },
    "GetModuleHandleW": {
        "category": "anti_analysis",
        "severity": "low",
        "description": "Gets module handle",
        "mitre": "T1014"
    },
    "LoadLibrary": {
        "category": "anti_analysis",
        "severity": "medium",
        "description": "Loads DLL dynamically",
        "mitre": "T1014"
    },
    "LoadLibraryA": {
        "category": "anti_analysis",
        "severity": "medium",
        "description": "Loads DLL dynamically",
        "mitre": "T1014"
    },
    "LoadLibraryW": {
        "category": "anti_analysis",
        "severity": "medium",
        "description": "Loads DLL dynamically",
        "mitre": "T1014"
    },
    "GetProcAddress": {
        "category": "anti_analysis",
        "severity": "high",
        "description": "Gets function address (API resolution)",
        "mitre": "T1014"
    },
}


def detect_suspicious_apis() -> list[dict[str, Any]]:
    """Detect suspicious API imports in the binary.

    Returns:
        List of suspicious API calls with metadata
    """
    if not IDA_AVAILABLE:
        return []

    results = []

    # Scan all functions for suspicious API names
    for func_ea in idautils.Functions():
        func_name = idc.get_func_name(func_ea)

        # Check if function name matches any suspicious API
        for api_name, api_info in SUSPICIOUS_APIS.items():
            if api_name.lower() in func_name.lower():
                results.append({
                    "address": func_ea,
                    "function": func_name,
                    "api": api_name,
                    "category": api_info["category"],
                    "severity": api_info["severity"],
                    "description": api_info["description"],
                    "mitre": api_info.get("mitre", ""),
                })

    return results


def get_apis_by_category(category: str) -> list[dict[str, Any]]:
    """Get suspicious APIs by category.

    Args:
        category: Category name (process_injection, code_injection, etc.)

    Returns:
        List of APIs in the category
    """
    return [
        {**info, "name": name}
        for name, info in SUSPICIOUS_APIS.items()
        if info["category"] == category
    ]


def get_apis_by_severity(severity: str) -> list[dict[str, Any]]:
    """Get suspicious APIs by severity.

    Args:
        severity: Severity level (critical, high, medium, low)

    Returns:
        List of APIs with the severity
    """
    return [
        {**info, "name": name}
        for name, info in SUSPICIOUS_APIS.items()
        if info["severity"] == severity
    ]


def format_suspicious_api_report(apis: list[dict[str, Any]]) -> str:
    """Format suspicious API results as markdown report.

    Args:
        apis: List of suspicious API detections

    Returns:
        Formatted markdown report
    """
    if not apis:
        return "No suspicious API calls detected."

    # Group by category
    by_category = {}
    for api in apis:
        category = api["category"]
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(api)

    # Format report
    report_lines = ["## 🚨 Suspicious API Detection Report\n"]
    report_lines.append(f"**Total suspicious APIs:** {len(apis)}\n")

    # Sort categories by severity
    category_order = ["process_injection", "code_injection", "memory_manipulation",
                      "process_manipulation", "crypto", "network", "registry",
                      "file_system", "anti_analysis"]

    for category in category_order:
        if category not in by_category:
            continue

        category_apis = by_category[category]
        category_title = category.replace("_", " ").title()

        report_lines.append(f"### 📋 {category_title}\n")

        for api in sorted(category_apis, key=lambda x: x["address"]):
            severity_icon = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢"
            }.get(api["severity"], "⚪")

            mitre_ref = f" (MITRE:{api['mitre']})" if api.get("mitre") else ""

            report_lines.append(
                f"- {severity_icon} **{api['function']}** at `{api['address']:X}`{mitre_ref}\n"
                f"  - *{api['description']}*\n"
            )

    return "\n".join(report_lines)


# Color schemes for highlighting in markdown
API_CATEGORY_COLORS = {
    "process_injection": "#ff6b6b",      # Red
    "code_injection": "#ee5a5a",          # Dark Red
    "memory_manipulation": "#f06595",     # Pink
    "process_manipulation": "#cc5de8",    # Purple
    "crypto": "#9d4edd",                   # Purple
    "network": "#7c3aed",                  # Dark Purple
    "registry": "#6366f1",                 # Indigo
    "file_system": "#3b82f6",              # Blue
    "anti_analysis": "#8b5cf6",            # Violet
}

API_SEVERITY_ICONS = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🟢",
}


if __name__ == "__main__":
    # Test detection (requires IDA)
    if IDA_AVAILABLE:
        results = detect_suspicious_apis()
        report = format_suspicious_api_report(results)
        print(report)
    else:
        print("IDA Pro API not available")
