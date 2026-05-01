"""Lightweight Markdown to HTML converter for QLabel rich text.

Handles the subset of Markdown that LLMs commonly produce:
- Fenced code blocks (```lang ... ```)
- Inline code (`code`)
- Bold (**text**), italic (*text*)
- Headers (# through ####)
- Bullet lists (- item, * item)
- Numbered lists (1. item)
- Links [text](url)
- Tables (| col1 | col2 | ...)
- Paragraphs (double newline)
- Horizontal rules (---, ***)

No external dependencies. Output targets Qt's supported HTML subset.
"""

from __future__ import annotations

import html
import re

# -- Colors matching the dark theme --
_CODE_BG = "#2d2d2d"
_CODE_FG = "#ce9178"
_CODE_BORDER = "#3c3c3c"
_BLOCK_BG = "#1a1a1a"
_BLOCK_FG = "#d4d4d4"
_LINK_COLOR = "#569cd6"
_HR_COLOR = "#3c3c3c"
_H_COLOR = "#569cd6"

# Suspicious API highlighting colors
_API_CRITICAL_BG = "#3d1f1f"
_API_CRITICAL_FG = "#ff6b6b"
_API_HIGH_BG = "#3d2a1f"
_API_HIGH_FG = "#ffa07a"
_API_MEDIUM_BG = "#3d3a1f"
_API_MEDIUM_FG = "#ffd93d"
_API_LOW_BG = "#1f3d2a"
_API_LOW_FG = "#6bff98"

# Anti-debug highlighting
_ANTI_DEBUG_BG = "#2d1f3d"
_ANTI_DEBUG_FG = "#d9b3ff"

_MARKDOWN_HINT_RE = re.compile(
    r"(^#{1,4}\s)|(^\s*[-*]\s+)|(^\s*\d+[.)]\s+)|```|`[^`]+`|\*\*|__|(?<!\w)\*(.+?)\*(?!\w)|(?<!\w)_(.+?)_(?!\w)|\[[^\]]+\]\([^)]+\)|^[-*_]{3,}\s*$|^\|.*\||[┌─┐│└┘▽▼▲△╔╗╚╝║═╟┤┬┴├┤┼┴┬╭╮╰╯╱╲╳▀▄■▴▸▶►◄↕↔↖↗↘↙→←↑↓⇐⇑⇒⇔⇕⇖⇗⇘⇙⌈⌉⌊⌋⌌⌍⌎⏏⏐⏑⏒⏓⏔⏕⏖⏗⏘⏙␟␠␡␢␣␤␥␦␧␨␩␪␫␬␭␮␯␰␱␲␳␴␵␶␷␸␹␺␻␼␽␾␿⏀⏁⏂⏃⏄⏅⏆⏇⏈⏉⏊⏋⏌⏍⏎⏏⏐⏑⏒⏓⏔⏕⏖⏗⏘⏙⏚⏛⏜⏝⏞⏟⏠]",
    re.MULTILINE,
)

_ASCII_ART_PATTERN = re.compile(
    r'[┌─┐│└┘▽▼▲△╔╗╚╝║═╟┤┬┴├┤┼┴┬╭╮╰╯╱╲╳▀▄■▴▸▶►◄↕↔↖↗↘↙→←↑↓⇐⇑⇒⇔⇕⇖⇗⇘⇙⌈⌉⌊⌋⌌⌍⌎⏏⏐⏑⏒⏓⏔⏕⏖⏗⏘⏙␟␠␡␢␣␤␥␦␧␨␩␪␫␬␭␮␯␰␱␲␳␴␵␶␷␸␹␺␻␼␽␾␿⏀⏁⏂⏃⏄⏅⏆⏇⏈⏉⏊⏋⏌⏍⏎⏏⏐⏑⏒⏓⏔⏕⏖⏗⏘⏙⏚⏛⏜⏝⏞⏟⏠]',
    re.MULTILINE
)

_INLINE_CODE_STYLE = (
    f"background-color:{_CODE_BG}; color:{_CODE_FG}; "
    f"padding:1px 4px; border-radius:3px; font-family:monospace; font-size:12px;"
)

# ASCII art diagram style
_DIAGRAM_STYLE = (
    f"background-color:{_BLOCK_BG}; color:{_BLOCK_FG}; "
    f"border:1px solid {_CODE_BORDER}; border-radius:4px; "
    f"padding:8px; font-family:'Monaco', 'Menlo', 'Ubuntu Mono', monospace; "
    f"font-size:11px; line-height:1.2; white-space:pre; overflow-x:auto;"
)

# Finding bookmark styles
_FINDING_STYLES = {
    "critical": f"background-color:#3d1f1f; color:#ff6b6b; border:1px solid #ff6b6b; border-radius:3px; padding:2px 6px; font-weight:bold;",
    "suspicious": f"background-color:#3d2a1f; color:#ffa07a; border:1px solid #ffa07a; border-radius:3px; padding:2px 6px;",
    "verified": f"background-color:#1f3d2a; color:#6bff98; border:1px solid #6bff98; border-radius:3px; padding:2px 6px;",
    "interesting": f"background-color:#3d3a1f; color:#ffd93d; border:1px solid #ffd93d; border-radius:3px; padding:2px 6px;",
    "question": f"background-color:#1f2a3d; color:#569cd6; border:1px solid #569cd6; border-radius:3px; padding:2px 6px;",
    "false_positive": f"background-color:#2a2a2a; color:#808080; border:1px solid #808080; border-radius:3px; padding:2px 6px;",
}

_BLOCK_CODE_STYLE = (
    f"background-color:{_BLOCK_BG}; color:{_BLOCK_FG}; "
    f"border:1px solid {_CODE_BORDER}; border-radius:4px; "
    f"padding:8px; font-family:monospace; font-size:12px; "
    f"white-space:pre-wrap; word-break:break-all;"
)

_TABLE_STYLE = (
    "border:1px solid #3c3c3c; border-collapse:collapse; "
    "margin:4px 0; width:100%;"
)
_TABLE_CELL_STYLE = (
    "border:1px solid #3c3c3c; padding:4px 8px; "
    "text-align:left; vertical-align:top;"
)
_TABLE_HEADER_STYLE = (
    "background-color:#2d2d2d; color:#569cd6; "
    "font-weight:bold; font-size:12px;"
)
_TABLE_ROW_STYLE = "font-size:12px;"


def _parse_table_row(row: str) -> list[str]:
    """Parse a markdown table row and return list of cell contents."""
    # Remove leading/trailing pipes and split
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]

    cells = [cell.strip() for cell in row.split("|")]
    return cells


def _is_separator_row(row: str) -> bool:
    """Check if a row is a table separator (contains only |, -, and spaces)."""
    row = row.strip()
    if not row.startswith("|") or not row.endswith("|"):
        return False
    # Remove leading/trailing pipes
    inner = row[1:-1].strip()
    # Check if remaining content is only |, -, and spaces
    return all(c in "|- " for c in inner)


def _parse_table(lines: list[str], start_idx: int) -> tuple[str, int]:
    """Parse a markdown table starting at start_idx.

    Returns (html_table, next_line_index).
    """
    if start_idx >= len(lines):
        return "", start_idx

    # Parse header row
    header_row = lines[start_idx]
    headers = _parse_table_row(header_row)

    # Check for separator row
    if start_idx + 1 < len(lines) and _is_separator_row(lines[start_idx + 1]):
        # This is a valid table with separator
        separator_idx = start_idx + 1
        data_start_idx = start_idx + 2
    else:
        # No separator row, treat all rows as data
        separator_idx = start_idx  # No separator
        data_start_idx = start_idx + 1

    # Parse data rows
    data_rows = []
    i = data_start_idx
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("|") and line.endswith("|"):
            data_rows.append(_parse_table_row(line))
            i += 1
        else:
            break

    # Build HTML table
    html_parts = ['<table style="' + _TABLE_STYLE + '">']

    # Header row
    html_parts.append('<tr>')
    for header in headers:
        header_html = _inline(header)
        html_parts.append(
            f'<th style="{_TABLE_CELL_STYLE}{_TABLE_HEADER_STYLE}">{header_html}</th>'
        )
    html_parts.append('</tr>')

    # Data rows
    for row in data_rows:
        html_parts.append('<tr style="' + _TABLE_ROW_STYLE + '">')
        # Ensure all rows have same number of cells as headers
        for j in range(len(headers)):
            if j < len(row):
                cell_html = _inline(row[j])
            else:
                cell_html = ""
            html_parts.append(
                f'<td style="{_TABLE_CELL_STYLE}">{cell_html}</td>'
            )
        html_parts.append('</tr>')

    html_parts.append('</table>')

    return "".join(html_parts), i


# Suspicious API detection patterns (subset for highlighting)
_SUSPICIOUS_API_PATTERNS = {
    # Critical - Process Injection
    "CreateRemoteThread": {"severity": "critical", "color": _API_CRITICAL_FG},
    "WriteProcessMemory": {"severity": "critical", "color": _API_CRITICAL_FG},
    "VirtualAllocEx": {"severity": "critical", "color": _API_CRITICAL_FG},
    "NtAllocateVirtualMemory": {"severity": "critical", "color": _API_CRITICAL_FG},
    "NtWriteVirtualMemory": {"severity": "critical", "color": _API_CRITICAL_FG},
    "NtCreateThreadEx": {"severity": "critical", "color": _API_CRITICAL_FG},
    "RtlCreateUserThread": {"severity": "critical", "color": _API_CRITICAL_FG},

    # High - Code Injection, Memory Manipulation
    "SetWindowsHookEx": {"severity": "high", "color": _API_HIGH_FG},
    "SetWindowsHookExA": {"severity": "high", "color": _API_HIGH_FG},
    "SetWindowsHookExW": {"severity": "high", "color": _API_HIGH_FG},
    "VirtualProtect": {"severity": "high", "color": _API_HIGH_FG},
    "VirtualProtectEx": {"severity": "high", "color": _API_HIGH_FG},
    "NtProtectVirtualMemory": {"severity": "high", "color": _API_HIGH_FG},

    # High - Crypto, Network
    "CryptEncrypt": {"severity": "high", "color": _API_HIGH_FG},
    "CryptDecrypt": {"severity": "high", "color": _API_HIGH_FG},
    "CryptImportKey": {"severity": "high", "color": _API_HIGH_FG},
    "CryptExportKey": {"severity": "high", "color": _API_HIGH_FG},
    "HttpSendRequest": {"severity": "high", "color": _API_HIGH_FG},
    "HttpSendRequestA": {"severity": "high", "color": _API_HIGH_FG},
    "HttpSendRequestW": {"severity": "high", "color": _API_HIGH_FG},
    "InternetConnect": {"severity": "high", "color": _API_HIGH_FG},
    "GetProcAddress": {"severity": "high", "color": _API_HIGH_FG},

    # Medium - Process/File/Registry
    "CreateProcess": {"severity": "medium", "color": _API_MEDIUM_FG},
    "ShellExecute": {"severity": "medium", "color": _API_MEDIUM_FG},
    "LoadLibrary": {"severity": "medium", "color": _API_MEDIUM_FG},
    "RegSetValue": {"severity": "medium", "color": _API_MEDIUM_FG},
    "RegSetValueEx": {"severity": "medium", "color": _API_MEDIUM_FG},
    "CreateFile": {"severity": "medium", "color": _API_MEDIUM_FG},
    "DeleteFile": {"severity": "medium", "color": _API_MEDIUM_FG},

    # Anti-debug APIs
    "IsDebuggerPresent": {"severity": "critical", "color": _ANTI_DEBUG_FG},
    "CheckRemoteDebuggerPresent": {"severity": "critical", "color": _ANTI_DEBUG_FG},
    "OutputDebugString": {"severity": "medium", "color": _ANTI_DEBUG_FG},
    "DebugBreak": {"severity": "medium", "color": _ANTI_DEBUG_FG},
    "NtQueryInformationProcess": {"severity": "critical", "color": _ANTI_DEBUG_FG},
    "UnhandledExceptionFilter": {"severity": "critical", "color": _ANTI_DEBUG_FG},
    "AddVectoredExceptionHandler": {"severity": "critical", "color": _ANTI_DEBUG_FG},
}


def _highlight_suspicious_apis(text: str) -> str:
    """Highlight suspicious API calls in text.

    Args:
        text: Input text that may contain API names

    Returns:
        Text with APIs highlighted in HTML spans
    """
    for api_name, api_info in _SUSPICIOUS_API_PATTERNS.items():
        # Match whole API name only (case-insensitive)
        pattern = r"\b" + re.escape(api_name) + r"\b"
        severity = api_info["severity"]
        color = api_info["color"]

        # Choose background color based on severity
        bg_colors = {
            "critical": _API_CRITICAL_BG,
            "high": _API_HIGH_BG,
            "medium": _API_MEDIUM_BG,
            "low": _API_LOW_BG,
        }
        bg_color = bg_colors.get(severity, _API_MEDIUM_BG)

        # Create highlighted span
        replacement = f'<span style="background-color:{bg_color}; color:{color}; padding:1px 3px; border-radius:2px; font-family:monospace; font-weight:bold;">{api_name}</span>'

        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    return text


def _has_markdown_syntax(text: str) -> bool:
    """Return True when the input likely needs markdown processing."""
    return bool(text and _MARKDOWN_HINT_RE.search(text))


def _is_ascii_art_diagram(text: str) -> bool:
    """Check if text is an ASCII art diagram (not a numbered list)."""
    if not text or len(text) < 3:
        return False

    lines = text.split('\n')
    if len(lines) < 3:
        return False

    # Exclude numbered lists - check if most lines start with numbers
    numbered_line_count = 0
    for line in lines:
        if re.match(r"^\s*\d+[.\)]\s+", line.strip()):
            numbered_line_count += 1

    # If more than 50% of lines are numbered list items, it's not a diagram
    if numbered_line_count / len(lines) > 0.5:
        return False

    # Count diagram characters
    diagram_char_count = 0
    for line in lines:
        matches = _ASCII_ART_PATTERN.findall(line)
        diagram_char_count += len(matches)

    # If average more than 3 diagram chars per line, likely a diagram
    avg_chars = diagram_char_count / len(lines)
    return avg_chars > 3


def md_to_html(text: str, return_code_blocks: bool = False) -> str | tuple:
    """Convert a Markdown string to Qt-compatible HTML.

    Args:
        text: Markdown text to convert
        return_code_blocks: If True, returns (html, code_blocks, diagram_blocks) tuple where
                           code_blocks is a list of (lang, code) tuples and
                           diagram_blocks is a list of diagram strings.

    Returns:
        HTML string, or (html, code_blocks, diagram_blocks) tuple if return_code_blocks=True.
    """
    if not text:
        return "" if not return_code_blocks else ("", [], [])

    if not _has_markdown_syntax(text):
        escaped = html.escape(text).replace("\n", "<br>")
        result = re.sub(r"(<br>\s*){3,}", "<br><br>", escaped)
        return result if not return_code_blocks else (result, [], [])

    # Phase 1: extract fenced code blocks and ASCII diagrams to protect them from inline processing
    blocks: list[str] = []
    code_blocks: list[tuple[str, str]] = []  # (lang, code) tuples
    diagram_blocks: list[tuple[str]] = []  # (diagram,) tuples
    block_counter = [0]  # Use list to allow modification in nested function
    diagram_counter = [0]  # Separate counter for diagrams

    def _stash_block(m: re.Match) -> str:
        lang = m.group(1) or ""
        code = m.group(2).strip("\n")

        # Store original code for copy button functionality
        code_blocks.append((lang, code))

        code_escaped = html.escape(code)
        lang_tag = f'<span style="color:#808080;font-size:10px;">{html.escape(lang)}</span><br>' if lang else ""
        block_html = f'<div style="{_BLOCK_CODE_STYLE}">{lang_tag}{code_escaped}</div>'
        blocks.append(block_html)
        idx = block_counter[0]
        block_counter[0] += 1
        return f"\x00BLOCK{idx}\x00"

    text = re.sub(r"```(\w*)\n(.*?)```", _stash_block, text, flags=re.DOTALL)

    # Extract ASCII art diagrams as well
    def _stash_diagram(diagram_text: str) -> str:
        diagram_blocks.append((diagram_text,))

        diagram_escaped = html.escape(diagram_text)
        diagram_html = f'<div style="{_DIAGRAM_STYLE}">{diagram_escaped}</div>'
        blocks.append(diagram_html)
        idx = diagram_counter[0]
        diagram_counter[0] += 1
        return f"\x00DIAGRAM{idx}\x00"

    # Check for diagrams line by line
    lines = text.split("\n")
    i = 0
    processed_lines = []

    # Helper to check if a line contains diagram characters
    def _has_diagram_chars(line: str) -> bool:
        if not line:
            return False
        # Check if line is a numbered list item - exclude it
        if re.match(r"^\s*\d+[.\)]\s+", line.strip()):
            return False
        # Check if line has significant diagram character density
        diagram_char_count = len(_ASCII_ART_PATTERN.findall(line))
        return diagram_char_count >= 3  # Require at least 3 diagram chars per line

    while i < len(lines):
        line = lines[i]

        # Look ahead to check if we have a diagram starting here
        if _has_diagram_chars(line):
            # Collect consecutive diagram lines
            diagram_lines = [line]
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                # Continue if next line also has diagram characters or is empty/indented
                if _has_diagram_chars(next_line) or not next_line.strip() or next_line.startswith(" "):
                    diagram_lines.append(next_line)
                    j += 1
                else:
                    break

            # If we have 3+ lines, it's likely a diagram
            if len(diagram_lines) >= 3:
                diagram_text = "\n".join(diagram_lines)
                placeholder = _stash_diagram(diagram_text)
                processed_lines.append(placeholder)
                i = j
                continue

        processed_lines.append(line)
        i += 1

    text = "\n".join(processed_lines)

    # Phase 2: process line-by-line for block-level elements
    lines = text.split("\n")
    out_lines: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Block/Diagram placeholder — pass through
        if re.match(r"^\x00(BLOCK|DIAGRAM)\d+\x00$", stripped):
            # Close any open paragraph before the block
            out_lines.append(stripped)
            i += 1
            continue

        # Table — detect table rows (start and end with |)
        if stripped.startswith("|") and stripped.endswith("|"):
            table_html, next_i = _parse_table(lines, i)
            if table_html:
                out_lines.append(table_html)
                i = next_i
                continue
            # If table parsing failed, fall through to regular text processing

        # Horizontal rule
        if re.match(r"^[-*_]{3,}\s*$", stripped):
            out_lines.append(f'<hr style="border:1px solid {_HR_COLOR};">')
            i += 1
            continue

        # Headers
        hm = re.match(r"^(#{1,4})\s+(.*)", stripped)
        if hm:
            level = len(hm.group(1))
            sizes = {1: 18, 2: 16, 3: 14, 4: 13}
            size = sizes.get(level, 13)
            h_text = _inline(hm.group(2))
            out_lines.append(
                f'<div style="color:{_H_COLOR};font-weight:bold;font-size:{size}px;margin:6px 0 2px 0;">{h_text}</div>'
            )
            i += 1
            continue

        # Bullet list — collect consecutive items
        if re.match(r"^[-*]\s+", stripped):
            items: list[str] = []
            while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                item_text = re.sub(r"^\s*[-*]\s+", "", lines[i])
                items.append(f"<li>{_inline(item_text)}</li>")
                i += 1
            out_lines.append("<ul style='margin:2px 0 2px 16px;'>" + "".join(items) + "</ul>")
            continue

        # Numbered list — collect consecutive items
        if re.match(r"^\d+[.)]\s+", stripped):
            items = []
            while i < len(lines) and re.match(r"^\s*\d+[.)]\s+", lines[i]):
                item_text = re.sub(r"^\s*\d+[.)]\s+", "", lines[i])
                items.append(f"<li>{_inline(item_text)}</li>")
                i += 1
            out_lines.append("<ol style='margin:2px 0 2px 16px;'>" + "".join(items) + "</ol>")
            continue

        # Empty line → paragraph break
        if not stripped:
            out_lines.append("<br>")
            i += 1
            continue

        # Regular text
        out_lines.append(_inline(stripped))
        i += 1

    result = "<br>".join(out_lines)

    # Phase 3: restore code blocks and diagrams (only if not returning for widget rendering)
    if not return_code_blocks:
        # Code blocks: BLOCK0, BLOCK1, BLOCK2...
        for idx, block_html in enumerate(code_blocks):
            result = result.replace(f"\x00BLOCK{idx}\x00", blocks[idx])

        # Diagram blocks: DIAGRAM0, DIAGRAM1, DIAGRAM2...
        for idx, diagram_html in enumerate(diagram_blocks):
            # Diagram blocks come after code blocks in the blocks list
            block_idx = len(code_blocks) + idx
            result = result.replace(f"\x00DIAGRAM{idx}\x00", blocks[block_idx])

    # Clean up double <br> from paragraph joins
    result = re.sub(r"(<br>\s*){3,}", "<br><br>", result)

    if return_code_blocks:
        return result, code_blocks, diagram_blocks
    return result


def _inline(text: str) -> str:
    """Apply inline Markdown formatting to a line of text."""
    text = html.escape(text)

    # Stash inline code spans so bold/italic don't mangle their contents
    code_spans: list[str] = []

    def _stash_code(m: re.Match) -> str:
        code_spans.append(f'<span style="{_INLINE_CODE_STYLE}">{m.group(1)}</span>')
        return f"\x01CODE{len(code_spans) - 1}\x01"

    text = re.sub(r"`([^`]+)`", _stash_code, text)

    # Now apply bold/italic/links on the text with code safely stashed
    text = _inline_formatting(text)

    # Restore code spans
    for idx, span_html in enumerate(code_spans):
        text = text.replace(f"\x01CODE{idx}\x01", span_html)

    return text


def _inline_formatting(text: str) -> str:
    """Apply bold, italic, link, hex address, and suspicious API formatting."""
    # Bold: **text** or __text__
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)

    # Italic: *text* or _text_ (but not inside words for underscore)
    text = re.sub(r"(?<!\w)\*(.+?)\*(?!\w)", r"<i>\1</i>", text)
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<i>\1</i>", text)

    # Hex addresses: 0x401000, 0X401000, 401000h, :00401000, sub_401000
    # Convert to clickable links
    def _make_address_link(m: re.Match) -> str:
        addr = m.group(0)
        return f'<a style="color:{_LINK_COLOR}; text-decoration:underline;" href="ida://{addr}">{addr}</a>'

    # Function calls with parentheses: functionName()
    def _make_function_call_link(m: re.Match) -> str:
        func_name = m.group(1)
        return f'<a style="color:#4ec9b0; text-decoration:underline; font-weight:bold;" href="ida://func:{func_name}">{func_name}</a>()'

    # Match function calls like generatePWFOTP(), setDigitalLoginPassword(), ArraysUtil$1.compare@ILL()
    # Support alphanumeric, underscore, $, @, and other common function name characters
    text = re.sub(r"\b([a-zA-Z_][a-zA-Z0-9_$@.]{3,})\(\)", _make_function_call_link, text)

    # Match various hex address formats
    # sub_401000, loc_401000, off_401000, etc. (IDA labels) - do first to avoid partial matches
    text = re.sub(r"\b(?:sub|loc|off|seg|str|byte|word|dword|qword|asc)_[0-9a-fA-F]+\b", _make_address_link, text)
    # 0x401000 or 0X401000
    text = re.sub(r"\b0[xX][0-9a-fA-F]+\b", _make_address_link, text)
    # 401000h or 401000H (assembly style)
    text = re.sub(r"\b[0-9a-fA-F]+h\b", _make_address_link, text)
    # :00401000 (IDA format)
    text = re.sub(r":[0-9a-fA-F]{8}\b", _make_address_link, text)

    # Finding bookmarks: [FINDING:0x401000] or [FINDING:0x401000|custom text]
    # Do this FIRST to avoid conflicts with hex address linking
    def _make_finding_link(m: re.Match) -> str:
        full_match = m.group(0)  # [FINDING:0x401000] or [FINDING:0x401000|text]

        # Extract the part after [FINDING:
        content = full_match[9:]  # Remove "[FINDING:"

        # Split by | if present
        if "|" in content:
            addr_part, custom_text = content.split("|", 1)
            custom_text = custom_text.rstrip("]")
        else:
            addr_part = content.rstrip("]")
            custom_text = None

        # Parse address (remove common hex prefixes to avoid double-linking)
        clean_addr = addr_part.strip()
        # Remove 0x, 0X, : prefix, h suffix
        clean_addr = re.sub(r"^(0[xX]|:)?([0-9a-fA-F]+)h?$", r"\2", clean_addr)

        try:
            address = int(clean_addr, 16)
            display_text = custom_text if custom_text else f"0x{address:X}"
            # Make it clickable like a link
            return f'<a style="color:#ffd93d; text-decoration:underline; font-weight:bold;" href="finding://{address:X}">[FINDING] {display_text}</a>'
        except ValueError:
            # If not a valid hex address, return original
            return full_match

    # Match [FINDING:...] format specifically
    text = re.sub(r"\[FINDING:[^\]]+\]", _make_finding_link, text)

    # Links: [text](url)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        rf'<a style="color:{_LINK_COLOR};" href="\2">\1</a>',
        text,
    )

    # Suspicious API highlighting - do this last to avoid interfering with other formatting
    text = _highlight_suspicious_apis(text)

    return text
