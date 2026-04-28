---
name: Application Shielding Bypass
description: Bypass application protections — root/JB detection, SSL pinning, anti-debug, obfuscation
tags: [bypass, shielding, protection, anti-tamper, root, jailbreak]
---
Task: Application Shielding Bypass. Defeat security controls and protections in mobile/desktop applications.

## Phase 1: Root/Jailbreak Detection Bypass

**Android Root Detection Bypass**
```
Common checks:
1. su binary: which su
2. Superuser app: com.noshufou.android.su
3. Root management apps: com.koushikdutta.superuser
4. System properties: getprop ro.secure
5. Build tags: getprop ro.build.tags
6. Dangerous properties: ro.debuggable
7. Test keys: /system/app/Superuser.apk
8. Mounted /system: mount | grep /system
9. Writable /system: touch /system/test
10. Root cloaking apps

Bypass techniques:

1. Hook detection methods (Frida):
Java.perform(function() {
    var RootBeer = Java.use("com.scottyab.rootbeer.RootBeer");
    RootBeer.isRooted.implementation = function() {
        return false; // Always return not rooted
    };
});

2. Patch APK:
- Smali code modification
- Remove root checks
- Rebuild and sign

3. Magisk Hide:
- Magisk modules to hide root
- Denylist custom apps
- Systemless root

4. Environment spoofing:
- Hide su binary
- Remove root apps from package list
- Modify build properties
```

**iOS Jailbreak Detection Bypass**
```
Common checks:
1. Cydia/Sileo installation
2. Cydia URL scheme: cydia://
3. Fork() system call (jailbreak enables fork)
4. Symbolic links: /Applications, /var/mobile
5. Write access: /private/var
6. Dyld injection: dyld_image_add
7. Jailbreak files: /bin/sh, /bin/bash
8. Filesystem layout
9. SSH daemon
10. Substrate/Cydia Substrate

Bypass techniques:

1. Hook detection (Frida):
if (ObjC.available) {
    var JailbreakDetection = ObjC.classes.JailbreakDetection;
    JailbreakDetection["- isJailbroken"].implementation = function() {
        return false;
    };
}

2. Cycript:
cycript -r com.victim.app
cy# [[JailbreakDetection sharedInstance] isJailbroken] = NO

3. Substrate tweak:
%hook JailbreakDetection
- (BOOL)isJailbroken {
    return NO;
}
%end

4. Environment spoofing:
- Hide Cydia/Sileo icons
- Remove jailbreak tweaks
- Patch filesystem checks
- Hide symbolic links
```

## Phase 2: SSL Pinning Bypass

**Android SSL Pinning Bypass**
```
Common implementations:
1. Network Security Configuration
2. OkHttp certificate pinner
3. TrustManager implementation
4. Certificate pinning in code

Bypass techniques:

1. Frida script (universal):
Java.perform(function() {
    var TrustManager = Java.use("javax.net.ssl.TrustManager");
    var SSLContext = Java.use("javax.net.ssl.SSLContext");
    
    // Bypass all certificate validation
    var TrustManagerClass = Java.use("javax.net.ssl.X509TrustManager");
    var TrustManagers = [TrustManagerClass.$new()];
    
    var SSLContextClass = Java.use("javax.net.ssl.SSLContext");
    var MySSLContext = SSLContextClass.getInstance("TLS");
    MySSLContext.init(null, TrustManagers, null);
});

2. Frida script (OkHttp):
Java.perform(function() {
    var CertificatePinner = Java.use("okhttp3.CertificatePinner");
    CertificatePinner.check.overload("java.lang.String", "java.util.List").implementation = function() {
        // Do nothing, bypass check
    };
});

3. APK modification:
- Remove certificate pinning code
- Modify TrustManager
- Add Burp certificate
- Rebuild and sign

4. Custom ROM:
- Add user certificate to system store
- Modify certificate validation
- Disable SSL pinning system-wide
```

**iOS SSL Pinning Bypass**
```
Common implementations:
1. NSURLSession delegate methods
2. AFNetworking pinning
3. Custom certificate validation
4. Certificate Transparency

Bypass techniques:

1. Frida script (iOS SSL Kill Switch):
if (ObjC.available) {
    try {
        var NSURLSessionDelegate = ObjC.protocols.NSURLSessionDelegate;
        var delegate = ObjC.classes.NSURLSessionDelegate;
        
        // Bypass all SSL validation
        var method = delegate["- URLSession:didReceiveChallenge:completionHandler:"];
        if (method) {
            Interceptor.attach(method.implementation, {
                onEnter: function(args) {
                    var completionHandler = new ObjC.Block(args[3]);
                    var credBlock = ObjC.classes.NSURLCredential.credentialForTrust_(args[2]);
                    completionHandler.implementation(0, credBlock);
                }
            });
        }
    } catch(e) {
        console.log("Error: " + e);
    }
}

2. Cycript:
cycript -r com.victim.app
cy# [[NSURLCredential alloc] initWithTrust:challenge.protectionSpace.serverTrust]

3. Substrate tweak:
%hook NSURLSessionDelegate
- (void)URLSession:(NSURLSession *)session didReceiveChallenge:(NSURLAuthenticationChallenge *)challenge completionHandler:(void (^)(NSURLSessionAuthDisposition, NSURLCredential *))completionHandler {
    completionHandler(0, [NSURLCredential credentialForTrust:challenge.protectionSpace.serverTrust]);
}
%end

4. Burp certificate:
- Install Burp CA on device
- Trust certificate
- Use proxy
```

## Phase 3: Anti-Debug Bypass

**Android Anti-Debug Bypass**
```
Common checks:
1. Debug.isDebuggerConnected()
2. Debug.waitingForDebugger()
3. android:debuggable in manifest
4. Timing checks
5. ptrace() self-tracing
6. Application flags
7. JDWP checks
8. Stack trace analysis

Bypass techniques:

1. Hook Debug class (Frida):
Java.perform(function() {
    var Debug = Java.use("android.os.Debug");
    Debug.isDebuggerConnected.implementation = function() {
        return false;
    };
    Debug.waitingForDebugger.implementation = function() {
        return false;
    };
});

2. Patch manifest:
- Remove android:debuggable="true"
- Remove debugging code
- Rebuild APK

3. Timing attack bypass:
- Slow down execution
- Hook time calls
- Normalize timing

4. Self-ptrace bypass:
- Ignore ptrace result
- Hook ptrace calls
- Patch binary
```

**iOS Anti-Debug Bypass**
```
Common checks:
1. ptrace PT_TRACE_ME
2. sysctl debug info
3. Process environment
4. Timing checks
5. Debugger detection
6. Breakpoint checks

Bypass techniques:

1. Hook sysctl (Frida):
if (ObjC.available) {
    var sysctl = Module.findExportByName(null, "sysctl");
    Interceptor.attach(sysctl, {
        onLeave: function(retval) {
            // Return not being debugged
            retval.replace(0);
        }
    });
}

2. Hook ptrace:
var ptrace = Module.findExportByName(null, "ptrace");
Interceptor.attach(ptrace, {
    onLeave: function(retval) {
        retval.replace(0);
    }
});

3. Anti-anti-debug:
- Patch binary checks
- Hook debugging APIs
- Normalize environment
```

## Phase 4: Anti-Tamper Bypass

**Android Tamper Detection Bypass**
```
Common checks:
1. APK signature verification
2. checksum validation
3. DEX checksum
4. Resource checksum
5. File integrity checks
6. Obfuscation detection

Bypass techniques:

1. Hook signature checks:
Java.perform(function() {
    var Signature = Java.use("android.content.pm.Signature");
    var PackageManager = Java.use("android.content.pm.PackageManager");
    
    PackageManager.checkSignatures.implementation = function() {
        // Return valid signature
        return PackageManager.PACKAGE_SIGNING_MATCH;
    };
});

2. Patch verification code:
- Remove signature checks
- Skip checksum validation
- Patch verification methods

3. Re-sign APK:
- Remove original signature
- Sign with new certificate
- Update manifest
```

**iOS Tamper Detection Bypass**
```
Common checks:
1. Code signature verification
2. Entitlements validation
3. Provisioning profile checks
4. Binary integrity
5. Bundle integrity

Bypass techniques:

1. Bypass code signing checks:
if (ObjC.available) {
    var SecStaticCodeCheckValidity = Module.findExportByName("Security", "SecStaticCodeCheckValidity");
    Interceptor.attach(SecStaticCodeCheckValidity, {
        onLeave: function(retval) {
            retval.replace(1); // Always valid
        }
    });
}

2. Patch entitlements:
- Remove entitlement checks
- Patch provisioning validation
- Skip bundle checks

3. Re-sign IPA:
- Remove original signature
- Sign with new certificate
- Update entitlements
```

## Phase 5: Obfuscation Bypass

**Android Obfuscation Bypass**
```
Common obfuscation:
1. ProGuard/R8 class/method renaming
2. String encryption
3. Control flow obfuscation
4. Native code obfuscation
5. Resource obfuscation

Deobfuscation techniques:

1. Deobfuscate with JADX:
- JADX decompiler
- Automatic deobfuscation
- Rename classes

2. String decryption:
// Hook string decryption
Java.perform(function() {
    var Crypto = Java.use("com.victim.Crypto");
    Crypto.decrypt.implementation = function(encrypted) {
        var result = this.decrypt(encrypted);
        console.log("Decrypted: " + result);
        return result;
    };
});

3. DEX deobfuscation:
- JEB Decompiler
- GDA Decompiler
- Manual analysis
```

**iOS Obfuscation Bypass**
```
Common obfuscation:
1. Class name obfuscation
2. Selector obfuscation
3. String encryption
4. Control flow obfuscation
5. Native code obfuscation

Deobfuscation techniques:

1. Class dump:
class-dump /path/to/App.app

2. String decryption:
// Hook decryption
if (ObjC.available) {
    var Crypto = ObjC.classes.Crypto;
    var method = Crypto["- decryptString:"];
    Interceptor.attach(method.implementation, {
        onLeave: function(retval) {
            console.log("Decrypted: " + retval);
        }
    });
}

3. Disassembly:
- Hopper Disassembler
- IDA Pro
- Ghidra
```

## Phase 6: Integrity Check Bypass

**Android Integrity Bypass**
```
Common checks:
1. APK signature verification
2. DEX checksum verification
3. Resource integrity checks
4. Native library checksums
5. OAT file verification

Bypass techniques:

1. Hook verification methods:
Java.perform(function() {
    var IntegrityChecker = Java.use("com.victim.IntegrityChecker");
    IntegrityChecker.verifyAPK.implementation = function() {
        return true; // Always valid
    };
    IntegrityChecker.verifyChecksums.implementation = function() {
        return true;
    };
});

2. Patch checksums:
- Calculate new checksums
- Replace in code/resources
- Update verification

3. Bypass SafetyNet:
// Hook SafetyNet
Java.perform(function() {
    var SafetyNet = Java.use("com.google.android.gms.safetynet.SafetyNet");
    SafetyNet.verify.implementation = function() {
        // Return valid response
        return validResponse;
    };
});
```

**iOS Integrity Bypass**
```
Common checks:
1. Code signature validation
2. Entitlements validation
3. Provisioning profile checks
4. Binary integrity verification
5. Bundle integrity checks

Bypass techniques:

1. Hook SecStaticCodeCheckValidity:
if (ObjC.available) {
    var SecStaticCodeCheckValidity = Module.findExportByName("Security", "SecStaticCodeCheckValidity");
    Interceptor.attach(SecStaticCodeCheckValidity, {
        onLeave: function(retval) {
            retval.replace(1); // errSecSuccess
        }
    });
}

2. Patch integrity checks:
- Remove verification code
- Skip checks
- Return valid responses
```

## Phase 7: Environment Detection Bypass

**Android Environment Bypass**
```
Common checks:
1. Emulator detection
2. Debuggable flag
3. Test keys
4. Unknown sources
5. ADB enabled
6. Developer mode

Bypass techniques:

1. Emulator detection bypass:
Java.perform(function() {
    var EmulatorDetector = Java.use("com.victim.EmulatorDetector");
    EmulatorDetector.isEmulator.implementation = function() {
        return false;
    };
});

2. Hide ADB:
// Disable ADB
settings put global adb_enabled 0

3. Hide developer mode:
// Modify settings
settings put global development_settings_enabled 0
```

**iOS Environment Bypass**
```
Common checks:
1. Simulator detection
2. Debug environment
3. Development certificate
4. TestFlight detection
5. Enterprise app detection

Bypass techniques:

1. Simulator detection bypass:
if (ObjC.available) {
    var UIDevice = ObjC.classes.UIDevice;
    var currentDevice = ObjC.classes.UIApplication.sharedApplication.keyWindow.rootViewController;
    
    Interceptor.attach(currentDevice["- isSimulator"].implementation, {
        onLeave: function(retval) {
            retval.replace(0); // Not simulator
        }
    });
}

2. Development bypass:
// Patch environment checks
// Remove debug flags
// Hide development indicators
```

## Phase 8: Automation

**Frida Automation Scripts**
```
Universal bypass script:
// Bypass all protections
Java.perform(function() {
    // Root detection
    var RootDetection = Java.use("com.victim.RootDetection");
    RootDetection["- isRooted"].implementation = function() { return false; };
    
    // SSL pinning
    var TrustManager = Java.use("javax.net.ssl.X509TrustManager");
    TrustManager.checkServerTrusted.implementation = function() { };
    
    // Debug detection
    var Debug = Java.use("android.os.Debug");
    Debug.isDebuggerConnected.implementation = function() { return false; };
    
    // Integrity
    var Integrity = Java.use("com.victim.Integrity");
    Integrity.verify.implementation = function() { return true; };
});
```

**Xposed Module**
```
Create Xposed module:
public class BypassModule implements IXposedHookLoadPackage {
    @Override
    public void handleLoadPackage(LoadPackageParam lpparam) {
        if (!lpparam.packageName.equals("com.victim"))
            return;
        
        // Root detection bypass
        findAndHookMethod("com.victim.RootDetection", 
            lpparam.classLoader, "isRooted", 
            new XC_MethodReplacement() {
                @Override
                protected Object replaceHookedMethod(MethodHookParam param) {
                    return false;
                }
            });
        
        // SSL pinning bypass
        hookAllConstructors("javax.net.ssl.X509TrustManager", 
            new XC_MethodHook() {
                @Override
                protected void beforeHookedMethod(MethodHookParam param) {
                    // Skip validation
                }
            });
    }
}
```

## Final Report

```
[SHIELDING BYPASS] Root Detection
App: com.victim.app
Severity: HIGH (protection bypass)
Bypass: Frida hooking

[Target Protections]
1. Root detection: com.victim.RootDetection.isRooted()
2. SSL pinning: OkHttp3 CertificatePinner
3. Debug detection: android.os.Debug.isDebuggerConnected()
4. Integrity: APK signature verification
5. Obfuscation: ProGuard + string encryption

[Bypass Techniques]
1. Root detection: Frida hook isRooted()
2. SSL pinning: Frida hook check()
3. Debug detection: Frida hook isDebuggerConnected()
4. Integrity: Frida hook verify()
5. Obfuscation: String decryption hooks

[Frida Script]
Java.perform(function() {
    // Root detection bypass
    var RootDetection = Java.use("com.victim.RootDetection");
    RootDetection.isRooted.implementation = function() { return false; };
    
    // SSL pinning bypass
    var CertificatePinner = Java.use("okhttp3.CertificatePinner");
    CertificatePinner.check.implementation = function() { };
    
    // Debug detection bypass
    var Debug = Java.use("android.os.Debug");
    Debug.isDebuggerConnected.implementation = function() { return false; };
    
    // Integrity bypass
    var Integrity = Java.use("com.victim.Integrity");
    Integrity.verify.implementation = function() { return true; };
});

[Testing]
- All protections bypassed
- App functions normally
- Network traffic intercepted
- Dynamic analysis possible

[Remediation]
- Add integrity checks to native code
- Use hardware-backed keystore
- Implement runtime attestation
- Add anti-frida measures
```

## Tools

**Frida:**
- Dynamic instrumentation
- Runtime hooking
- Memory manipulation
- SSL pinning bypass

**Xposed:**
- Framework-wide hooking
- Root detection bypass
- Global modifications

**Substrate:**
- iOS runtime hooking
- Jailbreak detection bypass
- System-wide modifications

**Cycript:**
- Runtime modification
- Objective-C manipulation
- Memory inspection

## Target Platforms

- Android (API 15-34)
- iOS (10-17)
- Windows applications
- macOS applications
- Linux applications
