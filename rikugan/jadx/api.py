"""JADX integration for Rikugan - Android APK reverse engineering.

This module provides tools for analyzing Android APKs using JADX decompiler.
JADX exports APKs to Java source code, which Rikugan can then analyze.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from ..core.logging import log_debug, log_error, log_info


class JadxAnalyzer:
    """Wrapper for JADX decompiler to analyze Android APKs."""

    def __init__(self, jadx_path: str | None = None):
        """Initialize JADX analyzer.

        Args:
            jadx_path: Path to jadx CLI executable. If None, searches in PATH.
        """
        self._jadx_path = jadx_path or self._find_jadx()
        self._validate_jadx()

    def _find_jadx(self) -> str:
        """Find JADX executable in system PATH."""
        possible_names = ["jadx", "jadx.bat", "jadx.exe"]

        for name in possible_names:
            try:
                result = subprocess.run(
                    ["which", name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

        # Try common installation paths
        common_paths = [
            "/usr/local/bin/jadx",
            "/usr/bin/jadx",
            "/opt/jadx/bin/jadx",
            os.path.expanduser("~/jadx/bin/jadx"),
            os.path.expanduser("~/.local/bin/jadx"),
        ]

        for path in common_paths:
            if os.path.exists(path):
                return path

        raise RuntimeError(
            "JADX not found. Install from https://github.com/skylot/jadx "
            "or set jadx_path explicitly."
        )

    def _validate_jadx(self) -> None:
        """Validate that JADX is working."""
        try:
            result = subprocess.run(
                [self._jadx_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.strip() or result.stderr.strip()
                log_info(f"JADX found: {version}")
            else:
                log_error(f"JADX validation failed: {result.stderr}")
        except Exception as e:
            log_error(f"Failed to validate JADX: {e}")

    def decompile_apk(
        self,
        apk_path: str,
        output_dir: str,
        export_resources: bool = True,
        decompile_debug: bool = False
    ) -> str:
        """Decompile APK to Java source code.

        Args:
            apk_path: Path to APK file.
            output_dir: Directory to save decompiled sources.
            export_resources: Export resources (AndroidManifest.xml, etc.).
            decompile_debug: Include debug info.

        Returns:
            Path to decompiled sources directory.
        """
        if not os.path.exists(apk_path):
            raise FileNotFoundError(f"APK not found: {apk_path}")

        # Build JADX command
        cmd = [
            self._jadx_path,
            "-d", output_dir,
            "--show-bad-code"
        ]

        if export_resources:
            cmd.append("-e")

        if decompile_debug:
            cmd.append("-ds")

        cmd.append(apk_path)

        log_info(f"Decompiling APK: {apk_path}")
        log_debug(f"JADX command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )

            if result.returncode != 0:
                log_error(f"JADX decompilation failed: {result.stderr}")
                raise RuntimeError(f"JADX failed: {result.stderr}")

            # JADX creates subdirectory with APK name
            apk_name = Path(apk_path).stem
            decompiled_dir = Path(output_dir) / apk_name

            if not decompiled_dir.exists():
                # Fallback: check if output_dir directly contains sources
                decompiled_dir = Path(output_dir)

            log_info(f"APK decompiled to: {decompiled_dir}")
            return str(decompiled_dir)

        except subprocess.TimeoutExpired:
            log_error("JADX decompilation timed out")
            raise RuntimeError("JADX decompilation timed out")
        except Exception as e:
            log_error(f"JADX decompilation error: {e}")
            raise

    def get_package_structure(self, decompiled_dir: str) -> dict[str, Any]:
        """Analyze package structure of decompiled APK.

        Args:
            decompiled_dir: Path to decompiled sources.

        Returns:
            Dictionary with package structure:
            {
                "packages": ["com.example.app", ...],
                "activities": ["com.example.app.MainActivity", ...],
                "services": ["com.example.app.MyService", ...],
                "receivers": ["com.example.app.MyReceiver", ...],
                "providers": ["com.example.app.MyProvider", ...],
                "total_classes": 150,
                "total_methods": 2500
            }
        """
        decompiled_path = Path(decompiled_dir)
        if not decompiled_path.exists():
            raise FileNotFoundError(f"Decompiled directory not found: {decompiled_dir}")

        sources_dir = decompiled_path / "sources"
        if not sources_dir.exists():
            sources_dir = decompiled_path

        result = {
            "packages": [],
            "activities": [],
            "services": [],
            "receivers": [],
            "providers": [],
            "total_classes": 0,
            "total_methods": 0
        }

        # Find all Java files
        java_files = list(sources_dir.rglob("*.java"))
        result["total_classes"] = len(java_files)

        for java_file in java_files:
            # Extract package name from file path
            rel_path = java_file.relative_to(sources_dir)
            parts = rel_path.parts[:-1]  # Remove filename

            if parts:
                package = ".".join(parts)
                if package not in result["packages"]:
                    result["packages"].append(package)

            # Read file content to analyze class type
            try:
                with open(java_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                    # Count methods
                    method_count = content.count("void ") + content.count("int ") + content.count("String ")
                    result["total_methods"] += method_count

                    # Check for Android components
                    if "extends Activity" in content or "extends AppCompatActivity" in content:
                        class_name = self._extract_class_name(content, package)
                        if class_name:
                            result["activities"].append(class_name)

                    elif "extends Service" in content:
                        class_name = self._extract_class_name(content, package)
                        if class_name:
                            result["services"].append(class_name)

                    elif "extends BroadcastReceiver" in content:
                        class_name = self._extract_class_name(content, package)
                        if class_name:
                            result["receivers"].append(class_name)

                    elif "extends ContentProvider" in content:
                        class_name = self._extract_class_name(content, package)
                        if class_name:
                            result["providers"].append(class_name)

            except Exception as e:
                log_debug(f"Failed to analyze {java_file}: {e}")

        return result

    def _extract_class_name(self, content: str, package: str) -> str | None:
        """Extract class name from Java file content."""
        import re

        # Find class declaration
        match = re.search(r'public\s+class\s+(\w+)', content)
        if match:
            class_name = match.group(1)
            if package:
                return f"{package}.{class_name}"
            return class_name
        return None

    def find_android_manifest(self, decompiled_dir: str) -> dict[str, Any]:
        """Find and parse AndroidManifest.xml.

        Args:
            decompiled_dir: Path to decompiled sources.

        Returns:
            Dictionary with manifest information.
        """
        decompiled_path = Path(decompiled_dir)

        # Look for AndroidManifest.xml in various locations
        manifest_paths = [
            decompiled_path / "AndroidManifest.xml",
            decompiled_path / "resources" / "AndroidManifest.xml",
            decompiled_path.parent / "AndroidManifest.xml",
        ]

        for manifest_path in manifest_paths:
            if manifest_path.exists():
                return self._parse_manifest(manifest_path)

        return {"error": "AndroidManifest.xml not found"}

    def _parse_manifest(self, manifest_path: Path) -> dict[str, Any]:
        """Parse AndroidManifest.xml and extract key information."""
        try:
            with open(manifest_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            import re
            result = {
                "package": re.search(r'package="([^"]+)"', content).group(1) if re.search(r'package="([^"]+)"', content) else "",
                "version_code": re.search(r'versionCode="([^"]+)"', content).group(1) if re.search(r'versionCode="([^"]+)"', content) else "",
                "version_name": re.search(r'versionName="([^"]+)"', content).group(1) if re.search(r'versionName="([^"]+)"', content) else "",
                "min_sdk": re.search(r'minSdkVersion="([^"]+)"', content).group(1) if re.search(r'minSdkVersion="([^"]+)"', content) else "",
                "target_sdk": re.search(r'targetSdkVersion="([^"]+)"', content).group(1) if re.search(r'targetSdkVersion="([^"]+)"', content) else "",
                "permissions": re.findall(r'uses-permission\s+android:name="([^"]+)"', content),
                "activities": re.findall(r'activity\s+android:name="([^"]+)"', content),
                "services": re.findall(r'service\s+android:name="([^"]+)"', content),
                "receivers": re.findall(r'receiver\s+android:name="([^"]+)"', content),
                "providers": re.findall(r'provider\s+android:name="([^"]+)"', content),
            }

            return result

        except Exception as e:
            log_error(f"Failed to parse manifest: {e}")
            return {"error": str(e)}

    def search_string_in_sources(
        self,
        decompiled_dir: str,
        search_string: str,
        case_sensitive: bool = False
    ) -> list[dict[str, Any]]:
        """Search for string in decompiled Java sources.

        Args:
            decompiled_dir: Path to decompiled sources.
            search_string: String to search for.
            case_sensitive: Perform case-sensitive search.

        Returns:
            List of matches with file and line information.
        """
        decompiled_path = Path(decompiled_dir)
        sources_dir = decompiled_path / "sources"
        if not sources_dir.exists():
            sources_dir = decompiled_path

        matches = []
        java_files = list(sources_dir.rglob("*.java"))

        for java_file in java_files:
            try:
                with open(java_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        search_line = line if case_sensitive else line.lower()
                        search_term = search_string if case_sensitive else search_string.lower()

                        if search_term in search_line:
                            matches.append({
                                "file": str(java_file.relative_to(sources_dir)),
                                "line": line_num,
                                "content": line.strip(),
                                "package": self._get_package_from_file(java_file, sources_dir)
                            })
            except Exception as e:
                log_debug(f"Failed to search in {java_file}: {e}")

        return matches

    def _get_package_from_file(self, java_file: Path, sources_dir: Path) -> str:
        """Extract package name from Java file path."""
        rel_path = java_file.relative_to(sources_dir)
        parts = rel_path.parts[:-1]  # Remove filename
        return ".".join(parts) if parts else ""

    def find_native_libraries(self, decompiled_dir: str) -> list[str]:
        """Find native libraries (.so files) in decompiled APK.

        Args:
            decompiled_dir: Path to decompiled sources.

        Returns:
            List of native library paths.
        """
        decompiled_path = Path(decompiled_dir)
        lib_dirs = [
            decompiled_path / "lib" / "arm64-v8a",
            decompiled_path / "lib" / "armeabi-v7a",
            decompiled_path / "lib" / "x86",
            decompiled_path / "lib" / "x86_64",
        ]

        native_libs = []
        for lib_dir in lib_dirs:
            if lib_dir.exists():
                for lib_file in lib_dir.glob("*.so"):
                    native_libs.append(str(lib_file.relative_to(decompiled_path)))

        return native_libs

    def get_class_dependencies(self, decompiled_dir: str, class_name: str) -> dict[str, Any]:
        """Analyze dependencies of a specific class.

        Args:
            decompiled_dir: Path to decompiled sources.
            class_name: Fully qualified class name (e.g., "com.example.app.MainActivity").

        Returns:
            Dictionary with class dependencies:
            {
                "imports": ["android.app.Activity", ...],
                "methods": ["onCreate", "onResume"],
                "fields": ["private Button button;"],
                "extends": "Activity",
                "implements": ["View.OnClickListener"]
            }
        """
        decompiled_path = Path(decompiled_dir)
        sources_dir = decompiled_path / "sources"
        if not sources_dir.exists():
            sources_dir = decompiled_path

        # Convert class name to file path
        class_path = class_name.replace(".", "/") + ".java"
        class_file = sources_dir / class_path

        if not class_file.exists():
            return {"error": f"Class file not found: {class_file}"}

        try:
            with open(class_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            import re
            result = {
                "imports": re.findall(r'import\s+([\w.]+);', content),
                "methods": re.findall(r'(public|private|protected)?\s*(static)?\s*\w+\s+(\w+)\s*\(', content),
                "fields": re.findall(r'(public|private|protected)?\s*(static)?\s*\w+\s+\w+\s*;', content),
                "extends": re.search(r'class\s+\w+\s+extends\s+(\w+)', content).group(1) if re.search(r'class\s+\w+\s+extends\s+(\w+)', content) else "",
                "implements": re.findall(r'implements\s+([\w\s,]+)', content),
                "class_name": class_name
            }

            return result

        except Exception as e:
            log_error(f"Failed to analyze class {class_name}: {e}")
            return {"error": str(e)}

    def export_to_json(self, decompiled_dir: str, output_file: str) -> None:
        """Export analysis results to JSON file.

        Args:
            decompiled_dir: Path to decompiled sources.
            output_file: Path to output JSON file.
        """
        analysis = {
            "package_structure": self.get_package_structure(decompiled_dir),
            "manifest": self.find_android_manifest(decompiled_dir),
            "native_libraries": self.find_native_libraries(decompiled_dir)
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2)

        log_info(f"Analysis exported to: {output_file}")


def create_jadx_tools(analyzer: JadxAnalyzer) -> list[dict[str, Any]]:
    """Create Rikugan tool definitions for JADX analysis.

    Args:
        analyzer: JadxAnalyzer instance.

    Returns:
        List of tool definitions compatible with Rikugan tool registry.
    """
    from ..tools.base import ToolDefinition, ParameterSchema

    tools = [
        ToolDefinition(
            name="jadx_decompile_apk",
            description="Decompile Android APK to Java source code using JADX",
            parameters=[
                ParameterSchema(
                    name="apk_path",
                    type="string",
                    description="Path to the APK file to decompile",
                    required=True
                ),
                ParameterSchema(
                    name="output_dir",
                    type="string",
                    description="Directory to save decompiled sources",
                    required=True
                ),
                ParameterSchema(
                    name="export_resources",
                    type="boolean",
                    description="Export AndroidManifest.xml and resources",
                    required=False,
                    default=True
                )
            ],
            category="jadx",
            handler=lambda **kwargs: analyzer.decompile_apk(**kwargs)
        ),

        ToolDefinition(
            name="jadx_analyze_structure",
            description="Analyze package structure of decompiled APK",
            parameters=[
                ParameterSchema(
                    name="decompiled_dir",
                    type="string",
                    description="Path to decompiled sources directory",
                    required=True
                )
            ],
            category="jadx",
            handler=lambda **kwargs: analyzer.get_package_structure(**kwargs)
        ),

        ToolDefinition(
            name="jadx_find_manifest",
            description="Find and parse AndroidManifest.xml",
            parameters=[
                ParameterSchema(
                    name="decompiled_dir",
                    type="string",
                    description="Path to decompiled sources directory",
                    required=True
                )
            ],
            category="jadx",
            handler=lambda **kwargs: analyzer.find_android_manifest(**kwargs)
        ),

        ToolDefinition(
            name="jadx_search_string",
            description="Search for string in decompiled Java sources",
            parameters=[
                ParameterSchema(
                    name="decompiled_dir",
                    type="string",
                    description="Path to decompiled sources directory",
                    required=True
                ),
                ParameterSchema(
                    name="search_string",
                    type="string",
                    description="String to search for",
                    required=True
                ),
                ParameterSchema(
                    name="case_sensitive",
                    type="boolean",
                    description="Perform case-sensitive search",
                    required=False,
                    default=False
                )
            ],
            category="jadx",
            handler=lambda **kwargs: analyzer.search_string_in_sources(**kwargs)
        ),

        ToolDefinition(
            name="jadx_analyze_class",
            description="Analyze dependencies and structure of a specific class",
            parameters=[
                ParameterSchema(
                    name="decompiled_dir",
                    type="string",
                    description="Path to decompiled sources directory",
                    required=True
                ),
                ParameterSchema(
                    name="class_name",
                    type="string",
                    description="Fully qualified class name (e.g., com.example.app.MainActivity)",
                    required=True
                )
            ],
            category="jadx",
            handler=lambda **kwargs: analyzer.get_class_dependencies(**kwargs)
        ),

        ToolDefinition(
            name="jadx_find_native_libs",
            description="Find native libraries (.so files) in decompiled APK",
            parameters=[
                ParameterSchema(
                    name="decompiled_dir",
                    type="string",
                    description="Path to decompiled sources directory",
                    required=True
                )
            ],
            category="jadx",
            handler=lambda **kwargs: analyzer.find_native_libraries(**kwargs)
        ),

        ToolDefinition(
            name="jadx_export_analysis",
            description="Export complete APK analysis to JSON file",
            parameters=[
                ParameterSchema(
                    name="decompiled_dir",
                    type="string",
                    description="Path to decompiled sources directory",
                    required=True
                ),
                ParameterSchema(
                    name="output_file",
                    type="string",
                    description="Path to output JSON file",
                    required=True
                )
            ],
            category="jadx",
            handler=lambda **kwargs: analyzer.export_to_json(**kwargs)
        )
    ]

    return tools
