# Rikugan JADX Plugin

Android APK reverse engineering plugin for Rikugan using JADX decompiler.

## Features

🔥 **Comprehensive APK Analysis:**
- Decompile APKs to Java source code
- Analyze package structure and components
- Parse AndroidManifest.xml
- Search strings in decompiled code
- Find native libraries (.so files)
- Analyze class dependencies
- Security assessment
- Malware analysis

## Installation

### 1. Install JADX

**macOS:**
```bash
brew install jadx
```

**Linux:**
```bash
wget https://github.com/skylot/jadx/releases/download/v1.4.7/jadx-1.4.7.zip
unzip jadx-1.4.7.zip
sudo ln -s $(pwd)/jadx-1.4.7/bin/jadx /usr/local/bin/jadx
```

**Windows:**
```bash
# Download from https://github.com/skylot/jadx/releases
# Extract and add to PATH
```

### 2. Install Rikugan JADX Plugin

```bash
cd /path/to/Rikugan
cp rikugan_jadx.py ~/.local/bin/rikugan-jadx
chmod +x ~/.local/bin/rikugan-jadx
```

## Usage

### Command Line Interface

**Analyze APK:**
```bash
python rikugan_jadx.py analyze app.apk -o ./decompiled
```

**Search for strings:**
```bash
python rikugan_jadx.py search app.apk "API_KEY"
python rikugan_jadx.py search app.apk "http://" --case-sensitive
```

**Show package structure:**
```bash
python rikugan_jadx.py structure app.apk --export structure.json
```

**Analyze specific class:**
```bash
python rikugan_jadx.py class app.apk com.example.app.MainActivity
```

**Interactive mode:**
```bash
python rikugan_jadx.py interactive app.apk
```

### Python API

```python
from rikugan.jadx import JadxAnalyzer

# Initialize analyzer
analyzer = JadxAnalyzer()

# Decompile APK
decompiled_dir = analyzer.decompile_apk("app.apk", "./output")

# Analyze structure
structure = analyzer.get_package_structure(decompiled_dir)
print(f"Total classes: {structure['total_classes']}")

# Parse manifest
manifest = analyzer.find_android_manifest(decompiled_dir)
print(f"Package: {manifest['package']}")
print(f"Permissions: {manifest['permissions']}")

# Search for strings
matches = analyzer.search_string_in_sources(decompiled_dir, "API_KEY")
for match in matches:
    print(f"{match['file']}:{match['line']} - {match['content']}")

# Analyze class
class_info = analyzer.get_class_dependencies(decompiled_dir, "com.example.MainActivity")
print(f"Methods: {class_info['methods']}")

# Find native libraries
native_libs = analyzer.find_native_libraries(decompiled_dir)
print(f"Native libraries: {native_libs}")

# Export analysis
analyzer.export_to_json(decompiled_dir, "analysis.json")
```

## Examples

### Malware Analysis

```bash
# Analyze suspicious APK
python rikugan_jadx.py analyze suspicious.apk -o ./malware_analysis

# Search for C2 domains
python rikugan_jadx.py search suspicious.apk "http://"

# Check permissions
python rikugan_jadx.py structure suspicious.apk

# Find native code
python rikugan_jadx.py class suspicious.apk com.example.NativeLib
```

### Penetration Testing

```bash
# Decompile target app
python rikugan_jadx.py analyze target.apk -o ./target_app

# Find API endpoints
python rikugan_jadx.py search target.apk "api."

# Check for hardcoded secrets
python rikugan_jadx.py search target.apk "password"
python rikugan_jadx.py search target.apk "token"
python rikugan_jadx.py search target.apk "secret"

# Analyze network communication
python rikugan_jadx.py search target.apk "https://"
```

### Reverse Engineering

```bash
# Decompile and analyze
python rikugan_jadx.py analyze app.apk -o ./reversed

# Understand structure
python rikugan_jadx.py structure app.apk

# Analyze main activity
python rikugan_jadx.py class app.apk com.example.app.MainActivity

# Export complete analysis
python rikugan_jadx.py analyze app.apk --export analysis.json
```

## Rikugan Integration

### Using with Rikugan Skills

The JADX plugin includes a built-in skill that can be used within Rikugan:

```
User: /jadx Analyze this APK at /path/to/app.apk
Rikugan: [Decompiles APK and provides comprehensive analysis]

User: /jadx What permissions does this app request?
Rikugan: [Lists permissions and their risk levels]

User: /jadx Find the MainActivity class
Rikugan: [Analyzes MainActivity and shows details]

User: /jadx Search for API endpoints in the code
Rikugan: [Searches and lists found endpoints]
```

## Output Examples

### Structure Analysis

```json
{
  "packages": ["com.example.app", "com.example.app.utils"],
  "activities": ["com.example.app.MainActivity"],
  "services": ["com.example.app.NetworkService"],
  "receivers": ["com.example.app.BootReceiver"],
  "providers": ["com.example.app.DataProvider"],
  "total_classes": 150,
  "total_methods": 2500
}
```

### Manifest Analysis

```json
{
  "package": "com.example.app",
  "version_code": "1",
  "version_name": "1.0.0",
  "min_sdk": "21",
  "target_sdk": "33",
  "permissions": [
    "android.permission.INTERNET",
    "android.permission.ACCESS_FINE_LOCATION"
  ],
  "activities": [
    "com.example.app.MainActivity"
  ]
}
```

## Troubleshooting

### JADX Not Found

```
Error: JADX not found
```

**Solution:**
```bash
# Install JADX
brew install jadx  # macOS
# or download from https://github.com/skylot/jadx/releases

# Or specify path explicitly
python rikugan_jadx.py analyze app.apk --jadx /path/to/jadx
```

### Decompilation Timeout

```
Error: JADX decompilation timed out
```

**Solution:**
- Large APKs may take longer to decompile
- Increase timeout in code if needed
- Use existing decompiled directory with `-d` flag

### Memory Issues

```
Error: Out of memory during decompilation
```

**Solution:**
```bash
# Increase JVM memory for JADX
export JAVA_OPTS="-Xmx4g"
python rikugan_jadx.py analyze large_app.apk
```

## Advanced Usage

### Batch Analysis

```python
from rikugan.jadx import JadxAnalyzer
import json

analyzer = JadxAnalyzer()

apks = ["app1.apk", "app2.apk", "app3.apk"]
results = {}

for apk in apks:
    print(f"Analyzing {apk}...")
    decompiled_dir = analyzer.decompile_apk(apk, f"./output_{Path(apk).stem}")
    results[apk] = analyzer.get_package_structure(decompiled_dir)

# Save combined results
with open("batch_analysis.json", "w") as f:
    json.dump(results, f, indent=2)
```

### Security Assessment

```python
from rikugan.jadx import JadxAnalyzer

analyzer = JadxAnalyzer()
decompiled_dir = analyzer.decompile_apk("app.apk", "./security_analysis")

# Check for security issues
manifest = analyzer.find_android_manifest(decompiled_dir)

# Check debuggable
if manifest.get("debuggable"):
    print("⚠️  WARNING: App is debuggable!")

# Check dangerous permissions
dangerous_perms = [
    "android.permission.SEND_SMS",
    "android.permission.READ_SMS",
    "android.permission.CALL_PHONE"
]

for perm in manifest.get("permissions", []):
    if perm in dangerous_perms:
        print(f"⚠️  DANGEROUS: {perm}")

# Search for hardcoded secrets
secrets = analyzer.search_string_in_sources(decompiled_dir, "password")
if secrets:
    print(f"⚠️  Found {len(secrets)} potential hardcoded passwords")
```

## Requirements

- Python 3.10+
- JADX Decompiler 1.4.7+
- Rikugan framework

## License

MIT License - See main Rikugan project

## Contributing

Contributions welcome! Please open issues or pull requests on GitHub.

## Links

- JADX: https://github.com/skylot/jadx
- Rikugan: https://github.com/alicangnll/Rikugan
- Android Security: https://developer.android.com/topic/security/best-practices

## Author

Created for Rikugan Reverse Engineering Framework by Ali Can Gönüllü
