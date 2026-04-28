"""Type library auto-detection and structure recovery.

Automatically detects and applies standard type libraries (Windows, Linux, etc.)
to recover structure definitions and function signatures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TypeCategory(str, Enum):
    """Categories of types."""

    PRIMITIVE = "primitive"
    STRUCT = "struct"
    UNION = "union"
    CLASS = "class"
    ENUM = "enum"
    FUNCTION_POINTER = "function_pointer"
    ARRAY = "array"
    POINTER = "pointer"


class PlatformType(str, Enum):
    """Platform-specific type libraries."""

    WINDOWS_X86 = "windows_x86"
    WINDOWS_X64 = "windows_x64"
    LINUX_X86 = "linux_x86"
    LINUX_X64 = "linux_x64"
    MACOS = "macos"
    ANDROID = "android"
    IOS = "ios"
    CUSTOM = "custom"


@dataclass
class TypeInfo:
    """Information about a type."""

    name: str
    category: TypeCategory
    size: int
    members: dict[str, str] = field(default_factory=dict)  # member_name -> type_name
    platform: PlatformType = PlatformType.CUSTOM
    confidence: float = 1.0  # 0.0 to 1.0
    header_file: str = ""  # Source header file if known


@dataclass
class SignatureMatch:
    """A matched function signature."""

    function_name: str
    address: int
    signature: str
    confidence: float
    library_name: str
    reason: str


# Standard Windows types (x86 and x64)
WINDOWS_TYPES = {
    # Primitives
    "BYTE": TypeInfo("BYTE", TypeCategory.PRIMITIVE, 1, platform=PlatformType.WINDOWS_X86),
    "WORD": TypeInfo("WORD", TypeCategory.PRIMITIVE, 2, platform=PlatformType.WINDOWS_X86),
    "DWORD": TypeInfo("DWORD", TypeCategory.PRIMITIVE, 4, platform=PlatformType.WINDOWS_X86),
    "QWORD": TypeInfo("QWORD", TypeCategory.PRIMITIVE, 8, platform=PlatformType.WINDOWS_X86),
    "BOOL": TypeInfo("BOOL", TypeCategory.PRIMITIVE, 4, platform=PlatformType.WINDOWS_X86),
    "BOOLEAN": TypeInfo("BOOLEAN", TypeCategory.PRIMITIVE, 1, platform=PlatformType.WINDOWS_X86),
    "CHAR": TypeInfo("CHAR", TypeCategory.PRIMITIVE, 1, platform=PlatformType.WINDOWS_X86),
    "WCHAR": TypeInfo("WCHAR", TypeCategory.PRIMITIVE, 2, platform=PlatformType.WINDOWS_X86),
    "INT": TypeInfo("INT", TypeCategory.PRIMITIVE, 4, platform=PlatformType.WINDOWS_X86),
    "INT8": TypeInfo("INT8", TypeCategory.PRIMITIVE, 1, platform=PlatformType.WINDOWS_X86),
    "INT16": TypeInfo("INT16", TypeCategory.PRIMITIVE, 2, platform=PlatformType.WINDOWS_X86),
    "INT32": TypeInfo("INT32", TypeCategory.PRIMITIVE, 4, platform=PlatformType.WINDOWS_X86),
    "INT64": TypeInfo("INT64", TypeCategory.PRIMITIVE, 8, platform=PlatformType.WINDOWS_X86),
    "UINT": TypeInfo("UINT", TypeCategory.PRIMITIVE, 4, platform=PlatformType.WINDOWS_X86),
    "UINT8": TypeInfo("UINT8", TypeCategory.PRIMITIVE, 1, platform=PlatformType.WINDOWS_X86),
    "UINT16": TypeInfo("UINT16", TypeCategory.PRIMITIVE, 2, platform=PlatformType.WINDOWS_X86),
    "UINT32": TypeInfo("UINT32", TypeCategory.PRIMITIVE, 4, platform=PlatformType.WINDOWS_X86),
    "UINT64": TypeInfo("UINT64", TypeCategory.PRIMITIVE, 8, platform=PlatformType.WINDOWS_X86),
    "LONG": TypeInfo("LONG", TypeCategory.PRIMITIVE, 4, platform=PlatformType.WINDOWS_X86),
    "ULONG": TypeInfo("ULONG", TypeCategory.PRIMITIVE, 4, platform=PlatformType.WINDOWS_X86),
    "LONGLONG": TypeInfo("LONGLONG", TypeCategory.PRIMITIVE, 8, platform=PlatformType.WINDOWS_X86),
    "ULONGLONG": TypeInfo("ULONGLONG", TypeCategory.PRIMITIVE, 8, platform=PlatformType.WINDOWS_X86),
    "FLOAT": TypeInfo("FLOAT", TypeCategory.PRIMITIVE, 4, platform=PlatformType.WINDOWS_X86),
    "DOUBLE": TypeInfo("DOUBLE", TypeCategory.PRIMITIVE, 8, platform=PlatformType.WINDOWS_X86),
    "HANDLE": TypeInfo("HANDLE", TypeCategory.POINTER, 4, platform=PlatformType.WINDOWS_X86),
    "HWND": TypeInfo("HWND", TypeCategory.POINTER, 4, platform=PlatformType.WINDOWS_X86),
    "HINSTANCE": TypeInfo("HINSTANCE", TypeCategory.POINTER, 4, platform=PlatformType.WINDOWS_X86),
    "HMODULE": TypeInfo("HMODULE", TypeCategory.POINTER, 4, platform=PlatformType.WINDOWS_X86),
    "HRESULT": TypeInfo("HRESULT", TypeCategory.PRIMITIVE, 4, platform=PlatformType.WINDOWS_X86),
    "VOID": TypeInfo("VOID", TypeCategory.PRIMITIVE, 0, platform=PlatformType.WINDOWS_X86),
    "LPCSTR": TypeInfo("LPCSTR", TypeCategory.POINTER, 4, platform=PlatformType.WINDOWS_X86),
    "LPWSTR": TypeInfo("LPWSTR", TypeCategory.POINTER, 4, platform=PlatformType.WINDOWS_X86),
    "LPCVOID": TypeInfo("LPCVOID", TypeCategory.POINTER, 4, platform=PlatformType.WINDOWS_X86),
    "LPVOID": TypeInfo("LPVOID", TypeCategory.POINTER, 4, platform=PlatformType.WINDOWS_X86),
    "SIZE_T": TypeInfo("SIZE_T", TypeCategory.PRIMITIVE, 4, platform=PlatformType.WINDOWS_X86),
}

# Common Windows structures
WINDOWS_STRUCTS = {
    "RECT": TypeInfo(
        "RECT",
        TypeCategory.STRUCT,
        16,
        members={
            "left": "LONG",
            "top": "LONG",
            "right": "LONG",
            "bottom": "LONG",
        },
        platform=PlatformType.WINDOWS_X86,
        header_file="windef.h",
    ),
    "POINT": TypeInfo(
        "POINT",
        TypeCategory.STRUCT,
        8,
        members={
            "x": "LONG",
            "y": "LONG",
        },
        platform=PlatformType.WINDOWS_X86,
        header_file="windef.h",
    ),
    "MSG": TypeInfo(
        "MSG",
        TypeCategory.STRUCT,
        28,
        members={
            "hwnd": "HWND",
            "message": "UINT",
            "wParam": "WPARAM",
            "lParam": "LPARAM",
            "time": "DWORD",
            "pt": "POINT",
        },
        platform=PlatformType.WINDOWS_X86,
        header_file="winuser.h",
    ),
}

# Standard Linux types
LINUX_TYPES = {
    "size_t": TypeInfo("size_t", TypeCategory.PRIMITIVE, 4, platform=PlatformType.LINUX_X86),
    "ssize_t": TypeInfo("ssize_t", TypeCategory.PRIMITIVE, 4, platform=PlatformType.LINUX_X86),
    "pid_t": TypeInfo("pid_t", TypeCategory.PRIMITIVE, 4, platform=PlatformType.LINUX_X86),
    "uid_t": TypeInfo("uid_t", TypeCategory.PRIMITIVE, 4, platform=PlatformType.LINUX_X86),
    "gid_t": TypeInfo("gid_t", TypeCategory.PRIMITIVE, 4, platform=PlatformType.LINUX_X86),
    "off_t": TypeInfo("off_t", TypeCategory.PRIMITIVE, 4, platform=PlatformType.LINUX_X86),
    "time_t": TypeInfo("time_t", TypeCategory.PRIMITIVE, 4, platform=PlatformType.LINUX_X86),
    "socklen_t": TypeInfo("socklen_t", TypeCategory.PRIMITIVE, 4, platform=PlatformType.LINUX_X86),
    "in_addr_t": TypeInfo("in_addr_t", TypeCategory.PRIMITIVE, 4, platform=PlatformType.LINUX_X86),
    "in_port_t": TypeInfo("in_port_t", TypeCategory.PRIMITIVE, 2, platform=PlatformType.LINUX_X86),
}

# Common Linux structures
LINUX_STRUCTS = {
    "sockaddr": TypeInfo(
        "sockaddr",
        TypeCategory.STRUCT,
        16,
        members={
            "sa_family": "unsigned short",
            "sa_data": "char[14]",
        },
        platform=PlatformType.LINUX_X86,
        header_file="sys/socket.h",
    ),
    "sockaddr_in": TypeInfo(
        "sockaddr_in",
        TypeCategory.STRUCT,
        16,
        members={
            "sin_family": "short",
            "sin_port": "unsigned short",
            "sin_addr": "in_addr",
            "sin_zero": "char[8]",
        },
        platform=PlatformType.LINUX_X86,
        header_file="netinet/in.h",
    ),
    "in_addr": TypeInfo(
        "in_addr",
        TypeCategory.STRUCT,
        4,
        members={
            "s_addr": "unsigned long",
        },
        platform=PlatformType.LINUX_X86,
        header_file="netinet/in.h",
    ),
}


class TypeLibrary:
    """Type library for a specific platform."""

    def __init__(self, platform: PlatformType):
        self.platform = platform
        self.types: dict[str, TypeInfo] = {}
        self.function_signatures: dict[str, str] = {}
        self._load_standard_types()

    def _load_standard_types(self) -> None:
        """Load standard types for the platform."""
        if self.platform in (PlatformType.WINDOWS_X86, PlatformType.WINDOWS_X64):
            self.types.update(WINDOWS_TYPES)
            self.types.update(WINDOWS_STRUCTS)
        elif self.platform in (PlatformType.LINUX_X86, PlatformType.LINUX_X64):
            self.types.update(LINUX_TYPES)
            self.types.update(LINUX_STRUCTS)

    def add_type(self, type_info: TypeInfo) -> None:
        """Add a custom type to the library."""
        self.types[type_info.name] = type_info

    def add_signature(self, func_name: str, signature: str) -> None:
        """Add a function signature to the library."""
        self.function_signatures[func_name] = signature

    def get_type(self, type_name: str) -> TypeInfo | None:
        """Get type information by name."""
        return self.types.get(type_name)

    def get_signature(self, func_name: str) -> str | None:
        """Get function signature by name."""
        return self.function_signatures.get(func_name)


class TypeRecoveryEngine:
    """Engine for automatic type detection and recovery."""

    def __init__(self, platform: PlatformType = PlatformType.CUSTOM):
        self.platform = platform
        self.library = TypeLibrary(platform)
        self.matches: list[SignatureMatch] = []

    def detect_platform(self, import_names: list[str]) -> PlatformType:
        """Detect target platform from imported functions."""
        import_lower = [name.lower() for name in import_names]

        # Check for Windows
        windows_indicators = [
            "createfilea",
            "createfilew",
            "registryopen",
            "registryclose",
            "virtualalloc",
            "virtualfree",
            "loadlibrarya",
            "loadlibraryw",
            "getmodulehandle",
            "getprocaddress",
        ]

        linux_indicators = [
            "libc.so.6",
            "libpthread.so.0",
            "g_malloc",
            "g_free",
            "__libc_start_main",
        ]

        windows_score = sum(1 for ind in windows_indicators if any(ind in imp for imp in import_lower))
        linux_score = sum(1 for ind in linux_indicators if any(ind in imp for imp in import_lower))

        if windows_score > linux_score:
            return PlatformType.WINDOWS_X86  # Assume x86 for now
        elif linux_score > windows_score:
            return PlatformType.LINUX_X86
        else:
            return PlatformType.CUSTOM

    def match_structures(self, data_refs: list[dict[str, Any]]) -> list[tuple[int, TypeInfo]]:
        """Match data references to known structures.

        Args:
            data_refs: List of data reference dicts with 'address', 'size', 'values'

        Returns:
            List of (address, type_info) tuples for matches
        """
        matches = []

        for ref in data_refs:
            ref_size = ref.get("size", 0)
            ref_addr = ref.get("address", 0)

            # Find structures with matching size
            for _type_name, type_info in self.library.types.items():
                if type_info.category == TypeCategory.STRUCT and type_info.size == ref_size:
                    # Try to validate by checking member offsets
                    if self._validate_struct_match(ref, type_info):
                        matches.append((ref_addr, type_info))

        return matches

    def _validate_struct_match(self, data_ref: dict[str, Any], type_info: TypeInfo) -> bool:
        """Validate that a data reference matches a structure type."""
        # For now, just check size
        # Could be enhanced to validate member offsets and values
        return data_ref.get("size", 0) == type_info.size

    def match_function_signature(self, func_data: dict[str, Any], imports: list[str]) -> SignatureMatch | None:
        """Match a function to a known signature.

        Args:
            func_data: Function data with address, name, args
            imports: List of imported function names

        Returns:
            Signature match if found
        """
        func_name = func_data.get("name", "")
        func_addr = func_data.get("address", func_data.get("start", 0))

        # Direct name match
        for import_name in imports:
            if func_name.lower() in import_name.lower() or import_name.lower() in func_name.lower():
                return SignatureMatch(
                    function_name=func_name,
                    address=func_addr,
                    signature=self._infer_signature_from_import(import_name, func_data),
                    confidence=0.8,
                    library_name="import",
                    reason=f"Name matches import {import_name}",
                )

        # Pattern-based matching for common functions
        pattern_matches = self._match_by_pattern(func_data, imports)
        if pattern_matches:
            return pattern_matches

        return None

    def _infer_signature_from_import(self, import_name: str, func_data: dict[str, Any]) -> str:
        """Infer function signature from import name."""
        # Map common Windows API signatures
        api_signatures = {
            "createfile": "HANDLE CreateFile(LPCSTR lpFileName, DWORD dwDesiredAccess, DWORD dwShareMode, LPSECURITY_ATTRIBUTES lpSecurityAttributes, DWORD dwCreationDisposition, DWORD dwFlagsAndAttributes, HANDLE hTemplateFile)",
            "readfile": "BOOL ReadFile(HANDLE hFile, LPVOID lpBuffer, DWORD nNumberOfBytesToRead, LPDWORD lpNumberOfBytesRead, LPOVERLAPPED lpOverlapped)",
            "writefile": "BOOL WriteFile(HANDLE hFile, LPCVOID lpBuffer, DWORD nNumberOfBytesToWrite, LPDWORD lpNumberOfBytesWritten, LPOVERLAPPED lpOverlapped)",
            "closehandle": "BOOL CloseHandle(HANDLE hObject)",
            "virtualalloc": "LPVOID VirtualAlloc(LPVOID lpAddress, SIZE_T dwSize, DWORD flAllocationType, DWORD flProtect)",
            "virtualfree": "BOOL VirtualFree(LPVOID lpAddress, SIZE_T dwSize, DWORD dwFreeType)",
            "loadlibrary": "HMODULE LoadLibrary(LPCSTR lpLibFileName)",
            "getprocaddress": "FARPROC GetProcAddress(HMODULE hModule, LPCSTR lpProcName)",
        }

        import_lower = import_name.lower()
        for pattern, signature in api_signatures.items():
            if pattern in import_lower:
                return signature

        # Generic signature
        num_args = func_data.get("arg_count", 0)
        args = ", ".join([f"arg{i}" for i in range(num_args)])
        return f"void {func_data.get('name', 'unknown')}({args})"

    def _match_by_pattern(self, func_data: dict[str, Any], imports: list[str]) -> SignatureMatch | None:
        """Match function by behavioral patterns."""
        func_name = func_data.get("name", "").lower()
        callees = func_data.get("callees", [])

        # Check for common patterns
        if "malloc" in func_name or any("malloc" in c.lower() for c in callees):
            return SignatureMatch(
                function_name=func_data.get("name", ""),
                address=func_data.get("address", 0),
                signature="void* malloc(size_t size)",
                confidence=0.6,
                library_name="libc",
                reason="Memory allocation pattern detected",
            )

        if "free" in func_name or any("free" in c.lower() for c in callees):
            return SignatureMatch(
                function_name=func_data.get("name", ""),
                address=func_data.get("address", 0),
                signature="void free(void* ptr)",
                confidence=0.6,
                library_name="libc",
                reason="Memory deallocation pattern detected",
            )

        return None

    def apply_type_to_address(self, address: int, type_name: str) -> bool:
        """Apply a type to a specific address (placeholder for host integration)."""
        # This would be implemented by host-specific code
        return True

    def apply_signature_to_function(self, func_addr: int, signature: str) -> bool:
        """Apply a signature to a function (placeholder for host integration)."""
        # This would be implemented by host-specific code
        return True
