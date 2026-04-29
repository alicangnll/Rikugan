"""Message display widgets for the chat view."""

from __future__ import annotations

import random
import re as _re
from typing import ClassVar

from .markdown import md_to_html
from .qt_compat import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    Qt,
    QTimer,
    QToolButton,
    QVBoxLayout,
    QWidget,
    qt_flags,
)

_THINKING_PHRASES = [
    "analyzing binary structure...",
    "examining control flow...",
    "tracing cross-references...",
    "inspecting disassembly...",
    "reading function signatures...",
    "correlating data references...",
    "mapping call graph...",
    "evaluating type patterns...",
    "scanning string references...",
    "deobfuscating logic...",
    "checking import table...",
    "inferring variable types...",
    "analyzing stack layout...",
    "tracing data flow...",
    "examining vtable references...",
    "decoding encoded values...",
]

# Re-export tool widgets so existing consumers that import from this module
# continue to work without changes.

# ---------------------------------------------------------------------------
# Collapsible section (unchanged, used internally)
# ---------------------------------------------------------------------------


class CollapsibleSection(QFrame):
    """A widget with a clickable header that shows/hides content."""

    def __init__(self, title: str, parent: QWidget = None):
        super().__init__(parent)
        self._expanded = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Header
        header = QHBoxLayout()
        self._toggle_btn = QToolButton()
        self._toggle_btn.setObjectName("collapse_button")
        self._toggle_btn.setText("▶")
        self._toggle_btn.setFixedSize(16, 16)
        self._toggle_btn.clicked.connect(self.toggle)

        self._title_label = QLabel(title)
        self._title_label.setObjectName("tool_header")
        header.addWidget(self._toggle_btn)
        header.addWidget(self._title_label, 1)
        layout.addLayout(header)

        # Content area
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(20, 0, 0, 0)
        self._content.setVisible(False)
        layout.addWidget(self._content)

    def toggle(self) -> None:
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        self._toggle_btn.setText("▼" if self._expanded else "▶")

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self._content.setVisible(expanded)
        self._toggle_btn.setText("▼" if expanded else "▶")

    def content_layout(self) -> QVBoxLayout:
        return self._content_layout


# ---------------------------------------------------------------------------
# User message
# ---------------------------------------------------------------------------


class UserMessageWidget(QFrame):
    """Displays a user message."""

    def __init__(self, text: str, parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("message_user")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)

        self._role_label = QLabel("You")
        self._role_label.setStyleSheet("color: #4ec9b0; font-weight: bold; font-size: 11px;")
        layout.addWidget(self._role_label)

        self._content = QLabel(text)
        self._content.setWordWrap(True)
        self._content.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._content.setTextInteractionFlags(
            qt_flags(
                Qt.TextInteractionFlag.TextSelectableByMouse,
                Qt.TextInteractionFlag.TextSelectableByKeyboard,
            )
        )
        self._content.setStyleSheet("""
            color: #d4d4d4;
            font-size: 13px;
        """)
        self._content.setMinimumWidth(100)
        self._content.setMinimumHeight(50)
        self._content.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        layout.addWidget(self._content)


# ---------------------------------------------------------------------------
# Thinking content parser
# ---------------------------------------------------------------------------

_THINK_RE = _re.compile(r"<think>(.*?)</think>", _re.DOTALL)


def _split_thinking(text: str):
    """Split text into (thinking_content, visible_content).

    Handles:
    - One or more complete ``<think>...</think>`` blocks
    - An unclosed ``<think>`` during streaming
    """
    thinking_parts: list = []

    # Extract all complete <think>...</think> blocks
    last_end = 0
    visible_parts: list = []
    for m in _THINK_RE.finditer(text):
        visible_parts.append(text[last_end : m.start()])
        thinking_parts.append(m.group(1).strip())
        last_end = m.end()
    visible_parts.append(text[last_end:])
    remaining = "".join(visible_parts)

    # Check for unclosed <think> (still streaming)
    open_idx = remaining.rfind("<think>")
    if open_idx >= 0:
        partial = remaining[open_idx + 7 :].strip()
        if partial:
            thinking_parts.append(partial)
        remaining = remaining[:open_idx]

    return "\n\n".join(thinking_parts), remaining.strip()


# ---------------------------------------------------------------------------
# Collapsible thinking block
# ---------------------------------------------------------------------------


class _ThinkingBlock(QFrame):
    """Collapsible block for model reasoning / chain-of-thought."""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("thinking_block")
        self.setStyleSheet("#thinking_block { background: #1a1a2e; border: 1px solid #2a2a3e; border-radius: 6px; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(0)

        self._toggle = QToolButton()
        self._toggle.setObjectName("collapse_button")
        self._toggle.setText("\u25b6")  # ▶
        self._toggle.setFixedSize(14, 14)
        self._toggle.clicked.connect(self._on_toggle)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(4)
        header.addWidget(self._toggle)
        self._header_label = QLabel("Thinking")
        self._header_label.setStyleSheet("color: #707090; font-size: 11px; font-style: italic;")
        header.addWidget(self._header_label, 1)
        layout.addLayout(header)

        self._content = QLabel()
        self._content.setWordWrap(True)
        self._content.setTextFormat(Qt.TextFormat.RichText)
        self._content.setTextInteractionFlags(
            qt_flags(
                Qt.TextInteractionFlag.TextSelectableByMouse,
                Qt.TextInteractionFlag.TextSelectableByKeyboard,
            )
        )
        self._content.setStyleSheet("color: #606078; font-size: 12px;")
        self._content.hide()
        layout.addWidget(self._content)

        self._expanded = False
        self.hide()

    def _on_toggle(self) -> None:
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        self._toggle.setText("\u25bc" if self._expanded else "\u25b6")

    def set_thinking(self, text: str, in_progress: bool = False) -> None:
        self._content.setText(md_to_html(text))
        label = "Thinking\u2026" if in_progress else "Thinking"
        self._header_label.setText(label)
        self.show()


# ---------------------------------------------------------------------------
# Assistant message (with streaming + Markdown)
# ---------------------------------------------------------------------------


class AssistantMessageWidget(QFrame):
    """Displays an assistant message with streaming support and Markdown rendering."""

    # Larger batch = fewer re-layouts during streaming = less shaking.
    _RENDER_BATCH = 120

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("message_assistant")
        self._full_text = ""
        self._pending_delta = 0
        self._code_blocks = []  # Store extracted code blocks for copying

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)

        self._role_label = QLabel("Rikugan")
        self._role_label.setStyleSheet("color: #569cd6; font-weight: bold; font-size: 11px;")
        layout.addWidget(self._role_label)

        self._thinking_block = _ThinkingBlock()
        layout.addWidget(self._thinking_block)

        self._content = QLabel()
        self._content.setWordWrap(True)
        self._content.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._content.setTextFormat(Qt.TextFormat.RichText)
        self._content.setTextInteractionFlags(
            qt_flags(
                Qt.TextInteractionFlag.TextSelectableByMouse,
                Qt.TextInteractionFlag.TextSelectableByKeyboard,
                Qt.TextInteractionFlag.LinksAccessibleByMouse,
            )
        )
        self._content.setOpenExternalLinks(True)
        self._content.setStyleSheet("color: #d4d4d4; font-size: 13px;")
        # Enable context menu for copy functionality
        self._content.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._content.customContextMenuRequested.connect(self._show_context_menu)
        # Enable mouse tracking for double-click to copy
        self._content.setMouseTracking(True)
        self._content.mouseDoubleClickEvent = self._on_double_click
        # Allow proper sizing for tables and long content
        self._content.setMinimumWidth(100)
        self._content.setMinimumHeight(50)
        self._content.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        layout.addWidget(self._content)

    def _render(self) -> None:
        thinking, visible = _split_thinking(self._full_text)
        if thinking:
            in_progress = "<think>" in self._full_text and "</think>" not in self._full_text
            self._thinking_block.set_thinking(thinking, in_progress=in_progress)
        else:
            self._thinking_block.hide()
        # Extract code blocks before rendering
        self._extract_code_blocks(visible)
        # Use setHtml for proper HTML rendering instead of setText
        self._content.setHtml(md_to_html(visible))
        self._pending_delta = 0

    def _extract_code_blocks(self, text: str) -> None:
        """Extract code blocks from markdown text for copying."""
        import re
        self._code_blocks = []
        # Match fenced code blocks: ```lang ... ```
        pattern = r'```(\w*)\n(.*?)```'
        for match in re.finditer(pattern, text, re.DOTALL):
            lang = match.group(1) or ""
            code = match.group(2).strip()
            self._code_blocks.append({'language': lang, 'code': code})

    def copy_last_code_block(self) -> bool:
        """Copy the last code block to clipboard.

        Returns:
            True if successful, False otherwise
        """
        if not self._code_blocks:
            return False

        try:
            from .copy_utils import add_copy_to_clipboard
            import html

            last_block = self._code_blocks[-1]
            raw_code = last_block['code']

            # If raw_code contains HTML entities, decode them
            if '&lt;' in raw_code or '&gt;' in raw_code or '&amp;' in raw_code:
                try:
                    raw_code = html.unescape(raw_code)
                except:
                    pass  # If decoding fails, use as-is

            add_copy_to_clipboard(raw_code)
            print(f"Copied code block ({len(raw_code)} chars)")
            return True
        except Exception as e:
            print(f"Failed to copy code block: {e}")
            import traceback
            traceback.print_exc()
            return False

    def copy_all_code_blocks(self) -> bool:
        """Copy all code blocks to clipboard, separated by newlines.

        Returns:
            True if successful, False otherwise
        """
        if not self._code_blocks:
            return False

        try:
            from .copy_utils import add_copy_to_clipboard
            import html

            # Collect and decode all code blocks
            decoded_blocks = []
            for block in self._code_blocks:
                code = block['code']
                # If code contains HTML entities, decode them
                if '&lt;' in code or '&gt;' in code or '&amp;' in code:
                    try:
                        code = html.unescape(code)
                    except:
                        pass  # If decoding fails, use as-is
                decoded_blocks.append(code)

            all_code = '\n\n'.join(decoded_blocks)
            add_copy_to_clipboard(all_code)
            print(f"Copied {len(self._code_blocks)} code blocks ({len(all_code)} chars)")
            return True
        except Exception as e:
            print(f"Failed to copy code blocks: {e}")
            import traceback
            traceback.print_exc()
            return False

    def has_code_blocks(self) -> bool:
        """Check if this message contains any code blocks."""
        return len(self._code_blocks) > 0

    def _on_double_click(self, event) -> None:
        """Handle double-click to copy code blocks."""
        if self._code_blocks:
            if self.copy_last_code_block():
                self._show_copy_feedback()
                print("Code copied (double-click)")
        # Call original event handler
        QLabel.mouseDoubleClickEvent(self._content, event)

    def _show_context_menu(self, pos) -> None:
        """Show context menu with copy options."""
        import sys

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d2d;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
            }
            QMenu::item {
                padding: 6px 24px;
            }
            QMenu::item:selected {
                background-color: #3c3c3c;
            }
        """)

        if self._code_blocks:
            # Add copy options for code blocks
            if len(self._code_blocks) == 1:
                action = menu.addAction("Copy Code")
                # Use lambda to avoid immediate execution
                action.triggered.connect(lambda checked=False: self._safe_copy_last())
            else:
                action_last = menu.addAction("Copy Last Code Block")
                action_last.triggered.connect(lambda checked=False: self._safe_copy_last())

                action_all = menu.addAction("Copy All Code Blocks")
                action_all.triggered.connect(lambda checked=False: self._safe_copy_all())

            menu.addSeparator()

        # Add standard copy action
        menu.addAction("Copy Selection")
        menu.setActiveAction(menu.actions()[-1])

        menu.exec_(self._content.mapToGlobal(pos))

    def _safe_copy_last(self) -> None:
        """Safely copy last code block with error handling."""
        try:
            if self.copy_last_code_block():
                self._show_copy_feedback()
        except Exception as e:
            print(f"Error in copy_last_code_block: {e}")

    def _safe_copy_all(self) -> None:
        """Safely copy all code blocks with error handling."""
        try:
            if self.copy_all_code_blocks():
                self._show_copy_feedback()
        except Exception as e:
            print(f"Error in copy_all_code_blocks: {e}")

    def keyPressEvent(self, event) -> None:
        """Handle keyboard shortcuts for copying code blocks."""
        # Ctrl+Shift+C to copy the last code block
        if (event.key() == Qt.Key.Key_C and
            event.modifiers() & Qt.KeyboardModifier.ControlModifier and
            event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            if self.copy_last_code_block():
                # Show brief feedback
                self._show_copy_feedback()
                return
        # Let parent handle other keys
        super().keyPressEvent(event)

    def _show_copy_feedback(self) -> None:
        """Show brief visual feedback when code is copied."""
        original_style = self._content.styleSheet()
        self._content.setStyleSheet(original_style + " background-color: rgba(80, 200, 120, 0.1);")
        # Reset after 300ms
        QTimer.singleShot(300, lambda: self._content.setStyleSheet(original_style))

    def append_text(self, delta: str) -> None:
        self._full_text += delta
        self._pending_delta += len(delta)
        if self._pending_delta >= self._RENDER_BATCH:
            self._render()

    def set_text(self, text: str) -> None:
        self._full_text = text
        self._render()

    def full_text(self) -> str:
        return self._full_text


# ---------------------------------------------------------------------------
# Thinking indicator
# ---------------------------------------------------------------------------


class ThinkingWidget(QFrame):
    """Animated thinking indicator shown while the LLM is processing."""

    _STAR_FRAMES: ClassVar[list[str]] = ["✳", "✴", "✵", "✶"]

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("message_thinking")
        self._phrase_idx = random.randint(0, len(_THINKING_PHRASES) - 1)
        self._star_idx = 0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self._star_label = QLabel(self._STAR_FRAMES[0])
        self._star_label.setStyleSheet("color: #dcdcaa; font-size: 14px;")
        self._star_label.setFixedWidth(18)
        layout.addWidget(self._star_label)

        self._phrase_label = QLabel(_THINKING_PHRASES[self._phrase_idx])
        self._phrase_label.setStyleSheet("color: #808080; font-style: italic; font-size: 12px;")
        layout.addWidget(self._phrase_label, 1)

        self._stopped = False

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(900)

    def _tick(self) -> None:
        if self._stopped:
            return
        self._star_idx = (self._star_idx + 1) % len(self._STAR_FRAMES)
        self._star_label.setText(self._STAR_FRAMES[self._star_idx])

        if self._star_idx == 0:
            self._phrase_idx = (self._phrase_idx + 1) % len(_THINKING_PHRASES)
            self._phrase_label.setText(_THINKING_PHRASES[self._phrase_idx])

    def stop(self) -> None:
        self._stopped = True
        try:
            self._timer.stop()
            self._timer.timeout.disconnect(self._tick)
        except (RuntimeError, TypeError):
            return  # timer already stopped or signal already disconnected — harmless


# ---------------------------------------------------------------------------
# Other message widgets
# ---------------------------------------------------------------------------


class QueuedMessageWidget(QFrame):
    """Displays a queued user message with dashed border."""

    def __init__(self, text: str, parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("message_queued")
        self.setStyleSheet(
            "QFrame#message_queued { border: 1px dashed #007acc; border-radius: 6px; background: #1e1e2e; }"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)

        content_layout = QVBoxLayout()

        self._role_label = QLabel("You")
        self._role_label.setStyleSheet("color: #4ec9b0; font-weight: bold; font-size: 11px;")
        content_layout.addWidget(self._role_label)

        self._content = QLabel(text)
        self._content.setWordWrap(True)
        self._content.setTextInteractionFlags(
            qt_flags(
                Qt.TextInteractionFlag.TextSelectableByMouse,
                Qt.TextInteractionFlag.TextSelectableByKeyboard,
            )
        )
        self._content.setStyleSheet("color: #d4d4d4; font-size: 13px;")
        content_layout.addWidget(self._content)

        layout.addLayout(content_layout, 1)

        self._badge = QLabel("[queued]")
        self._badge.setStyleSheet("color: #808080; font-size: 10px; font-style: italic;")
        self._badge.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self._badge)


class UserQuestionWidget(QFrame):
    """Displays a question from the agent to the user with clickable option buttons."""

    def __init__(self, question: str, options: list | None = None, parent: QWidget = None):
        super().__init__(parent)
        self._option_selected_callback = None
        self.setObjectName("message_question")
        self.setStyleSheet(
            "QFrame#message_question { border: 1px solid #dcdcaa; border-radius: 6px; background: #2d2d1e; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        self._header = QLabel("Rikugan asks:")
        self._header.setStyleSheet("color: #dcdcaa; font-weight: bold; font-size: 11px;")
        layout.addWidget(self._header)

        self._q_label = QLabel(question)
        self._q_label.setWordWrap(True)
        self._q_label.setTextInteractionFlags(
            qt_flags(
                Qt.TextInteractionFlag.TextSelectableByMouse,
                Qt.TextInteractionFlag.TextSelectableByKeyboard,
            )
        )
        self._q_label.setStyleSheet("color: #d4d4d4; font-size: 13px;")
        layout.addWidget(self._q_label)

        if options:
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(0, 4, 0, 0)
            btn_layout.setSpacing(8)
            for opt in options:
                btn = QPushButton(opt)
                btn.setStyleSheet(
                    "QPushButton { background: #2d4a6e; color: #9cdcfe; border: 1px solid #4a7ab5; "
                    "border-radius: 4px; padding: 4px 14px; font-size: 12px; }"
                    "QPushButton:hover { background: #3a5a8a; }"
                    "QPushButton:pressed { background: #1a3a5e; }"
                    "QPushButton:disabled { color: #808080; background: #1e2a3a; border-color: #444; }"
                )
                btn.clicked.connect(lambda checked, o=opt: self._on_option(o))
                btn_layout.addWidget(btn)
            btn_layout.addStretch()
            layout.addLayout(btn_layout)
            self._buttons = btn_layout

    def set_option_selected_callback(self, callback) -> None:
        self._option_selected_callback = callback

    def _on_option(self, option: str) -> None:
        # Disable all buttons after selection
        for i in range(self._buttons.count()):
            item = self._buttons.itemAt(i)
            if item and item.widget():
                item.widget().setEnabled(False)
        if self._option_selected_callback is not None:
            self._option_selected_callback(option)


class ExplorationPhaseWidget(QFrame):
    """Displays an exploration phase transition."""

    _PHASE_ICONS: ClassVar[dict[str, str]] = {
        "explore": "\u25b6",  # play
        "plan": "\u270e",  # pencil
        "execute": "\u2699",  # gear
        "save": "\u2714",  # checkmark
    }

    def __init__(self, from_phase: str, to_phase: str, reason: str = "", parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("message_tool")
        self.setStyleSheet("QFrame#message_tool { border-color: #d7ba7d; background: #2d2a1f; }")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        icon = self._PHASE_ICONS.get(to_phase, "\u2192")
        self._phase_label = QLabel(f"{icon}  Phase: {to_phase.upper()}")
        self._phase_label.setStyleSheet("color: #d7ba7d; font-weight: bold; font-size: 11px;")
        layout.addWidget(self._phase_label)

        if reason:
            self._reason_label = QLabel(reason)
            self._reason_label.setWordWrap(True)
            self._reason_label.setStyleSheet("color: #b0a070; font-size: 11px;")
            layout.addWidget(self._reason_label, 1)


class ExplorationFindingWidget(QFrame):
    """Displays a single exploration finding."""

    _CATEGORY_COLORS: ClassVar[dict[str, str]] = {
        "function_purpose": "#4ec9b0",
        "hypothesis": "#d7ba7d",
        "constant": "#b5cea8",
        "data_structure": "#c586c0",
        "string_ref": "#ce9178",
        "import_usage": "#569cd6",
        "patch_result": "#6a9955",
        "general": "#808080",
    }

    def __init__(
        self,
        category: str,
        summary: str,
        address: str | None = None,
        relevance: str = "medium",
        parent: QWidget = None,
    ):
        super().__init__(parent)
        self.setObjectName("message_tool")
        color = self._CATEGORY_COLORS.get(category, "#808080")
        self.setStyleSheet(f"QFrame#message_tool {{ border-color: {color}; }}")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self._cat_label = QLabel(f"[{category}]")
        self._cat_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 10px;")
        layout.addWidget(self._cat_label)

        if address:
            self._addr_label = QLabel(address)
            self._addr_label.setStyleSheet("color: #808080; font-family: monospace; font-size: 10px;")
            layout.addWidget(self._addr_label)

        self._summary_label = QLabel(summary)
        self._summary_label.setWordWrap(True)
        self._summary_label.setStyleSheet("color: #d4d4d4; font-size: 11px;")
        layout.addWidget(self._summary_label, 1)

        if relevance == "high":
            rel_label = QLabel("\u2605")
            rel_label.setStyleSheet("color: #d7ba7d; font-size: 12px;")
            rel_label.setToolTip("High relevance")
            layout.addWidget(rel_label)


class ResearchNoteWidget(QFrame):
    """Displays a research note saved event."""

    def __init__(
        self,
        title: str,
        genre: str,
        path: str,
        preview: str = "",
        review_passed: bool = True,
        parent: QWidget = None,
    ):
        super().__init__(parent)
        self.setObjectName("message_tool")
        accent = "#6a9955" if review_passed else "#d7ba7d"
        self.setStyleSheet(f"QFrame#message_tool {{ border-color: {accent}; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        # Header row
        header = QHBoxLayout()
        icon = "\u2705" if review_passed else "\u270f"  # checkmark or pencil
        self._title_label = QLabel(f"{icon}  {title}")
        self._title_label.setStyleSheet(f"color: {accent}; font-weight: bold; font-size: 11px;")
        header.addWidget(self._title_label)

        self._genre_label = QLabel(f"#{genre}")
        self._genre_label.setStyleSheet("color: #808080; font-size: 10px; font-style: italic;")
        header.addWidget(self._genre_label)
        header.addStretch()
        layout.addLayout(header)

        # Path
        self._path_label = QLabel(path)
        self._path_label.setStyleSheet("color: #606060; font-family: monospace; font-size: 10px;")
        layout.addWidget(self._path_label)

        # Preview
        if preview:
            self._preview_label = QLabel(preview)
            self._preview_label.setWordWrap(True)
            self._preview_label.setStyleSheet("color: #a0a0a0; font-size: 11px;")
            layout.addWidget(self._preview_label)


class SubagentEventWidget(QFrame):
    """Displays a subagent lifecycle event (spawned, completed, failed)."""

    _STATUS_COLORS: ClassVar[dict[str, str]] = {
        "spawned": "#569cd6",
        "completed": "#4ec9b0",
        "failed": "#f44747",
    }

    def __init__(
        self,
        status: str,
        name: str,
        detail: str = "",
        parent: QWidget = None,
    ):
        super().__init__(parent)
        self.setObjectName("message_tool")
        color = self._STATUS_COLORS.get(status, "#808080")
        self.setStyleSheet(f"QFrame#message_tool {{ border-color: {color}; background: #252530; }}")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        icon_map = {"spawned": "\u25b6", "completed": "\u2714", "failed": "\u2718"}
        icon = icon_map.get(status, "\u2022")
        self._icon = QLabel(icon)
        self._icon.setStyleSheet(f"color: {color}; font-size: 14px;")
        layout.addWidget(self._icon)

        label_text = f"Subagent \u201c{name}\u201d {status}"
        self._label = QLabel(label_text)
        self._label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 11px;")
        layout.addWidget(self._label)

        if detail:
            self._detail = QLabel(detail)
            self._detail.setWordWrap(True)
            self._detail.setStyleSheet("color: #b0b0b0; font-size: 11px;")
            layout.addWidget(self._detail, 1)


class ErrorMessageWidget(QFrame):
    """Displays an error message."""

    def __init__(self, error_text: str, parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("message_tool")
        self.setStyleSheet("QFrame#message_tool { border-color: #f44747; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)

        self._header = QLabel("Error")
        self._header.setStyleSheet("color: #f44747; font-weight: bold; font-size: 11px;")
        layout.addWidget(self._header)

        self._content = QLabel(error_text)
        self._content.setWordWrap(True)
        self._content.setTextInteractionFlags(
            qt_flags(
                Qt.TextInteractionFlag.TextSelectableByMouse,
                Qt.TextInteractionFlag.TextSelectableByKeyboard,
            )
        )
        self._content.setStyleSheet("color: #f44747; font-size: 12px;")
        self._content.setMinimumWidth(0)
        self._content.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout.addWidget(self._content)
