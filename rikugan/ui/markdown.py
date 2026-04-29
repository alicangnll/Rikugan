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

_MARKDOWN_HINT_RE = re.compile(
    r"(^#{1,4}\s)|(^\s*[-*]\s+)|(^\s*\d+[.)]\s+)|```|`[^`]+`|\*\*|__|(?<!\w)\*(.+?)\*(?!\w)|(?<!\w)_(.+?)_(?!\w)|\[[^\]]+\]\([^)]+\)|^[-*_]{3,}\s*$|^\|.*\|",
    re.MULTILINE,
)

_INLINE_CODE_STYLE = (
    f"background-color:{_CODE_BG}; color:{_CODE_FG}; "
    f"padding:1px 4px; border-radius:3px; font-family:monospace; font-size:12px;"
)

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


def _has_markdown_syntax(text: str) -> bool:
    """Return True when the input likely needs markdown processing."""
    return bool(text and _MARKDOWN_HINT_RE.search(text))


def md_to_html(text: str, return_code_blocks: bool = False) -> str | tuple:
    """Convert a Markdown string to Qt-compatible HTML.

    Args:
        text: Markdown text to convert
        return_code_blocks: If True, returns (html, code_blocks) tuple where
                           code_blocks is a list of (lang, code) tuples.

    Returns:
        HTML string, or (html, code_blocks) tuple if return_code_blocks=True.
    """
    if not text:
        return "" if not return_code_blocks else ("", [])

    if not _has_markdown_syntax(text):
        escaped = html.escape(text).replace("\n", "<br>")
        result = re.sub(r"(<br>\s*){3,}", "<br><br>", escaped)
        return result if not return_code_blocks else (result, [])

    # Phase 1: extract fenced code blocks to protect them from inline processing
    blocks: list[str] = []
    code_blocks: list[tuple[str, str]] = []  # (lang, code) tuples

    def _stash_block(m: re.Match) -> str:
        lang = m.group(1) or ""
        code = m.group(2).strip("\n")

        # Store original code for copy button functionality
        code_blocks.append((lang, code))

        code_escaped = html.escape(code)
        lang_tag = f'<span style="color:#808080;font-size:10px;">{html.escape(lang)}</span><br>' if lang else ""
        block_html = f'<div style="{_BLOCK_CODE_STYLE}">{lang_tag}{code_escaped}</div>'
        blocks.append(block_html)
        return f"\x00BLOCK{len(blocks) - 1}\x00"

    text = re.sub(r"```(\w*)\n(.*?)```", _stash_block, text, flags=re.DOTALL)

    # Phase 2: process line-by-line for block-level elements
    lines = text.split("\n")
    out_lines: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Block placeholder — pass through
        if re.match(r"^\x00BLOCK\d+\x00$", stripped):
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

    # Phase 3: restore code blocks (only if not returning code blocks for widget rendering)
    if not return_code_blocks:
        for idx, block_html in enumerate(blocks):
            result = result.replace(f"\x00BLOCK{idx}\x00", block_html)

    # Clean up double <br> from paragraph joins
    result = re.sub(r"(<br>\s*){3,}", "<br><br>", result)

    if return_code_blocks:
        return result, code_blocks
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
    """Apply bold, italic, and link formatting."""
    # Bold: **text** or __text__
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)

    # Italic: *text* or _text_ (but not inside words for underscore)
    text = re.sub(r"(?<!\w)\*(.+?)\*(?!\w)", r"<i>\1</i>", text)
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<i>\1</i>", text)

    # Links: [text](url)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        rf'<a style="color:{_LINK_COLOR};" href="\2">\1</a>',
        text,
    )

    return text
