"""Lightweight Markdown to HTML converter for QLabel rich text.

Handles the subset of Markdown that LLMs commonly produce:
- Fenced code blocks (```lang ... ```)
- Inline code (`code`)
- Bold (**text**), italic (*text*)
- Headers (# through ####)
- Bullet lists (- item, * item)
- Numbered lists (1. item)
- Links [text](url)
- Tables (| Header | Header |)
- Paragraphs (double newline)
- Horizontal rules (---, ***)

No external dependencies. Output targets Qt's supported HTML subset.
"""

from __future__ import annotations

import html
import re
import uuid

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
    r"(^#{1,4}\s)|(^\s*[-*]\s+)|(^\s*\d+[.)]\s+)|```|`[^`]+`|\*\*|__|(?<!\w)\*(.+?)\*(?!\w)|(?<!\w)_(.+?)_(?!\w)|\[[^\]]+\]\([^)]+\)|^[-*_]{3,}\s*$|^\|.+?\|",
    re.MULTILINE,
)

_INLINE_CODE_STYLE = (
    f"background-color:{_CODE_BG}; color:{_CODE_FG}; "
    f"padding:1px 4px; border-radius:3px; font-family:monospace; font-size:12px; "
    f"cursor:pointer; transition:all 0.2s;"  # Add cursor and transition
)

_BLOCK_CODE_STYLE = (
    f"background-color:{_BLOCK_BG}; color:{_BLOCK_FG}; "
    f"border:1px solid {_CODE_BORDER}; border-radius:4px; "
    f"padding:8px; font-family:monospace; font-size:12px; "
    f"white-space:pre-wrap; word-break:break-all;"
    f"position:relative;"  # Add relative positioning for copy button
)

_TABLE_STYLE = (
    f"border:1px solid {_CODE_BORDER}; border-collapse:collapse; "
    f"margin:12px 0; width:100%; max-width:100%; "
    f"background-color:{_BLOCK_BG};"
)

_TABLE_TH_STYLE = (
    f"background-color:#252526; color:{_H_COLOR}; "
    f"border:1px solid {_CODE_BORDER}; padding:10px 14px; "
    f"text-align:left; font-weight:bold; font-size:13px;"
)

_TABLE_TD_STYLE = (
    f"border:1px solid {_CODE_BORDER}; padding:8px 14px; "
    f"color:{_BLOCK_FG}; font-size:13px;"
)

_TABLE_ROW_EVEN_STYLE = "background-color:#1e1e1e;"
_TABLE_ROW_ODD_STYLE = "background-color:#252526;"


def _has_markdown_syntax(text: str) -> bool:
    """Return True when the input likely needs markdown processing."""
    return bool(text and _MARKDOWN_HINT_RE.search(text))


def _parse_table_row(row: str, is_header: bool = False, row_num: int = 0) -> str:
    """Parse a single table row and return HTML."""
    # Remove leading/trailing pipes and split
    cells = [cell.strip() for cell in row.strip().split('|')]
    # Remove empty cells from leading/trailing pipes
    cells = [cell for cell in cells if cell or not (cells.index(cell) == 0 or cells.index(cell) == len(cells) - 1)]

    tag = "th" if is_header else "td"
    style = _TABLE_TH_STYLE if is_header else _TABLE_TD_STYLE

    # Add alternating row colors for data rows
    row_style = ""
    if not is_header:
        row_style = _TABLE_ROW_EVEN_STYLE if row_num % 2 == 0 else _TABLE_ROW_ODD_STYLE

    cells_html = []
    for cell in cells:
        # Apply inline formatting to cell content
        formatted_cell = _inline(cell)
        cells_html.append(f"<{tag} style=\"{style}\">{formatted_cell}</{tag}>")

    if row_style:
        return "<tr style=\"" + row_style + "\">" + "".join(cells_html) + "</tr>"
    return "<tr>" + "".join(cells_html) + "</tr>"


def _extract_table(text: str, start_idx: int) -> tuple[str, int]:
    """Extract a complete table from text starting at start_idx.

    Returns:
        (table_html, new_index) - HTML table and index after the table
    """
    lines = text.split('\n')
    table_lines = []
    i = start_idx

    # Collect all consecutive table lines
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('|') and line.endswith('|'):
            table_lines.append(line)
            i += 1
        elif line.startswith('|') and '| --- ' in line.replace(' ', ''):
            # Separator line
            table_lines.append(line)
            i += 1
        else:
            break

    if not table_lines:
        return "", start_idx

    # Parse the table
    # First line is header
    header_row = _parse_table_row(table_lines[0], is_header=True)

    # Skip separator line (second line)
    tbody_rows = []
    row_num = 0
    for line in table_lines[2:]:
        if line and '|' in line:
            tbody_rows.append(_parse_table_row(line, is_header=False, row_num=row_num))
            row_num += 1

    table_html = f"<table style=\"{_TABLE_STYLE}\"><thead>{header_row}</thead><tbody>{''.join(tbody_rows)}</tbody></table>"

    return table_html, i


def md_to_html(text: str) -> str:
    """Convert a Markdown string to Qt-compatible HTML."""
    if not text:
        return ""
    if not _has_markdown_syntax(text):
        escaped = html.escape(text).replace("\n", "<br>")
        return re.sub(r"(<br>\s*){3,}", "<br><br>", escaped)

    # Phase 1: extract fenced code blocks to protect them from inline processing
    blocks: list[str] = []

    def _stash_block(m: re.Match) -> str:
        lang = m.group(1) or ""
        raw_code = m.group(2).strip("\n")
        code = html.escape(raw_code)

        # Generate unique ID for this code block
        block_id = f"code_{uuid.uuid4().hex[:8]}"

        # Create copy button HTML
        copy_btn = f'''
        <button
            onclick="RikuganCopyBlock('{block_id}')"
            style="
                position: absolute;
                top: 6px;
                right: 6px;
                background: rgba(86, 156, 214, 0.2);
                border: 1px solid rgba(86, 156, 214, 0.4);
                color: #569cd6;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 11px;
                font-family: sans-serif;
                cursor: pointer;
                opacity: 0;
                transition: opacity 0.2s;
                z-index: 10;
            "
            onmouseover="this.style.opacity='1'"
            onmouseout="this.style.opacity='0'"
            data-block-id="{block_id}"
        >Copy</button>
        '''

        # Add hover effect to the container
        container_style = _BLOCK_CODE_STYLE + "; cursor: pointer;"
        container_style += " transition: box-shadow 0.2s;"
        container_style += " margin: 12px 0;"

        lang_tag = f'<span style="color:#808080;font-size:10px;">{html.escape(lang)}</span><br>' if lang else ""
        block_html = f'<div id="{block_id}" style="{container_style}" onmouseover="this.style.boxShadow=&apos;0 4px 12px rgba(86,156,214,0.15)&apos;">{copy_btn}{lang_tag}{code}</div>'

        # Store raw code for copying
        blocks.append(block_html)
        blocks.append(f"__RAW_CODE_{block_id}:{raw_code}__")

        return f"\x00BLOCK{len(blocks) // 2}\x00"

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

        # Tables — detect and extract complete tables
        if stripped.startswith('|') and stripped.endswith('|') and '|' in stripped[1:-1]:
            # This looks like a table row, check if next line is separator
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line.startswith('|') and re.search(r'^\|?\s*:?-+:?\s*\|(\s*:?-+:?\s*\|)*\s*:?-+:?\s*\|?$', next_line):
                    # This is a table! Extract it
                    full_text = "\n".join(lines)
                    table_html, new_i = _extract_table(full_text, i)
                    if table_html:
                        out_lines.append(table_html)
                        i = new_i
                        continue
            # If not a valid table, treat as regular text
            out_lines.append(_inline(stripped))
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

    # Phase 3: restore code blocks (only even indices are HTML, odd are raw markers)
    for idx in range(0, len(blocks), 2):
        if idx < len(blocks):
            block_html = blocks[idx]
            block_num = idx // 2
            result = result.replace(f"\x00BLOCK{block_num}\x00", block_html)

    # Clean up double <br> from paragraph joins
    result = re.sub(r"(<br>\s*){3,}", "<br><br>", result)

    return result


def _inline(text: str) -> str:
    """Apply inline Markdown formatting to a line of text."""
    text = html.escape(text)

    # Stash inline code spans so bold/italic don't mangle their contents
    code_spans: list[str] = []

    def _stash_code(m: re.Match) -> str:
        code_id = f"inline_{uuid.uuid4().hex[:8]}"
        raw_code = m.group(1)
        code_spans.append(f'<span id="{code_id}" style="{_INLINE_CODE_STYLE}" onclick="RikuganCopyInline(\'{code_id}\')">{raw_code}</span>')
        return f"\x01CODE{len(code_spans) - 1}\x01"

    text = re.sub(r"`([^`]+)`", _stash_code, text)

    # Now apply bold/italic/links on the text with code safely stashed
    text = _inline_formatting(text)

    # Restore code spans
    for idx, span_html in enumerate(code_spans):
        text = text.replace(f"\x01CODE{idx}\x01", span_html)

    return text


def _inline_formatting(text: str) -> str:
    """Apply bold, italic, link, and badge formatting."""
    # Severity badges: 🔴 CRITICAL, 🟠 HIGH, 🟡 MEDIUM, 🟢 LOW
    text = re.sub(
        r"🔴\s*(CRITICAL|Critical)",
        r'<span style="background-color:#5a1e1e; color:#f44747; padding:2px 8px; border-radius:3px; font-weight:bold; font-size:11px;">\1</span>',
        text
    )
    text = re.sub(
        r"🟠\s*(HIGH|High)",
        r'<span style="background-color:#5a3a1e; color:#ff9800; padding:2px 8px; border-radius:3px; font-weight:bold; font-size:11px;">\1</span>',
        text
    )
    text = re.sub(
        r"🟡\s*(MEDIUM|Medium)",
        r'<span style="background-color:#5a4a1e; color:#ffc107; padding:2px 8px; border-radius:3px; font-weight:bold; font-size:11px;">\1</span>',
        text
    )
    text = re.sub(
        r"🟢\s*(LOW|Low)",
        r'<span style="background-color:#1e3a2e; color:#4caf50; padding:2px 8px; border-radius:3px; font-weight:bold; font-size:11px;">\1</span>',
        text
    )

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


# ═══════════════════════════════════════════════════
# COPY FUNCTIONALITY FOR IDA PRO UI
# ═══════════════════════════════════════════════════

def generate_copy_script() -> str:
    """Generate JavaScript for copy functionality."""
    return '''
<script>
(function() {
    // Store raw code for copying
    window.rikuganCodeStore = {};

    // Copy block code function
    window.RikuganCopyBlock = function(blockId) {
        const element = document.getElementById(blockId);
        if (!element) return;

        // Find stored raw code
        const rawCodeKey = `__RAW_CODE_${blockId}__`;
        const code = window.rikuganCodeStore[rawCodeKey] || element.textContent;

        // Copy to clipboard
        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(code).then(() => {
                showSuccess(blockId);
            }).catch(err => {
                fallbackCopy(code, blockId);
            });
        } else {
            fallbackCopy(code, blockId);
        }
    };

    // Copy inline code function
    window.RikuganCopyInline = function(codeId) {
        const element = document.getElementById(codeId);
        if (!element) return;

        const code = element.textContent;

        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(code).then(() => {
                // Visual feedback
                const originalStyle = element.getAttribute('style');
                element.style.background = 'rgba(80, 200, 120, 0.3)';
                element.style.borderColor = '#50c878';

                setTimeout(() => {
                    element.setAttribute('style', originalStyle);
                }, 500);
            }).catch(err => {
                console.error('Failed to copy:', err);
            });
        } else {
            // Fallback
            const textArea = document.createElement('textarea');
            textArea.value = code;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
        }

        // Prevent event propagation
        event.stopPropagation();
        event.preventDefault();
    };

    // Fallback copy method
    function fallbackCopy(text, elementId) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        document.body.appendChild(textArea);
        textArea.select();

        try {
            const successful = document.execCommand('copy');
            if (successful) {
                showSuccess(elementId);
            }
        } catch (err) {
            console.error('Fallback copy failed:', err);
        } finally {
            document.body.removeChild(textArea);
        }
    }

    // Show success state
    function showSuccess(elementId) {
        const button = document.querySelector(`[data-block-id="${elementId}"]`);
        if (button) {
            button.innerHTML = '✓';
            button.style.background = 'rgba(80, 200, 120, 0.3)';
            button.style.borderColor = '#50c878';

            setTimeout(() => {
                button.innerHTML = '📋';
                button.style.background = '';
                button.style.borderColor = '';
            }, 1500);
        }
    }

    // Initialize code store from page content
    document.addEventListener('DOMContentLoaded', function() {
        // Scan for raw code markers
        const bodyText = document.body.innerHTML;
        const codeRegex = /__RAW_CODE_([^_]+)__:([^<]+)__/g;
        let match;

        while ((match = codeRegex.exec(bodyText)) !== null) {
            const blockId = match[1];
            const rawCode = match[2];
            // Decode HTML entities
            const textarea = document.createElement('textarea');
            textarea.innerHTML = rawCode;
            window.rikuganCodeStore[blockId] = textarea.value;
        }

        // Clean up markers from DOM
        document.body.innerHTML = document.body.innerHTML.replace(/__RAW_CODE_[^_]+__:([^<]+)__/g, '');

        console.log('Rikugan copy functionality initialized');
    });
})();
</script>
'''


def get_copy_script() -> str:
    """Get the copy script (can be called externally)."""
    return generate_copy_script()


# Export for use in other modules
__all__ = ['md_to_html', 'get_copy_script', 'generate_copy_script']
