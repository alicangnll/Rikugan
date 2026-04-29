# Rikugan (六眼)

A reverse-engineering agent for **IDA Pro**, **Binary Ninja**, and **VSCode** that integrates a multi-provider LLM directly into your analysis workflow. This project was vibecoded together with my friend, Claude Code.

![alt text](assets/binja_showcase.png)

![alt text](assets/ida_showcase.png)

[Documentation](https://rikugan.reversing.codes/docs.html) | [Architecture](https://rikugan.reversing.codes/ARCHITECTURE.html) | [Issues](https://github.com/alicangnll/Rikugan/issues)

## 🚀 Quick Start

### Accessing Rikugan from Different Interfaces

**IDA Pro:**
- Press `Ctrl+Shift+I` (Windows/Linux) or `Cmd+Shift+I` (macOS)
- Or navigate to: `Edit → Plugins → Rikugan`
- Chat panel appears in the IDA UI

**Binary Ninja:**
- Press `Ctrl+Shift+I` (Windows/Linux) or `Cmd+Shift+I` (macOS)
- Or navigate to: `Tools → Rikugan → Open Chat`
- Chat panel appears in the Binary Ninja UI

**VSCode Extension:**
- Press `Ctrl+Shift+I` (Windows/Linux) or `Cmd+Shift+I` (macOS)
- Or use the Command Palette: `Ctrl+Shift+P` → "Rikugan: Open Chat"
- Right-click on code → "Ask Rikugan"
- Sidebar chat interface integrated with VSCode

**CLI Mode:**
```bash
# Standalone CLI mode
rikugan-cli --help

# Analyze binary directly
rikugan-cli analyze /path/to/binary

# Interactive chat mode
rikugan-cli chat
```

**JADX CLI (Android APK Analysis):**
```bash
# Analyze Android APKs with JADX integration
python rikugan_jadx.py analyze app.apk -o ./decompiled

# Search for strings in decompiled code
python rikugan_jadx.py search app.apk "API_KEY"

# Show package structure
python rikugan_jadx.py structure app.apk

# Analyze specific class
python rikugan_jadx.py class app.apk com.example.MainActivity

# Interactive AI mode for APK analysis
python rikugan_jadx.py interactive app.apk
```

## Install

Auto-detects IDA Pro, Binary Ninja, or both.

**Linux / macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/alicangnll/Rikugan/main/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/alicangnll/Rikugan/main/install.ps1 | iex
```

For host-specific install, manual setup, and configuration, see the [docs](https://rikugan.reversing.codes/docs.html).

## Is this another MCP client?

No, Rikugan is an ***agent*** built to live inside your RE host. It does not consume an MCP server to interact with the host database; it has its own agentic loop, context management, role prompt ([source](rikugan/agent/system_prompt.py)), and an in-process tool orchestration layer.

The agent loop is a generator-based turn cycle: each user message kicks off a stream→execute→repeat pipeline where the LLM response is streamed token-by-token and tool calls are intercepted and dispatched. It supports automatic error recovery, mid-run user questions, plan mode for multi-step workflows, and message queuing — all without leaving the disassembler.

The agent really ***lives*** and ***breathes*** reversing.

- No need to switch to an external MCP client
- Assistant-first, not designed to do your job (unless you ask it to)
- Extensible to many LLM providers and local installations (Ollama)
- Quick to enable — just hit Ctrl+Shift+I and the chat will appear

## Features

**60+ tools** covering navigation, decompiler, disassembly, cross-references, strings, annotations, types, scripting, and host-specific IL/microcode manipulation. The agent always asks permission before running scripts and will never execute the target binary. Full tool reference in the [docs](https://rikugan.reversing.codes/docs.html).

**🔥 NEW: Advanced Memory Corruption & Exploitation Analysis** — v1.2.5+!

The enhanced **Memory Corruption** skill provides comprehensive coverage of modern binary exploitation and mitigation bypass techniques:

- **Out-of-Bounds (OOB) Exploitation** — Array bounds detection, info leaks, corruption chains
- **Use-After-Free (UAF)** — Vtable hijacking, function pointer overwrite, partial overwrite
- **PAC Bypass** — Pointer Authentication Code bypass on ARM64 (iOS, Android)
- **ASLR Bypass** — Address Space Layout Randomization bypass via info leaks, partial overwrite
- **CFI Bypass** — Control Flow Integrity bypass with compatible gadgets
- **CET/Shadow Stack** — Control-flow Enforcement Technology bypass
- **MTE Bypass** — Memory Tagging Extension bypass on Android 14+
- **Remote Code Execution (RCE)** — Network-based exploitation and remote shell techniques
- **Kernel Exploitation** — Kernel-mode exploitation with SMEP/SMAP/KPTI bypass
- **ROP Chain Building** — Automatic ROP gadget discovery and chain construction
- **Modern Mitigation Matrix** — 14+ mitigation bypass strategies with quick reference

**Supported Exploitation Scenarios:**
- ARM64 iOS exploitation with PAC (iPhone 12+)
- Modern Linux with Full RELRO, PIE, Canaries, NX, ASLR
- Windows CFG/CET/ASLR bypass
- Android MTE+PAC exploitation (Android 14+)
- Remote network exploitation with ASLR bypass
- Kernel exploitation with SMEP/SMAP/KPTI

**Advanced Decompilation Integration** — New in v1.2.5! Smart analysis tools that understand your binary:

- **Cross-Reference Visualizer** — Interactive call graphs with complexity metrics and path finding
- **Smart Function Naming** — AI-powered pattern recognition suggests meaningful names for `sub_XXX` functions
- **Type Library Auto-Detection** — Automatically detects platform (Windows/Linux) and recovers structure definitions
- **Code Bookmarking** — Mark important locations with categories, tags, and notes
- **Advanced Search** — Find similar functions using Jaccard similarity, search by patterns/strings/imports

**Exploration** — Inspired by how code agents work, but applied to binaries. The orchestrator maps the binary (imports, exports, strings, key functions), then spawns isolated subagents to analyze in parallel. Each reports back, and the orchestrator synthesizes a complete picture.

|![alt text](assets/subagents_example_3.png)|
|:--:|
|Orchestrator spawning subagents in parallel|

**Natural Language Patches** (Experimental) — `/modify` lets you describe what you want changed in plain English. Rikugan explores the binary, builds context, and applies the patches.

|![alt text](assets/maze_solve.gif)|
|:--:|
|`/modify make this maze game easy, let me pass through walls`|

**Deobfuscation** (Experimental, Binary Ninja) — The `/deobfuscation` skill activates plan mode to recognize and remove control flow flattening, opaque predicates, MBA expressions, and junk code using IL read/write primitives.

|![](assets/cff_remove_example.gif)|
|:--:|
|~3x speed of the workflow, original process took ~4:30 min|

**🔥 NEW: JADX Integration - Android APK Analysis** — v1.2.5+!

Comprehensive Android APK reverse engineering with JADX decompiler integration:

- **APK Decompilation** — Automatic decompilation to Java source code using JADX
- **Package Structure Analysis** — Complete package hierarchy, component detection, class/method counting
- **Manifest Parsing** — Extract permissions, components, version info, SDK requirements
- **String Search** — Search decompiled Java sources for API keys, endpoints, credentials
- **Class Analysis** — Analyze dependencies, methods, fields, inheritance hierarchy
- **Native Library Detection** — Find and analyze .so files across different architectures
- **Security Assessment** — Detect debuggable builds, hardcoded secrets, insecure storage
- **Malware Analysis** — Identify suspicious permissions, C2 communication, obfuscation techniques

**CLI Usage:**
```bash
# Analyze APK structure
python rikugan_jadx.py analyze app.apk -o ./decompiled

# Search for API endpoints
python rikugan_jadx.py search app.apk "http://"

# Analyze specific class
python rikugan_jadx.py class app.apk com.example.MainActivity

# Interactive AI mode
python rikugan_jadx.py interactive app.apk
```

**Skill Integration:**
```
/jadx Analyze this APK at /path/to/app.apk
/jadx What permissions does this app request?
/jadx Find the MainActivity class
/jadx Search for hardcoded API keys
/jadx Check for native libraries
```

**Memory** — Findings are saved to `RIKUGAN.md` next to your database, persisting across sessions.

**Skills & MCP** — 42+ total skills (33 built-in + 9 external), custom skill support, and MCP server integration. Reuse skills and MCP servers from Claude Code and Codex. 

**Latest Skills (v1.2.5+):**
- **Memory Corruption & Mitigation Bypass** — Comprehensive coverage of UAF, OOB, PAC, ASLR, CFI, CET, MTE exploitation
- **Reverse Engineering** — Binary analysis, decompilation, assembly understanding
- **Protocol Analysis** — Network protocol reverse engineering and parsing
- **Crypto Analysis** — Cryptographic algorithm identification and analysis
- **Firmware RE** — Firmware extraction, analysis, and exploitation
- **Web App Security** — Web application vulnerability analysis
- **Binary Exploitation** — OOB, UAF, stack overflow, heap exploitation techniques
- **Kernel Exploit** — Kernel-mode exploitation and privilege escalation
- **ROP Builder** — Automatic ROP chain construction and DEP bypass
- **Android/iOS Exploit** — Mobile platform exploitation techniques
- **Auto Exploit** — Automated exploit generation
- **Malware Analysis** — Malware analysis and reverse engineering
- **CTF Tools** — CTF competition utilities and exploit helpers

**All Built-in Skills:**
```
android-exploit, app-shielding-bypass, auto-exploit, automated-exploit-gen,
binja-scripting, cloud-mobile-security, crypto-analysis, ctf, deobfuscation,
driver-analysis, firmware-re, generic-re, ida-scripting, ios-exploit,
jadx-analysis, (NEW! Android APK reverse engineering)
kernel-exploit, linux-malware, malware-analysis, memory-corruption, (Enhanced)
mobile-malware-analysis, mobile-pentest, modify, protocol-analysis,
race-condition, reverse-engineering, rop-builder, shellcode-generator,
smart-patch-binja, smart-patch-ida, vuln-audit, web-app-security
```

**External Skill Integration:**
- **Claude Code Skills** — Auto-import from `~/.claude/skills/`
- **MCP Servers** — Connect to external MCP servers for extended capabilities
- **Custom Skills** — Create your own skills with custom tools and workflows
- **Codex Skills** — Import skills from Codex editors

### Interface Integration Details

**IDA Pro Integration:**
- Native IDA plugin with Qt-based chat interface
- Direct access to IDA API (IDA, IDA Python, Hex-Rays)
- Real-time disassembly and decompilation analysis
- Cross-reference navigation and visualization
- Function renaming and annotation tools
- Script execution with safety prompts
- Memory view and structure analysis
- IDA database persistence

**Binary Ninja Integration:**
- Native Binary Ninja plugin with UI chat panel
- Direct access to Binary Ninja API (BNIL, LLIL, MLIL)
- Advanced IL manipulation and analysis
- Cross-reference visualization and graph views
- Binary database modification and patching
- Type library integration and recovery
- Function analysis and naming
- Binary Ninja cloud collaboration support

**VSCode Extension:**
- VSCode native extension with sidebar chat
- Right-click context menu integration
- Code selection analysis
- Multi-language support (C++, Python, Assembly, etc.)
- File-based analysis workflow
- Git integration and diff analysis
- Terminal integration and command execution
- Workspace-aware context management

**CLI Mode:**
- Standalone binary analysis without GUI
- Batch processing and automation
- Scriptable workflows
- Integration with CI/CD pipelines
- Headless operation for servers
- Multi-binary batch analysis
- Report generation in multiple formats

## Configuration & Setup

**Provider Configuration:**
```bash
# Claude (Recommended)
export ANTHROPIC_API_KEY="your-key"

# OpenAI-compatible
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"

# Ollama (Local)
export OLLAMA_BASE_URL="http://localhost:11434"

# Custom provider
export CUSTOM_API_KEY="your-key"
export CUSTOM_BASE_URL="https://your-endpoint.com/v1"
```

**MCP Server Integration:**
```json
// ~/.rikugan/mcp_servers.json
{
  "servers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"]
    }
  }
}
```

**Custom Skills:**
```bash
# Create custom skill directory
mkdir -p ~/.rikugan/skills/my-skill

# Add skill.md
cat > ~/.rikugan/skills/my-skill/skill.md << 'EOF'
---
name: My Custom Skill
description: Custom analysis workflow
tags: [custom, analysis]
---
Task: Custom analysis task.
EOF
```

**Profile Customization:**
```json
// ~/.rikugan/profiles/restricted.json
{
  "name": "restricted",
  "description": "Limited tool access",
  "allowed_tools": ["decompile_function", "get_disasm"],
  "data_filters": {
    "exclude_strings": true,
    "exclude_imports": false
  }
}
```

## Usage Examples

**Basic Reverse Engineering:**
```
User: Analyze this binary and find the main functionality
Rikugan: [Explores binary, maps imports/exports, analyzes key functions]

User: What does the function at 0x401000 do?
Rikugan: [Decompiles function, explains logic, identifies algorithms]

User: Rename all crypto functions based on their purpose
Rikugan: [Identifies crypto functions, suggests meaningful names]
```

**Vulnerability Analysis:**
```
User: Check for memory corruption vulnerabilities
Rikugan: [Activates memory-corruption skill, scans for dangerous functions]

User: Analyze this buffer overflow at 0x402000
Rikugan: [Activates binary-exploit skill, builds exploitation chain]

User: Can this binary be exploited on modern Linux?
Rikugan: [Checks mitigations, suggests bypass strategies]
```

**Malware Analysis:**
```
User: What type of malware is this?
Rikugan: [Activates malware-analysis skill, classifies malware family]

User: Find the C2 communication code
Rikugan: [Locates network functions, decodes C2 protocol]

User: Extract the configuration
Rikugan: [Identifies config structures, decodes encrypted data]
```

## Recommended Providers

| Provider | Notes |
|----------|-------|
| **Claude Opus 4.6** | Best overall. Recommend Claude Pro/Max plan with OAuth over API. |
| **Claude Sonnet 4.6** | Strong at lower cost. Both Anthropic models use prompt caching. |
| **MiniMax M2.5 / Highspeed** | On par with Opus in local tests. Generous limits, low cost. |
| **Gemini 2.5 / 3 / 3.1 Pro** | Solid results. Hallucinates more than Anthropic/MiniMax. |
| **Kimi 2.5** | Strong coding, but lacks rigor for complex RE tasks. |
| **LLAMA 70B / GPT 120B OSS** | Interesting but not production-ready for RE. |

Also supports any OpenAI-compatible endpoint and Ollama for local models.

## Keyboard Shortcuts

**Global Shortcuts (All Interfaces):**
- `Ctrl+Shift+I` / `Cmd+Shift+I` — Open Rikugan chat
- `Esc` — Close chat panel (in most interfaces)
- `Ctrl+Enter` — Send message

**IDA Pro Specific:**
- `Edit → Plugins → Rikugan` — Menu access
- `Alt+T` — Focus chat input (when chat is open)
- `Ctrl+Tab` — Switch between IDA and chat

**Binary Ninja Specific:**
- `Tools → Rikugan → Open Chat` — Menu access
- `Ctrl+Shift+R` — Quick analysis of current function
- `Ctrl+Shift+D` — Decompile and explain current function

**VSCode Extension:**
- `Ctrl+Shift+P` → "Rikugan: Open Chat" — Command palette
- `Right-click → Ask Rikugan` — Context menu
- `Ctrl+Shift+A` — Analyze selected code
- `Ctrl+Shift+E` — Explain selected function

## Tips & Tricks

**Performance Optimization:**
```
1. Use prompt caching — Anthropic models cache automatically
2. Limit context window — Reduce "max_tokens" for faster responses
3. Batch similar queries — Combine related questions
4. Use profiles — Restrict tools for faster analysis
5. Local models — Use Ollama for offline analysis
```

**Best Practices:**
```
1. Start with exploration — Let Rikugan map the binary first
2. Use plan mode — For complex multi-step workflows
3. Leverage memory — Important findings persist across sessions
4. Combine skills — Use multiple skills for comprehensive analysis
5. Verify suggestions — Always verify AI-generated analysis
```

**Advanced Workflows:**
```
# Automated vulnerability assessment
User: /skill vuln-audit
Rikugan: [Scans binary, identifies potential vulnerabilities]

# Custom exploitation chain
User: /skill memory-corruption
User: Find OOB vulnerabilities and build RCE exploit
Rikugan: [Activates skill, finds bugs, builds exploitation chain]

# Batch analysis
User: Analyze all functions in this binary
Rikugan: [Spawns subagents, parallel analysis, comprehensive report]

# Protocol reverse engineering
User: /skill protocol-analysis
User: Decode this network protocol
Rikugan: [Identifies protocol structure, builds parser]
```

## Troubleshooting

**Common Issues:**

**Plugin not appearing in IDA/Binary Ninja:**
```bash
# Check installation
rikugan-doctor --check-install

# Reinstall plugin
rikugan-install --force

# Check Python compatibility
python --version  # Should be 3.10+
```

**API connection issues:**
```bash
# Test API key
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY"

# Check proxy settings
echo $HTTP_PROXY
echo $HTTPS_PROXY

# Test with direct endpoint
export ANTHROPIC_BASE_URL="https://api.anthropic.com"
```

**Performance issues:**
```bash
# Clear cache
rm -rf ~/.rikugan/cache/*

# Reduce context size
# In settings.json: "max_context_tokens": 8192

# Use faster model
export RIKUGAN_DEFAULT_MODEL="claude-sonnet-4-6"
```

**Memory/context issues:**
```bash
# Increase memory limit
export RIKUGAN_MAX_MEMORY="4096"

# Use streaming mode
export RIKUGAN_STREAMING=true

# Enable prompt caching
export RIKUGAN_PROMPT_CACHING=true
```

## Requirements

- IDA Pro 9.0+ with Hex-Rays decompiler or Binary Ninja (UI mode)
- Python 3.10+
- At least one LLM provider
- Windows, macOS, or Linux

> **IDA Pro + Python >= 3.14:** Shiboken has a known UAF bug. Rikugan includes a workaround, but Python 3.10 is still the safest choice. See the [upstream report](https://community.hex-rays.com/t/ida-9-3-b1-macos-arm64-uaf-crash/646).

## Roadmap

**Near-term (v1.3.x):**
- [ ] Enhanced deobfuscation with ML-based pattern recognition
- [ ] Automated exploit generation with symbolic execution
- [ ] Advanced kernel analysis capabilities
- [ ] Mobile app analysis improvements (iOS/Android)
- [ ] Firmware analysis pipeline enhancements

**Mid-term (v1.4.x):**
- [ ] Multi-binary analysis workflow
- [ ] Collaborative analysis features
- [ ] Enhanced visualization and graphing
- [ ] Integration with more disassemblers (Ghidra, Radare2)
- [ ] Cloud-based analysis options

**Long-term:**
- [ ] Community skill marketplace
- [ ] Plugin system for custom tools
- [ ] Advanced ML-based vulnerability detection
- [ ] Real-time collaboration features
- [ ] Enterprise deployment options

## Contributing

Contributions are welcome! Areas where you can help:

**Skills Development:**
- Create new analysis skills
- Improve existing skill coverage
- Add platform-specific techniques
- Share custom workflows

**Bug Reports & Feature Requests:**
- [Open an issue](https://github.com/alicangnll/Rikugan/issues) for bugs
- Suggest new features or improvements
- Share interesting use cases
- Report documentation issues

**Code Contributions:**
- Fork the repository
- Create a feature branch
- Make your changes with tests
- Submit a pull request

**Documentation:**
- Improve documentation
- Add examples and tutorials
- Translate documentation
- Create video tutorials

## Community & Support

**Getting Help:**
- [Documentation](https://rikugan.reversing.codes/docs.html)
- [GitHub Issues](https://github.com/alicangnll/Rikugan/issues)
- [Discord Community](https://discord.gg/rikugan) (coming soon)

**Showcase:**
- Share your analysis workflows
- Post interesting findings
- Demonstrate new techniques
- Contribute to skill library

**Stay Updated:**
- ⭐ Star the repository on GitHub
- 👀 Watch for releases and updates
- 🐦 Follow [@rikugan_re](https://twitter.com/rikugan_re) for news
- 📧 Subscribe to updates at [rikugan.reversing.codes](https://rikugan.reversing.codes)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Claude Code** — For being an amazing pair programmer and friend
- **Anthropic** — For building incredible AI models that make this possible
- **Binary Ninja Team** — For the excellent API and support
- **Hex-Rays** — For IDA Pro and the powerful Hex-Rays decompiler
- **Community** — For feedback, testing, and contributions

Special thanks to everyone who provided feedback, reported bugs, and suggested improvements during the development process.

## Conclusion

If you'd asked me last year what I thought about AI doing reverse engineering, I'd probably have said something like "Nah, impossible — it hallucinates, and reverse engineering is not something as simple as writing code." But this year I completely changed my mind when I saw what was achievable. AI is not the ChatGPT from 2023 anymore; it's something entirely different.

For that reason, I decided to invest this year in researching this topic. It's amazing what we can build with agentic coding — it's surreal how quickly I'm learning topics that I simply "didn't have time" to study before.

Rikugan is just one of many projects I've built in the last three months. The first version was built in a single night. Within two days it already supported both IDA and Binary Ninja. Within three days, it was essentially what you see here, with only minor tweaks since.

This is a work in progress with many areas for improvement. I took care to ensure this wouldn't be another AI slop project, but I'm certain there is still room to grow. I hope you use it for good. If you find bugs, have suggestions, or want quality-of-life improvements, please open an issue.

That's all — thanks.

---

**Made with ❤️ and 🔥 by [Ali Can Gönüllü](https://github.com/alicangnll)**

*"The future of reverse engineering is automated, intelligent, and accessible to everyone."*
