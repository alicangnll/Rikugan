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
    QPushButton,
    QSizePolicy,
    Qt,
    QTimer,
    QToolButton,
    QVBoxLayout,
    QWidget,
    qt_flags,
    QApplication,
    QClipboard,
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
        self._content.setTextInteractionFlags(
            qt_flags(
                Qt.TextInteractionFlag.TextSelectableByMouse,
                Qt.TextInteractionFlag.TextSelectableByKeyboard,
            )
        )
        self._content.setStyleSheet("color: #d4d4d4; font-size: 13px;")
        self._content.setMinimumWidth(0)
        self._content.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
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
# Code block widget with copy button
# ---------------------------------------------------------------------------


class CodeBlockWidget(QFrame):
    """Displays a code block with language label and copy button."""

    def __init__(self, lang: str, code: str, parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("code_block")
        self.setStyleSheet(
            "QFrame#code_block { background: #1a1a1a; border: 1px solid #3c3c3c; border-radius: 4px; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header with language label and copy button
        header = QHBoxLayout()
        header.setContentsMargins(8, 4, 4, 4)

        if lang:
            self._lang_label = QLabel(lang)
            self._lang_label.setStyleSheet("color: #808080; font-size: 10px; font-weight: bold;")
            header.addWidget(self._lang_label)
        else:
            header.addStretch()

        header.addStretch()

        self._copy_btn = QPushButton("Copy")
        self._copy_btn.setStyleSheet(
            "QPushButton { background: #2d4a6e; color: #9cdcfe; border: 1px solid #4a7ab5; "
            "border-radius: 3px; padding: 2px 8px; font-size: 10px; }"
            "QPushButton:hover { background: #3a5a8a; }"
            "QPushButton:pressed { background: #1a3a5e; }"
        )
        self._copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_btn.clicked.connect(lambda: self._copy_to_clipboard(code))
        header.addWidget(self._copy_btn)

        layout.addLayout(header)

        # Code content
        self._code_label = QLabel(code)
        self._code_label.setWordWrap(True)
        self._code_label.setTextInteractionFlags(
            qt_flags(
                Qt.TextInteractionFlag.TextSelectableByMouse,
                Qt.TextInteractionFlag.TextSelectableByKeyboard,
            )
        )
        self._code_label.setStyleSheet(
            "color: #d4d4d4; font-size: 12px; font-family: monospace; "
            "padding: 8px; background: transparent;"
        )
        layout.addWidget(self._code_label)

    def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to clipboard and update button."""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

        self._copy_btn.setText("Copied!")
        self._copy_btn.setStyleSheet(
            "QPushButton { background: #4a6a4a; color: #9cdcfe; border: 1px solid #5a8a5a; "
            "border-radius: 3px; padding: 2px 8px; font-size: 10px; }"
        )

        # Reset button after 2 seconds
        QTimer.singleShot(2000, self._reset_copy_button)

    def _reset_copy_button(self) -> None:
        """Reset copy button to original state."""
        self._copy_btn.setText("Copy")
        self._copy_btn.setStyleSheet(
            "QPushButton { background: #2d4a6e; color: #9cdcfe; border: 1px solid #4a7ab5; "
            "border-radius: 3px; padding: 2px 8px; font-size: 10px; }"
            "QPushButton:hover { background: #3a5a8a; }"
            "QPushButton:pressed { background: #1a3a5e; }"
        )


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

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)

        self._role_label = QLabel("Rikugan")
        self._role_label.setStyleSheet("color: #569cd6; font-weight: bold; font-size: 11px;")
        layout.addWidget(self._role_label)

        self._thinking_block = _ThinkingBlock()
        layout.addWidget(self._thinking_block)

        # Container for mixed content (HTML labels + code block widgets)
        self._content_container = QWidget()
        self._content_layout = QVBoxLayout(self._content_container)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(4)
        self._content_layout.addStretch()
        layout.addWidget(self._content_container)

        # Track current content widgets
        self._content_widgets: list[QWidget] = []

    def _render(self) -> None:
        thinking, visible = _split_thinking(self._full_text)
        if thinking:
            in_progress = "<think>" in self._full_text and "</think>" not in self._full_text
            self._thinking_block.set_thinking(thinking, in_progress=in_progress)
        else:
            self._thinking_block.hide()

        # Parse markdown with code blocks extraction
        html_content, code_blocks = md_to_html(visible, return_code_blocks=True)

        # Clear existing content widgets
        for widget in self._content_widgets:
            widget.deleteLater()
        self._content_widgets.clear()

        # If no code blocks, use simple QLabel
        if not code_blocks:
            label = QLabel()
            label.setWordWrap(True)
            label.setTextFormat(Qt.TextFormat.RichText)
            label.setTextInteractionFlags(
                qt_flags(
                    Qt.TextInteractionFlag.TextSelectableByMouse,
                    Qt.TextInteractionFlag.TextSelectableByKeyboard,
                    Qt.TextInteractionFlag.LinksAccessibleByMouse,
                )
            )
            label.setOpenExternalLinks(True)
            label.setStyleSheet("color: #d4d4d4; font-size: 13px;")
            label.setMinimumWidth(0)
            label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            label.setText(html_content)
            self._content_layout.insertWidget(self._content_layout.count() - 1, label)
            self._content_widgets.append(label)
        else:
            # Split HTML by code block placeholders and create widgets
            parts = html_content.split("\x00BLOCK")
            for i, part in enumerate(parts):
                if not part:
                    continue

                # Check if this part starts with a placeholder (e.g., "0\x00")
                if part[0].isdigit() and "\x00" in part:
                    # Extract the block index
                    end_idx = part.find("\x00")
                    idx_str = part[:end_idx]
                    try:
                        block_idx = int(idx_str)
                        if block_idx < len(code_blocks):
                            lang, code = code_blocks[block_idx]
                            code_widget = CodeBlockWidget(lang, code)
                            self._content_layout.insertWidget(
                                self._content_layout.count() - 1, code_widget
                            )
                            self._content_widgets.append(code_widget)

                            # Process remaining content after the placeholder
                            remaining = part[end_idx + 1:]
                            if remaining.strip():
                                label = QLabel()
                                label.setWordWrap(True)
                                label.setTextFormat(Qt.TextFormat.RichText)
                                label.setTextInteractionFlags(
                                    qt_flags(
                                        Qt.TextInteractionFlag.TextSelectableByMouse,
                                        Qt.TextInteractionFlag.TextSelectableByKeyboard,
                                        Qt.TextInteractionFlag.LinksAccessibleByMouse,
                                    )
                                )
                                label.setOpenExternalLinks(True)
                                label.setStyleSheet("color: #d4d4d4; font-size: 13px;")
                                label.setMinimumWidth(0)
                                label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
                                label.setText(remaining)
                                self._content_layout.insertWidget(
                                    self._content_layout.count() - 1, label
                                )
                                self._content_widgets.append(label)
                    except (ValueError, IndexError):
                        # If parsing fails, treat as regular text
                        if part.strip():
                            label = QLabel()
                            label.setWordWrap(True)
                            label.setTextFormat(Qt.TextFormat.RichText)
                            label.setTextInteractionFlags(
                                qt_flags(
                                    Qt.TextInteractionFlag.TextSelectableByMouse,
                                    Qt.TextInteractionFlag.TextSelectableByKeyboard,
                                    Qt.TextInteractionFlag.LinksAccessibleByMouse,
                                )
                            )
                            label.setOpenExternalLinks(True)
                            label.setStyleSheet("color: #d4d4d4; font-size: 13px;")
                            label.setMinimumWidth(0)
                            label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
                            label.setText(part)
                            self._content_layout.insertWidget(
                                self._content_layout.count() - 1, label
                            )
                            self._content_widgets.append(label)
                else:
                    # Regular HTML content
                    if part.strip():
                        label = QLabel()
                        label.setWordWrap(True)
                        label.setTextFormat(Qt.TextFormat.RichText)
                        label.setTextInteractionFlags(
                            qt_flags(
                                Qt.TextInteractionFlag.TextSelectableByMouse,
                                Qt.TextInteractionFlag.TextSelectableByKeyboard,
                                Qt.TextInteractionFlag.LinksAccessibleByMouse,
                            )
                        )
                        label.setOpenExternalLinks(True)
                        label.setStyleSheet("color: #d4d4d4; font-size: 13px;")
                        label.setMinimumWidth(0)
                        label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
                        label.setText(part)
                        self._content_layout.insertWidget(self._content_layout.count() - 1, label)
                        self._content_widgets.append(label)

        self._pending_delta = 0

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
