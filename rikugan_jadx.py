#!/usr/bin/env python3
"""
Rikugan JADX Plugin - Android APK Reverse Engineering Assistant

This script provides command-line interface for analyzing Android APKs
using JADX decompiler integrated with Rikugan AI assistant.

Usage:
    python rikugan_jadx.py analyze /path/to/app.apk
    python rikugan_jadx.py search /path/to/app.apk "API_KEY"
    python rikugan_jadx.py structure /path/to/app.apk
    python rikugan_jadx.py interactive /path/to/app.apk

Requirements:
    - JADX: https://github.com/skylot/jadx
    - Python 3.10+
    - Rikugan dependencies

Author: Ali Can Gönüllü
License: MIT
"""

__version__ = "1.0.0"
__author__ = "Ali Can Gönüllü"

import argparse
import json
import os
import sys
from pathlib import Path

# Add Rikugan to path
rikugan_path = Path(__file__).parent
sys.path.insert(0, str(rikugan_path))

from rikugan.jadx import JadxAnalyzer


def print_section(title: str) -> None:
    """Print formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_json(data: dict, pretty: bool = True) -> None:
    """Print JSON data."""
    if pretty:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(data))


def cmd_analyze(args) -> int:
    """Analyze APK structure and components."""
    print_section("🔍 Analyzing APK")

    try:
        analyzer = JadxAnalyzer(jadx_path=args.jadx)

        # Decompile APK
        print(f"📦 Decompiling {args.apk}...")
        decompiled_dir = analyzer.decompile_apk(
            args.apk,
            args.output,
            export_resources=not args.no_resources
        )
        print(f"✅ Decompiled to: {decompiled_dir}")

        # Analyze structure
        print("\n📊 Analyzing package structure...")
        structure = analyzer.get_package_structure(decompiled_dir)
        print_json(structure)

        # Parse manifest
        print("\n📋 Parsing AndroidManifest.xml...")
        manifest = analyzer.find_android_manifest(decompiled_dir)
        print_json(manifest)

        # Find native libraries
        print("\n🔧 Finding native libraries...")
        native_libs = analyzer.find_native_libraries(decompiled_dir)
        if native_libs:
            print(f"Found {len(native_libs)} native libraries:")
            for lib in native_libs:
                print(f"  - {lib}")
        else:
            print("No native libraries found")

        # Export analysis
        if args.export:
            print(f"\n💾 Exporting analysis to {args.export}...")
            analyzer.export_to_json(decompiled_dir, args.export)
            print("✅ Analysis exported")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def cmd_search(args) -> int:
    """Search for string in decompiled sources."""
    print_section("🔎 Searching in APK")

    try:
        analyzer = JadxAnalyzer(jadx_path=args.jadx)

        # Decompile if not already done
        if not os.path.exists(args.decompiled_dir):
            print(f"📦 Decompiling {args.apk}...")
            decompiled_dir = analyzer.decompile_apk(
                args.apk,
                args.output or "/tmp/jadx_output"
            )
        else:
            decompiled_dir = args.decompiled_dir

        # Search
        print(f"🔍 Searching for '{args.search_string}'...")
        matches = analyzer.search_string_in_sources(
            decompiled_dir,
            args.search_string,
            case_sensitive=args.case_sensitive
        )

        if matches:
            print(f"\n✅ Found {len(matches)} matches:\n")
            for i, match in enumerate(matches[:args.max_results], 1):
                print(f"[{i}] {match['file']}:{match['line']}")
                print(f"    Package: {match['package']}")
                print(f"    Code: {match['content'][:100]}...")
                print()
        else:
            print("❌ No matches found")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def cmd_structure(args) -> int:
    """Show package structure."""
    print_section("📊 Package Structure")

    try:
        analyzer = JadxAnalyzer(jadx_path=args.jadx)

        # Decompile if needed
        if not os.path.exists(args.decompiled_dir):
            print(f"📦 Decompiling {args.apk}...")
            decompiled_dir = analyzer.decompile_apk(
                args.apk,
                args.output or "/tmp/jadx_output"
            )
        else:
            decompiled_dir = args.decompiled_dir

        # Analyze structure
        structure = analyzer.get_package_structure(decompiled_dir)

        print(f"📦 Total Classes: {structure['total_classes']}")
        print(f"⚙️  Total Methods: {structure['total_methods']}")
        print(f"📋 Packages: {len(structure['packages'])}")

        if structure['activities']:
            print(f"\n🎯 Activities ({len(structure['activities'])}):")
            for activity in structure['activities'][:10]:
                print(f"  - {activity}")
            if len(structure['activities']) > 10:
                print(f"  ... and {len(structure['activities']) - 10} more")

        if structure['services']:
            print(f"\n🔧 Services ({len(structure['services'])}):")
            for service in structure['services'][:10]:
                print(f"  - {service}")
            if len(structure['services']) > 10:
                print(f"  ... and {len(structure['services']) - 10} more")

        if structure['receivers']:
            print(f"\n📡 Receivers ({len(structure['receivers'])}):")
            for receiver in structure['receivers'][:10]:
                print(f"  - {receiver}")
            if len(structure['receivers']) > 10:
                print(f"  ... and {len(structure['receivers']) - 10} more")

        if structure['providers']:
            print(f"\n💾 Providers ({len(structure['providers'])}):")
            for provider in structure['providers'][:10]:
                print(f"  - {provider}")
            if len(structure['providers']) > 10:
                print(f"  ... and {len(structure['providers']) - 10} more")

        # Export to JSON if requested
        if args.export:
            with open(args.export, 'w') as f:
                json.dump(structure, f, indent=2)
            print(f"\n💾 Structure exported to {args.export}")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def cmd_class(args) -> int:
    """Analyze specific class."""
    print_section(f"🔍 Analyzing Class: {args.class_name}")

    try:
        analyzer = JadxAnalyzer(jadx_path=args.jadx)

        # Decompile if needed
        if not os.path.exists(args.decompiled_dir):
            print(f"📦 Decompiling {args.apk}...")
            decompiled_dir = analyzer.decompile_apk(
                args.apk,
                args.output or "/tmp/jadx_output"
            )
        else:
            decompiled_dir = args.decompiled_dir

        # Analyze class
        analysis = analyzer.get_class_dependencies(decompiled_dir, args.class_name)

        if "error" in analysis:
            print(f"❌ {analysis['error']}")
            return 1

        print(f"📦 Class: {analysis['class_name']}")
        if analysis['extends']:
            print(f"📌 Extends: {analysis['extends']}")
        if analysis['implements']:
            print(f"🔌 Implements: {', '.join(analysis['implements'])}")

        print(f"\n📥 Imports ({len(analysis['imports'])}):")
        for imp in analysis['imports'][:20]:
            print(f"  - {imp}")
        if len(analysis['imports']) > 20:
            print(f"  ... and {len(analysis['imports']) - 20} more")

        print(f"\n⚙️  Methods:")
        for method in analysis['methods'][:20]:
            print(f"  - {method}")
        if len(analysis['methods']) > 20:
            print(f"  ... and {len(analysis['methods']) - 20} more")

        print(f"\n🔧 Fields:")
        for field in analysis['fields'][:20]:
            print(f"  - {field}")
        if len(analysis['fields']) > 20:
            print(f"  ... and {len(analysis['fields']) - 20} more")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def cmd_interactive(args) -> int:
    """Interactive mode with Rikugan AI."""
    print_section("🤖 Rikugan JADX Interactive Mode")

    try:
        print("📦 Initializing JADX analyzer...")
        analyzer = JadxAnalyzer(jadx_path=args.jadx)

        # Decompile APK
        print(f"🔧 Decompiling {args.apk}...")
        decompiled_dir = analyzer.decompile_apk(
            args.apk,
            args.output or "/tmp/jadx_output"
        )

        # Perform analysis
        print("📊 Analyzing APK structure...")
        structure = analyzer.get_package_structure(decompiled_dir)
        manifest = analyzer.find_android_manifest(decompiled_dir)

        # Prepare context for AI
        context = {
            "apk_path": args.apk,
            "decompiled_dir": decompiled_dir,
            "structure": structure,
            "manifest": manifest
        }

        print("\n✅ APK analyzed successfully!")
        print("\n🤖 You can now ask questions about the APK.")
        print("Examples:")
        print("  - 'What are the main entry points?'")
        print("  - 'Find network communication code'")
        print("  - 'Analyze the MainActivity class'")
        print("  - 'What permissions does this app request?'")
        print("  - 'Find crypto API usage'")
        print("\nType 'quit' to exit\n")

        # Simple interactive loop
        while True:
            try:
                user_input = input("🤖 You: ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break

                # Process question (basic implementation)
                print(f"\n🤖 Rikugan: Processing '{user_input}'...")

                # This would integrate with Rikugan AI in full implementation
                # For now, provide basic responses
                response = process_basic_question(user_input, context, analyzer)
                print(f"🤖 Rikugan: {response}\n")

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def process_basic_question(question: str, context: dict, analyzer: JadxAnalyzer) -> str:
    """Process basic questions about APK (placeholder for AI integration)."""

    question_lower = question.lower()

    # Entry points
    if 'entry point' in question_lower or 'main activity' in question_lower:
        manifest = context['manifest']
        if manifest.get('activities'):
            main_activity = manifest['activities'][0]
            return f"Main entry point: {main_activity}. This is typically the first activity launched when the app starts."

    # Permissions
    if 'permission' in question_lower:
        manifest = context['manifest']
        permissions = manifest.get('permissions', [])
        if permissions:
            return f"This app requests {len(permissions)} permissions: {', '.join(permissions[:10])}"

    # Network communication
    if 'network' in question_lower or 'http' in question_lower:
        matches = analyzer.search_string_in_sources(
            context['decompiled_dir'],
            "http",
            case_sensitive=False
        )
        if matches:
            return f"Found {len(matches)} network-related code locations. Use 'jadx_search_string' for details."

    # Crypto
    if 'crypto' in question_lower or 'encrypt' in question_lower:
        matches = analyzer.search_string_in_sources(
            context['decompiled_dir'],
            "Cipher",
            case_sensitive=False
        )
        if matches:
            return f"Found {len(matches)} crypto-related code locations. The app uses cryptographic functions."

    # Native libraries
    if 'native' in question_lower or '.so' in question_lower:
        libs = analyzer.find_native_libraries(context['decompiled_dir'])
        if libs:
            return f"This app contains {len(libs)} native libraries: {', '.join(libs)}"

    # Structure overview
    if 'structure' in question_lower or 'overview' in question_lower:
        structure = context['structure']
        return (f"APK contains {structure['total_classes']} classes with {structure['total_methods']} methods. "
                f"Components: {len(structure['activities'])} activities, "
                f"{len(structure['services'])} services, "
                f"{len(structure['receivers'])} receivers, "
                f"{len(structure['providers'])} providers.")

    return "I understand your question, but full AI integration is not yet implemented in CLI mode. Use the specific commands for detailed analysis."


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Rikugan JADX - Android APK Reverse Engineering Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s analyze app.apk -o ./decompiled
  %(prog)s search app.apk "API_KEY" --case-sensitive
  %(prog)s structure app.apk --export structure.json
  %(prog)s class app.apk com.example.MainActivity
  %(prog)s interactive app.apk

For more information, visit: https://github.com/alicangnll/Rikugan
        """
    )

    parser.add_argument(
        "--jadx",
        help="Path to jadx executable (default: search in PATH)"
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze APK structure')
    analyze_parser.add_argument('apk', help='Path to APK file')
    analyze_parser.add_argument('-o', '--output', default='./jadx_output', help='Output directory')
    analyze_parser.add_argument('--no-resources', action='store_true', help='Don\'t export resources')
    analyze_parser.add_argument('--export', help='Export analysis to JSON file')
    analyze_parser.set_defaults(func=cmd_analyze)

    # Search command
    search_parser = subparsers.add_parser('search', help='Search in decompiled sources')
    search_parser.add_argument('apk', help='Path to APK file')
    search_parser.add_argument('search_string', help='String to search for')
    search_parser.add_argument('-o', '--output', default='./jadx_output', help='Output directory')
    search_parser.add_argument('-d', '--decompiled-dir', help='Use existing decompiled directory')
    search_parser.add_argument('--case-sensitive', action='store_true', help='Case-sensitive search')
    search_parser.add_argument('--max-results', type=int, default=50, help='Maximum results to show')
    search_parser.set_defaults(func=cmd_search)

    # Structure command
    structure_parser = subparsers.add_parser('structure', help='Show package structure')
    structure_parser.add_argument('apk', help='Path to APK file')
    structure_parser.add_argument('-o', '--output', default='./jadx_output', help='Output directory')
    structure_parser.add_argument('-d', '--decompiled-dir', help='Use existing decompiled directory')
    structure_parser.add_argument('--export', help='Export structure to JSON file')
    structure_parser.set_defaults(func=cmd_structure)

    # Class command
    class_parser = subparsers.add_parser('class', help='Analyze specific class')
    class_parser.add_argument('apk', help='Path to APK file')
    class_parser.add_argument('class_name', help='Fully qualified class name')
    class_parser.add_argument('-o', '--output', default='./jadx_output', help='Output directory')
    class_parser.add_argument('-d', '--decompiled-dir', help='Use existing decompiled directory')
    class_parser.set_defaults(func=cmd_class)

    # Interactive command
    interactive_parser = subparsers.add_parser('interactive', help='Interactive AI mode')
    interactive_parser.add_argument('apk', help='Path to APK file')
    interactive_parser.add_argument('-o', '--output', default='./jadx_output', help='Output directory')
    interactive_parser.set_defaults(func=cmd_interactive)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
