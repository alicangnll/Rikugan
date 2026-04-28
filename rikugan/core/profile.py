"""Analysis profiles: control what data reaches the LLM provider."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .logging import log_debug

# ---------------------------------------------------------------------------
# IOC filter categories — keys used in AnalysisProfile.ioc_filters
# ---------------------------------------------------------------------------

IOC_FILTER_CATEGORIES: dict[str, str] = {
    "hashes": "File hashes (MD5, SHA1, SHA256)",
    "ipv4": "IPv4 addresses",
    "ipv6": "IPv6 addresses",
    "domains": "Domain names",
    "urls": "URLs (http/https/ftp)",
    "registry_keys": "Windows registry keys",
    "file_paths": "File paths (Windows & Unix)",
    "emails": "Email addresses",
    "crypto_wallets": "Cryptocurrency wallet addresses",
    "mutexes": "Mutex / named object names",
}


@dataclass
class AnalysisProfile:
    """A named analysis profile that controls data filtering and tool access."""

    name: str
    description: str = ""
    denied_tools: list[str] = field(default_factory=list)
    denied_functions: list[str] = field(default_factory=list)
    custom_filters: list[str] = field(default_factory=list)
    hide_binary_metadata: bool = False
    ioc_filters: dict[str, bool] = field(default_factory=dict)
    custom_filter_rules: list[dict[str, Any]] = field(default_factory=list)
    singular_analysis: bool = False
    builtin: bool = False

    # Model and token preferences for this profile
    preferred_model: str = ""  # Empty = use default
    preferred_temperature: float | None = None  # None = use default
    preferred_max_tokens: int | None = None  # None = use default
    preferred_context_window: int | None = None  # None = use default

    @property
    def has_any_ioc_filter(self) -> bool:
        """True if any IOC category is enabled or custom filter rules exist."""
        return any(self.ioc_filters.values()) or bool(self.custom_filter_rules)

    @property
    def filter_iocs_in_data(self) -> bool:
        """Backward-compat property — True when any IOC filter is active."""
        return self.has_any_ioc_filter

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict suitable for JSON storage."""
        d = asdict(self)
        # Don't persist the builtin flag — it's derived at load time
        d.pop("builtin", None)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnalysisProfile:
        """Deserialize from a dict."""
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}

        # Backward compat: old configs have filter_iocs_in_data bool
        if data.get("filter_iocs_in_data") and not data.get("ioc_filters"):
            filtered["ioc_filters"] = {k: True for k in IOC_FILTER_CATEGORIES}
            filtered.pop("filter_iocs_in_data", None)
        elif "filter_iocs_in_data" in filtered:
            filtered.pop("filter_iocs_in_data", None)

        return cls(**filtered)


# ---------------------------------------------------------------------------
# Built-in profiles
# ---------------------------------------------------------------------------

DEFAULT_PROFILE = AnalysisProfile(
    name="default",
    description="Standard analysis mode - balanced for most RE tasks",
    builtin=True,
)

PRIVATE_PROFILE = AnalysisProfile(
    name="private",
    description="Private malware analysis — no metadata or IOCs leak",
    hide_binary_metadata=True,
    ioc_filters={k: True for k in IOC_FILTER_CATEGORIES},
    singular_analysis=True,
    builtin=True,
)

MALWARE_ANALYSIS_PROFILE = AnalysisProfile(
    name="malware-analysis",
    description="Malware analysis - IOC filtering enabled, privacy-focused",
    hide_binary_metadata=True,
    ioc_filters={
        "hashes": True,
        "ipv4": True,
        "ipv6": True,
        "domains": True,
        "urls": True,
        "registry_keys": True,
        "file_paths": True,
        "emails": True,
        "crypto_wallets": True,
        "mutexes": True,
    },
    singular_analysis=True,
    preferred_model="claude-sonnet-4-20250514",  # Balanced for malware analysis
    preferred_max_tokens=16384,
    builtin=True,
)

EXPLOIT_DEV_PROFILE = AnalysisProfile(
    name="exploit-dev",
    description="Exploit development - detailed ASM, memory analysis, no restrictions",
    custom_filters=[
        "Enable detailed assembly analysis",
        "Allow memory corruption techniques",
        "Include shellcode analysis tools",
    ],
    preferred_model="claude-sonnet-4-20250514",  # Smartest for exploit dev
    preferred_temperature=0.1,  # Low temp for precision
    preferred_max_tokens=24000,  # More tokens for long exploit chains
    builtin=True,
)

FIRMWARE_ANALYSIS_PROFILE = AnalysisProfile(
    name="firmware-analysis",
    description="Firmware analysis - large binary blobs, embedded systems",
    custom_filters=[
        "Handle unknown architectures",
        "Analyze binary blobs without structure",
        "Enable embedded system analysis",
    ],
    denied_tools=[
        "debugger_breakpoint",  # Firmware can't be debugged live
    ],
    preferred_model="claude-sonnet-4-20250514",
    preferred_context_window=200000,  # Max context for large firmware
    builtin=True,
)

NETWORK_ANALYSIS_PROFILE = AnalysisProfile(
    name="network-analysis",
    description="Network protocol analysis - packet parsing, protocol reverse engineering",
    custom_filters=["Focus on protocol parsing", "Analyze network-related functions", "Include socket/API analysis"],
    ioc_filters={
        "ipv4": True,
        "ipv6": True,
        "domains": True,
        "urls": True,
    },
    preferred_model="claude-sonnet-4-20250514",
    preferred_temperature=0.2,  # Slightly higher for creative protocol thinking
    builtin=True,
)

CRYPTO_ANALYSIS_PROFILE = AnalysisProfile(
    name="crypto-analysis",
    description="Cryptography analysis - algorithm identification, math operations",
    custom_filters=["Focus on crypto primitives", "Analyze mathematical operations", "Include constant detection"],
    denied_tools=[
        "string_extraction",  # Less relevant for crypto
    ],
    preferred_model="claude-sonnet-4-20250514",  # Best for math/crypto
    preferred_temperature=0.0,  # Zero temp for mathematical precision
    builtin=True,
)

BINARY_PATCHING_PROFILE = AnalysisProfile(
    name="binary-patching",
    description="Binary patching - modification tools enabled, analysis-focused",
    custom_filters=[
        "Enable binary modification tools",
        "Allow patching and modification",
        "Include code generation assistance",
    ],
    preferred_model="claude-sonnet-4-20250514",
    preferred_temperature=0.3,  # Medium temp for creative patching
    preferred_max_tokens=20000,
    builtin=True,
)

DEEP_REVERSE_PROFILE = AnalysisProfile(
    name="deep-reverse",
    description="Deep reverse engineering - maximum analysis depth, long sessions",
    custom_filters=["Enable comprehensive analysis", "Allow extended exploration", "Include cross-reference analysis"],
    preferred_model="claude-sonnet-4-20250514",
    preferred_max_tokens=24000,  # Max tokens for deep analysis
    preferred_context_window=200000,  # Max context window
    builtin=True,
)

MOBILE_PENTEST_PROFILE = AnalysisProfile(
    name="mobile-pentest",
    description="Mobile penetration testing - Android/iOS analysis, security assessment",
    custom_filters=[
        "Focus on mobile frameworks",
        "Analyze Dalvik/ART bytecode",
        "Include iOS Mach-O analysis",
        "Enable mobile-specific security checks",
    ],
    ioc_filters={
        "domains": True,
        "urls": True,
        "file_paths": True,
    },
    preferred_model="claude-sonnet-4-20250514",
    preferred_max_tokens=20000,
    builtin=True,
)

BUILTIN_PROFILES: dict[str, AnalysisProfile] = {
    "default": DEFAULT_PROFILE,
    "private": PRIVATE_PROFILE,
    "malware-analysis": MALWARE_ANALYSIS_PROFILE,
    "exploit-dev": EXPLOIT_DEV_PROFILE,
    "firmware-analysis": FIRMWARE_ANALYSIS_PROFILE,
    "network-analysis": NETWORK_ANALYSIS_PROFILE,
    "crypto-analysis": CRYPTO_ANALYSIS_PROFILE,
    "binary-patching": BINARY_PATCHING_PROFILE,
    "deep-reverse": DEEP_REVERSE_PROFILE,
    "mobile-pentest": MOBILE_PENTEST_PROFILE,
}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_profile(name: str, custom_profiles: dict[str, dict] | None = None) -> AnalysisProfile:
    """Look up a profile by name.

    Checks built-in profiles first, then custom profiles from config.
    Falls back to DEFAULT_PROFILE if not found.
    """
    # Built-in
    if name in BUILTIN_PROFILES:
        return BUILTIN_PROFILES[name]

    # Custom
    if custom_profiles and name in custom_profiles:
        data = custom_profiles[name]
        if isinstance(data, dict):
            profile = AnalysisProfile.from_dict(data)
            profile.name = name
            log_debug(f"Loaded custom profile: {name}")
            return profile

    # Fallback
    log_debug(f"Profile '{name}' not found, falling back to default")
    return DEFAULT_PROFILE


def list_profiles(
    custom_profiles: dict[str, dict] | None = None,
) -> list[AnalysisProfile]:
    """List all available profiles (builtins + custom)."""
    profiles: list[AnalysisProfile] = list(BUILTIN_PROFILES.values())

    if custom_profiles:
        for name, data in sorted(custom_profiles.items()):
            if name in BUILTIN_PROFILES:
                continue  # don't override builtins
            if isinstance(data, dict):
                profile = AnalysisProfile.from_dict(data)
                profile.name = name
                profiles.append(profile)

    return profiles
