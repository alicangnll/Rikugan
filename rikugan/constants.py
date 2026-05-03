"""Global constants for Rikugan.

This module is data-only — no runtime detection or host probing.
For host capability flags see ``rikugan.core.host``.
"""

from __future__ import annotations
import json
from pathlib import Path

# Get the directory of this file
_RIKUGAN_ROOT = Path(__file__).parent.parent

# Read version from update.json
try:
    with open(_RIKUGAN_ROOT / "update.json", "r") as f:
        _update_info = json.load(f)
        PLUGIN_VERSION = _update_info["version"]
except (FileNotFoundError, KeyError, json.JSONDecodeError):
    PLUGIN_VERSION = "1.2.5"  # Fallback version

PLUGIN_NAME = "Rikugan-Fork"
PLUGIN_HOTKEY = "Ctrl+Shift+I"
PLUGIN_COMMENT = "Intelligent Reverse-engineering Integrated System"

CONFIG_DIR_NAME = "rikugan"
CONFIG_FILE_NAME = "config.json"
CHECKPOINTS_DIR_NAME = "checkpoints"

DEFAULT_MAX_TOKENS = 16384
DEFAULT_TEMPERATURE = 0.2
DEFAULT_CONTEXT_WINDOW = 200000

TOOL_RESULT_TRUNCATE_LEN = 8000

SYSTEM_PROMPT_VERSION = 1
CONFIG_SCHEMA_VERSION = 2
SESSION_SCHEMA_VERSION = 1

SKILLS_DIR_NAME = "skills"
MCP_CONFIG_FILE = "mcp.json"
MCP_TOOL_PREFIX = "mcp_"
MCP_DEFAULT_TIMEOUT = 30.0
