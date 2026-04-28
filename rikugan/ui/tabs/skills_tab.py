"""Skills settings tab: enable/disable Rikugan, Claude Code, and Codex skills."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ...core.config import RikuganConfig
from ...core.logging import log_debug
from...skills.loader import SkillDefinition
from ..qt_compat import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextEdit,
    Qt,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from ..settings_service import SettingsService


class SkillsTab(QWidget):
    """Tab for managing skills: Rikugan built-in/user skills + external skills."""

    def __init__(self, config: RikuganConfig, service: SettingsService, parent: QWidget = None):
        super().__init__(parent)
        self._config = config
        self._service = service
        self._rikugan_checks: dict[str, QCheckBox] = {}
        self._external_checks: dict[str, QCheckBox] = {}
        self._skill_details: dict[str, SkillDefinition] = {}  # Store full skill data
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)

        # Skills list on top
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)

        # Rikugan skills (pre-loaded by service)
        rikugan_group = self._build_rikugan_group(self._service.skills.rikugan)
        layout.addWidget(rikugan_group)

        # External skills (pre-loaded by service)
        for source_key, skills in sorted(self._service.skills.external.items()):
            group = self._build_external_group(source_key, skills)
            layout.addWidget(group)

        layout.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll)

        # Skill description text area at bottom
        desc_label = QLabel("Skill Description:")
        desc_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        outer.addWidget(desc_label)

        self._description_text = QTextEdit()
        self._description_text.setReadOnly(True)
        self._description_text.setMaximumHeight(150)
        self._description_text.setPlaceholderText(
            "Click on a skill checkbox above to view its full description here..."
        )
        outer.addWidget(self._description_text)

    def _build_rikugan_group(self, skills: list[SkillDefinition]) -> QGroupBox:
        """Build the Rikugan skills group box."""
        group = QGroupBox("Rikugan Skills")
        layout = QVBoxLayout(group)

        disabled_set = set(self._config.disabled_skills)

        if not skills:
            layout.addWidget(QLabel("No skills found"))
            return group

        # Add "Select All" button row
        button_row = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.setToolTip("Enable all Rikugan skills")
        select_all_btn.clicked.connect(lambda: self._select_all_rikugan_skills(True))
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.setToolTip("Disable all Rikugan skills")
        deselect_all_btn.clicked.connect(lambda: self._select_all_rikugan_skills(False))
        button_row.addWidget(select_all_btn)
        button_row.addWidget(deselect_all_btn)
        button_row.addStretch()
        layout.addLayout(button_row)

        for skill in sorted(skills, key=lambda s: s.slug):
            cb = QCheckBox(f"{skill.slug}  —  {skill.description or '(no description)'}")
            cb.setChecked(skill.slug not in disabled_set)
            # Store skill data for later retrieval
            self._skill_details[skill.slug] = skill
            # Connect state change event to show description
            cb.stateChanged.connect(lambda state, s=skill.slug: self._on_skill_state_changed(s, state))
            self._rikugan_checks[skill.slug] = cb
            layout.addWidget(cb)

        return group

    def _select_all_rikugan_skills(self, checked: bool) -> None:
        """Select or deselect all Rikugan skills."""
        for checkbox in self._rikugan_checks.values():
            checkbox.setChecked(checked)

    def _build_external_group(self, source_key: str, skills: list[SkillDefinition]) -> QGroupBox:
        """Build a group box for external skills from one source."""
        if source_key == "claude":
            title = "Claude Code Skills (~/.claude/skills/)"
        elif source_key == "codex":
            title = "Codex Skills (~/.codex/skills/)"
        else:
            title = f"{source_key} Skills"

        group = QGroupBox(title)
        layout = QVBoxLayout(group)

        if not skills:
            layout.addWidget(QLabel("No skills found"))
            return group

        enabled_set = set(self._config.enabled_external_skills)

        # Add "Select All" button row for this source
        button_row = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.setToolTip(f"Enable all {source_key} skills")
        select_all_btn.clicked.connect(lambda: self._select_all_external_skills(source_key, True))
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.setToolTip(f"Disable all {source_key} skills")
        deselect_all_btn.clicked.connect(lambda: self._select_all_external_skills(source_key, False))
        button_row.addWidget(select_all_btn)
        button_row.addWidget(deselect_all_btn)
        button_row.addStretch()
        layout.addLayout(button_row)

        for skill in sorted(skills, key=lambda s: s.slug):
            ext_id = f"{source_key}:{skill.slug}"
            cb = QCheckBox(f"{skill.slug}  —  {skill.description or '(no description)'}")
            cb.setChecked(ext_id in enabled_set)
            # Store skill data for later retrieval
            self._skill_details[ext_id] = skill
            # Connect state change event to show description
            cb.stateChanged.connect(lambda state, s=ext_id: self._on_skill_state_changed(s, state))
            self._external_checks[ext_id] = cb
            layout.addWidget(cb)

        return group

    def _select_all_external_skills(self, source_key: str, checked: bool) -> None:
        """Select or deselect all external skills from a specific source."""
        for ext_id, checkbox in self._external_checks.items():
            if ext_id.startswith(f"{source_key}:"):
                checkbox.setChecked(checked)

    def _on_skill_state_changed(self, skill_id: str, state) -> None:
        """Handle skill checkbox state change - show skill description in text area when checked."""
        # Only show description when checkbox is checked
        if state != Qt.CheckState.Checked.value:
            return

        skill = self._skill_details.get(skill_id)
        if not skill:
            return

        # Build description text
        desc_lines = []
        desc_lines.append(f"## {skill.name}")
        desc_lines.append(f"**Tags:** {', '.join(skill.tags)}")
        desc_lines.append(f"**Slug:** {skill.slug}")
        desc_lines.append("")
        desc_lines.append(skill.description)
        desc_lines.append("")

        # Try to read skill body if available
        skill_path = getattr(skill, 'path', None)
        if skill_path and Path(skill_path).exists():
            try:
                with open(skill_path, 'r') as f:
                    body = f.read()
                    if body.strip():
                        desc_lines.append("---")
                        desc_lines.append(body)
            except Exception:
                pass

        self._description_text.setText("\n".join(desc_lines))

    def apply_to_config(self, config: RikuganConfig) -> None:
        """Write checkbox state back to config fields."""
        # Disabled Rikugan skills (unchecked = disabled)
        config.disabled_skills = [slug for slug, cb in self._rikugan_checks.items() if not cb.isChecked()]

        # Enabled external skills (checked = enabled)
        config.enabled_external_skills = [ext_id for ext_id, cb in self._external_checks.items() if cb.isChecked()]

        log_debug(
            f"Skills config: {len(config.disabled_skills)} disabled, "
            f"{len(config.enabled_external_skills)} external enabled"
        )
