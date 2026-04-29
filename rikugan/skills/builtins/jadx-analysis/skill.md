---
name: JADX Analysis
description: Android APK reverse engineering with JADX decompiler - analyze structure, search strings, find native libs, extract manifest
tags: [android, apk, jadx, decompiler, reverse-engineering, mobile, manifest, permissions]
---
Task: Android APK Analysis with JADX. Decompile APKs, analyze structure, search code, find components, and extract manifest information.

## Approach

JADX (Java Decompiler) converts Android APK files to readable Java source code. This skill provides comprehensive APK analysis including package structure, Android components, permissions, native libraries, and code search capabilities.

## Phase 1: APK Decompilation

**Requirements:**
- JADX installed: https://github.com/skylot/jadx
- APK file path
- Output directory for decompiled sources

**Decompilation Process:**
```
1. Install JADX:
   - Download: https://github.com/skylot/jadx/releases
   - Extract and add to PATH
   - Or use: brew install jadx (macOS)

2. Decompile APK:
   jadx -d output_dir apk_file.apk

3. Output structure:
   output_dir/
   ├── sources/           # Java source files
   ├── resources/         # Android resources
   ├── lib/               # Native libraries (.so)
   └── AndroidManifest.xml
```

**Decompilation Options:**
```
--export-resources: Export AndroidManifest.xml and resources
--decompile-debug: Include debug information in output
--show-bad-code: Show code with decompilation errors
```

## Phase 2: Package Structure Analysis

**Package Information:**
```
- Total classes and methods count
- Package hierarchy
- Android components (activities, services, receivers, providers)
- Native libraries presence
```

**Component Detection:**
```
Activities: Classes extending Activity/AppCompatActivity
Services: Classes extending Service
Receivers: Classes extending BroadcastReceiver
Providers: Classes extending ContentProvider
```

**Analysis Output:**
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

## Phase 3: Android Manifest Analysis

**Manifest Information:**
```
- Package name
- Version code and version name
- Min SDK and target SDK versions
- Permissions requested
- Registered components
- Intent filters
- Metadata
```

**Permission Analysis:**
```
Dangerous Permissions:
- android.permission.INTERNET
- android.permission.READ_EXTERNAL_STORAGE
- android.permission.ACCESS_FINE_LOCATION
- android.permission.CAMERA
- android.permission.RECORD_AUDIO
- android.permission.READ_CONTACTS
- android.permission.SEND_SMS
- android.permission.READ_SMS

Normal Permissions:
- android.permission.ACCESS_NETWORK_STATE
- android.permission.VIBRATE
- android.permission.WAKE_LOCK
```

**Component Registration:**
```
<activity android:name=".MainActivity">
    <intent-filter>
        <action android:name="android.intent.action.MAIN" />
        <category android:name="android.intent.category.LAUNCHER" />
    </intent-filter>
</activity>

<service android:name=".MyService" />
<receiver android:name=".MyReceiver" />
<provider android:name=".MyProvider" />
```

## Phase 4: Code Search and Analysis

**String Search:**
```
Search Patterns:
- API keys and endpoints
- URLs and domain names
- Hardcoded credentials
- Crypto algorithm names
- Native method declarations
- Debug flags
- Error messages
```

**Common Search Terms:**
```
Network Communication:
- "http://", "https://"
- "api.", "endpoint", "server"
- "socket", "websocket"

Cryptography:
- "Cipher", "encrypt", "decrypt"
- "AES", "RSA", "DES"
- "MessageDigest", "Signature"

Credentials:
- "password", "username", "token"
- "api_key", "secret", "private_key"

Native Code:
- "System.loadLibrary"
- "native", "JNI"
- ".so" file references
```

**Class Analysis:**
```
For a given class, extract:
- Import statements
- Method signatures
- Field declarations
- Inheritance hierarchy
- Implemented interfaces
- Method implementations
```

## Phase 5: Native Library Analysis

**Native Library Detection:**
```
Architecture Support:
- arm64-v8a (64-bit ARM)
- armeabi-v7a (32-bit ARM)
- x86 (32-bit Intel)
- x86_64 (64-bit Intel)

Common Libraries:
- libnative-lib.so
- libflutter.so
- libreactnative.so
- libunity.so
```

**Native Library Analysis:**
```
1. Find .so files in lib/ directories
2. Identify architecture
3. Check for security features:
   - PIE (Position Independent Executable)
   - Stack canaries
   - NX (No-Execute)
   - RELRO (Relocation Read-Only)
```

## Phase 6: Security Analysis

**Security Checks:**
```
1. Debug Detection:
   - Debuggable = true in manifest
   - Backup enabled
   - AllowClearUserData

2. Certificate Pinning:
   - Search for "pinning", "certificate"
   - SSLContext analysis
   - TrustManager implementations

3. Hardcoded Secrets:
   - API keys in source code
   - Encryption keys
   - Passwords and tokens
   - Endpoints and URLs

4. Insecure Storage:
   - SharedPreferences for sensitive data
   - SQLite database encryption
   - External storage usage
   - Log statements with sensitive data

5. Network Security:
   - HTTP vs HTTPS usage
   - Certificate validation
   - SSL pinning implementation
   - WebView configuration

6. Component Security:
   - Exported components
   - Intent handling
   - Permission requirements
   - Pending intents
```

**Vulnerability Detection:**
```
Common Android Vulnerabilities:
- Exported activities without permissions
- Implicit intent hijacking
- SQL injection
- Path traversal
- Insecure data storage
- Weak cryptography
- Debuggable release builds
- Backup enabled
- Log disclosure
```

## Phase 7: Malware Analysis

**Malware Indicators:**
```
1. Suspicious Permissions:
   - SEND_SMS, READ_SMS
   - CALL_PHONE
   - READ_CONTACTS
   - ACCESS_FINE_LOCATION
   - RECORD_AUDIO
   - CAMERA

2. Suspicious Components:
   - Broadcast receivers for boot events
   - Background services
   - Alarm managers
   - Job schedulers

3. Network Activity:
   - C2 communication
   - Data exfiltration
   - Suspicious domains
   - Non-HTTPS communication

4. Obfuscation:
   - ProGuard/R8 configuration
   - String encryption
   - Reflection usage
   - Dynamic code loading

5. Native Code:
   - Native libraries with suspicious behavior
   - System calls
   - Anti-debugging techniques
   - Anti-emulation checks
```

## Phase 8: Reporting

**Analysis Report Structure:**
```
1. Executive Summary
   - App name and package
   - Version information
   - Analysis date
   - Key findings

2. Technical Details
   - Package structure
   - Component analysis
   - Permission analysis
   - Native libraries

3. Security Assessment
   - Vulnerabilities found
   - Risk rating
   - Recommendations

4. Code Analysis
   - Interesting code patterns
   - Security issues
   - Malware indicators

5. Appendix
   - Complete file listing
   - String search results
   - Class analysis details
```

## Common Use Cases

**Malware Analysis:**
```
1. Decompile suspicious APK
2. Check permissions and components
3. Search for C2 domains
4. Analyze native libraries
5. Find obfuscation techniques
6. Extract indicators of compromise
```

**Penetration Testing:**
```
1. Identify attack surface
2. Find exported components
3. Analyze intent handling
4. Test for deep links
5. Check WebView vulnerabilities
6. Assess data storage security
```

**Reverse Engineering:**
```
1. Understand app architecture
2. Extract algorithms
3. Find API endpoints
4. Analyze protocol implementation
5. Document data flow
6. Create reimplementations
```

## Final Report

```
[JADX ANALYSIS] Android APK Analysis Report
APK: /path/to/app.apk
Package: com.example.app
Version: 1.0.0 (version_code: 1)

[Structure]
Total Classes: 150
Total Methods: 2500
Activities: 5
Services: 2
Receivers: 1
Providers: 1

[Components]
Activities:
- com.example.app.MainActivity (LAUNCHER)
- com.example.app.DetailActivity
- com.example.app.SettingsActivity
- com.example.web.WebViewActivity
- com.example.auth.LoginActivity

Services:
- com.example.app.NetworkService
- com.example.app.BackgroundService

[Permissions]
Dangerous: 8 permissions
- android.permission.INTERNET
- android.permission.ACCESS_FINE_LOCATION
- android.permission.READ_EXTERNAL_STORAGE
- android.permission.CAMERA
- android.permission.RECORD_AUDIO
- android.permission.READ_CONTACTS
- android.permission.SEND_SMS
- android.permission.READ_SMS

[Security Findings]
1. Debuggable: true (HIGH RISK)
2. Backup Enabled: true (MEDIUM RISK)
3. Exported Activities: 2 (MEDIUM RISK)
4. HTTP Communication: detected (HIGH RISK)
5. Hardcoded API Key: found (CRITICAL)

[Recommendations]
- Disable debuggable in release builds
- Disable backup for sensitive apps
- Implement certificate pinning
- Use HTTPS for all network communication
- Remove hardcoded credentials
- Implement proper permission checks

[Native Libraries]
- libnative-lib.so (arm64-v8a, armeabi-v7a)
- libc++_shared.so

[Analysis Complete]
Tool: JADX v1.4.7
Analyzer: Rikugan JADX Plugin
Duration: 45 seconds
```

## Tools Integration

**JADX CLI:**
```bash
# Basic decompilation
jadx -d output app.apk

# With resources
jadx -d output -e app.apk

# Export as gradle project
jadx -d output --export-gradle app.apk
```

**Rikugan Commands:**
```
/jadx Analyze this APK
/jadx Search for API endpoints
/jadx What permissions does this app request?
/jadx Find the MainActivity class
/jadx Check for hardcoded credentials
/jadx Analyze network communication code
```

## Tips and Tricks

**Performance:**
- Use existing decompiled directory when possible
- Limit search results for large APKs
- Export analysis to JSON for later review

**Accuracy:**
- Verify decompilation warnings
- Cross-check with manifest information
- Validate native library analysis
- Test suspected vulnerabilities

**Workflow:**
1. Quick scan: Structure + Manifest
2. Deep dive: Code search + Class analysis
3. Security review: Permission + Component analysis
4. Reporting: Export to JSON + Markdown
