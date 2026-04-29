# Rikugan Development Features

This document describes development-oriented features in Rikugan that help during plugin development and malware analysis workflows.

## Auto-Reload (Development Mode)

Rikugan can automatically reload itself when source files change, making development faster without requiring IDA restarts.

### Enabling Auto-Reload

**Method 1: Environment Variable**
```bash
# Set environment variable before starting IDA
export RIKUGAN_AUTO_RELOAD=1
ida64 /path/to/binary
```

**Method 2: Configuration**
```python
# In Rikugan config (settings.json)
{
    "auto_reload": true
}
```

**Method 3: Keyboard Shortcut**
- Press `Ctrl+Shift+R` in IDA to toggle auto-reload on/off
- Check the IDA console for status messages

### How It Works

1. **File Watching**: Monitors all Python source files in the Rikugan package
2. **Change Detection**: Checks file hashes every 500ms
3. **Debouncing**: Waits 2 seconds after the last change before reloading
4. **Hot Reload**: Reloads modules while preserving IDA session state
5. **UI Updates**: Notifies registered callbacks after successful reload

### Development Workflow

```bash
# Terminal 1: Start IDA with auto-reload enabled
export RIKUGAN_AUTO_RELOAD=1
ida64 /path/to/malware

# Terminal 2: Edit Rikugan source code
vim rikugan/ui/markdown.py

# Auto-reload happens automatically when you save!
# Check IDA console for: "Reloading Rikugan due to source changes..."
```

### Status Messages

- `File watcher started` - Auto-reload is monitoring for changes
- `Changed: rikugan/ui/markdown.py` - File was modified
- `Reloading Rikugan...` - Reload in progress
- `Rikugan reloaded successfully` - Reload completed
- `Auto-reload disabled` - Auto-reload stopped

### Troubleshooting

**Auto-reload not working?**
- Check that `RIKUGAN_AUTO_RELOAD=1` is set
- Verify file permissions on Rikugan source files
- Check IDA console for error messages

**Reload causes errors?**
- Some changes require full IDA restart (e.g., adding new dependencies)
- Check IDA console for specific module reload failures
- Use `Ctrl+Shift+R` to disable auto-reload if needed

## Findings Bookmarking

Bookmark important findings during malware analysis with addresses, notes, tags, and categories.

### Basic Usage

**Add a finding** (in chat with AI):
```
Add a finding at 0x401000 for "Process injection entry point"
```

**Navigate to findings**:
- Click on finding links in AI responses: `[FINDING:0x401000]`
- Links will jump to the address and show finding details

**Finding categories**:
- [CRIT] **Critical** - Critical security issues
- [HIGH] **Suspicious** - Potentially malicious code
- [V] **Verified** - Confirmed findings
- [INT] **Interesting** - Notable code/behavior
- [FP] **False Positive** - Confirmed benign
- [?] **Question** - Needs investigation

### Finding Storage

Findings are stored in JSON alongside your IDB:
```
/path/to/binary_findings.json
```

**Example findings file**:
```json
[
  {
    "address": 1052672,
    "title": "Process injection entry point",
    "category": "critical",
    "notes": "Uses CreateRemoteThread to inject shellcode",
    "tags": ["injection", "process"],
    "timestamp": "2025-01-15T10:30:00.000000"
  }
]
```

### Programmatic Usage

```python
from rikugan.tools.findings_bookmark import get_findings_manager

# Get manager for current IDB
manager = get_findings_manager()

# Add a finding
finding = manager.add_finding(
    address=0x401000,
    title="Process injection",
    category="critical",
    notes="Uses CreateRemoteThread",
    tags=["injection", "process"]
)

# Get finding at address
finding = manager.get_finding(0x401000)
if finding:
    print(f"Title: {finding.title}")
    print(f"Category: {finding.category}")

# Export findings as markdown
report = manager.export_to_markdown()
print(report)

# Get findings by category
critical = manager.get_findings_by_category("critical")
print(f"Critical findings: {len(critical)}")
```

### Markdown Report Example

```markdown
# Findings Bookmark Report

**Total Findings:** 3
**Generated:** 2025-01-15 10:30:00

## Critical
*Critical security issue*

### **Process injection entry point**
- **Address:** `401000`
- **Category:** Critical
- **Date:** 2025-01-15T10:30:00.000000
- **Notes:** Uses CreateRemoteThread to inject shellcode
```

## Suspicious API Highlighting

Rikugan automatically highlights dangerous API calls in AI responses with color-coded severity levels.

### API Categories

**Process Injection ([CRIT] Critical)**
- `CreateRemoteThread`, `WriteProcessMemory`, `VirtualAllocEx`
- MITRE: T1055

**Memory Manipulation ([HIGH] High)**
- `VirtualProtect`, `VirtualProtectEx`
- MITRE: T1055

**Anti-Analysis ([MED] Medium)**
- `IsDebuggerPresent`, `CheckRemoteDebuggerPresent`
- MITRE: T1014

**Crypto ([MED] Medium)**
- `CryptEncrypt`, `CryptDecrypt`, `CryptGenKey`
- MITRE: T1020

**Network ([MED] Medium)**
- `InternetConnect`, `HttpSendRequest`, `socket`, `connect`
- MITRE: T1071

### Highlighting Example

When AI mentions APIs in responses:
```
The malware uses CreateRemoteThread for process injection
```

Becomes:
```
The malware uses <span style="background:#ff6b6b; color:white;">CreateRemoteThread</span> for process injection
```

## Hex Address Linking

All hex addresses in AI responses become clickable links for navigation.

### Supported Formats

- `0x401000` - Standard hex
- `00401000` - 8-digit hex
- `401000h` - Assembly suffix
- `:00401000` - IDA prefix

### Usage

Click any address link in AI responses to jump to that location in IDA's disassembly view.

## Anti-Debug Detection

Rikugan detects common anti-debugging techniques used by malware.

### Detection Categories

**Windows API Checks**
- `IsDebuggerPresent`
- `CheckRemoteDebuggerPresent`
- `NtQueryInformationProcess`

**PEB Checks**
- `fs:[30h]` / `gs:[60h]` BeingDebugged checks
- PEB structure access patterns

**Assembly Instructions**
- `rdtsc` - Timing checks
- `int 2d` - Exception-based anti-debug
- `int 3` - Software breakpoints

**Exception Handlers**
- `SetUnhandledExceptionFilter`
- `AddVectoredExceptionHandler`

### Usage

Rikugan automatically scans for anti-debug techniques during analysis and reports findings in AI responses.
