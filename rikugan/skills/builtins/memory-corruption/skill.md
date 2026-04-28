---
name: Memory Corruption
description: Memory corruption vulnerabilities — UAF, double-free, heap spray, overflow
tags: [memory, corruption, uaf, heap, overflow, use-after-free]
---
Task: Memory Corruption Analysis. Detect and exploit memory corruption vulnerabilities.

## Approach

Focus on memory management bugs: use-after-free, double-free, heap overflow, stack overflow. Understand allocator internals.

## Phase 1: Allocator Analysis

**Identify Memory Allocator**
```
Linux: glibc malloc (ptmalloc2), jemalloc, tcmalloc
Windows: HeapAlloc, RtlAllocateHeap, NT Heap
Custom: Application-specific allocators

Check:
- Import symbols (malloc, free, HeapAlloc)
- String patterns ("jemalloc", "tcmalloc")
- Heap metadata structures
```

**Heap Layout Analysis**
```
Understand heap organization:
- Chunk size and boundaries
- Metadata locations (size, flags, pointers)
- Free lists (fastbin, smallbin, largebin)
- Tcache (glibc 2.26+)

Tools:
- decompile malloc/free wrappers
- Analyze heap metadata structures
- Map heap layout from memory dumps
```

## Phase 2: Vulnerability Discovery

**Use-After-Free (UAF)**
```
Pattern Detection:
1. free(ptr); followed by ptr->method()
2. Double free: free(ptr); free(ptr);
3. Dangling pointers in structures
4. Reference count bugs

Code Patterns:
- free(object); object->vtable()
- pthread_mutex_unlock(&mutex); mutex->data
- Release without clearing pointers

Search:
- xrefs_to on free, HeapFree
- Look for continued use after free
- Check reference counting logic
```

**Double-Free**
```
Detection:
1. Same pointer freed twice
2. Free list corruption
3. Allocator crash: "double free or corruption"

Code Pattern:
ptr = malloc(100);
free(ptr);
... (no realloc)
free(ptr);  // ← Double free

Exploitation:
- Fastbin attack (glibc)
- Unsafe unlink
- Tcache poisoning
```

**Heap Overflow**
```
Detection:
1. Copy beyond allocated size
2. Off-by-one errors
3. Integer overflow in size

Code Pattern:
buf = malloc(user_size);
memcpy(buf, input, user_size + 8);  // Overflow
Or:
buf = malloc(size * 4);  // Integer overflow
memcpy(buf, input, user_input);

Impact:
- Corrupt adjacent chunks
- Overwrite chunk metadata
- Control malloc/free behavior
```

**Stack Overflow**
```
Detection:
1. Fixed-size buffers + unbounded copy
2. Recursive calls without limit
3. Large stack allocations

Code Pattern:
char buffer[256];
strcpy(buffer, user_input);  // No bounds check
Or:
char buffer[512];
gets(buffer);  // Always dangerous

Impact:
- Overwrite return address
- Corrupt stack canaries
- Hijack control flow
```

## Phase 3: Exploitation Techniques

**Use-After-Free Exploitation**
```
Method 1: Vtable Hijack
1. Allocate object A (with vtable)
2. Free object A
3. Allocate object B with controlled data
4. Object B occupies A's memory
5. Call virtual function on A
6. Executes B's vtable pointer → controlled call

Method 2: Function Pointer Overwrite
1. Free object with function pointer
2. Realloc with controlled data
3. Overwrite function pointer
4. Trigger function call
5. Control execution flow

Method 3: Partial Overwrite
1. Free object
2. Realloc partially overlapping object
3. Overwrite critical fields only
4. Preserve other functionality
```

**Double-Free Exploitation**
```
Fastbin Attack (glibc):
1. malloc(A) → free(A) → free(A) (double free)
2. A in fastbin twice
3. malloc(X) → contains A's address
4. Overwrite A's fd pointer
5. malloc(Y) → returns controlled address
6. malloc(Z) → returns fake chunk (write-what-where)

Unsafe Unlink:
1. Overflow chunk to corrupt forward/backward pointers
2. Forward pointer: &target - offset
3. Backward pointer: &target - offset*2
4. Trigger unlink → arbitrary write
```

**Heap Overflow Exploitation**
```
Chunk Metadata Corruption:
1. Overflow size field
2. Set size to large value
3. Next malloc returns chunk overlapping other data
4. Overwrite function pointers, vtables

Allocator Primitive:
1. Corrupt chunk → control malloc/free
2. Allocate arbitrary addresses
3. Overwrite GOT, .dtors, hooks
4. Code execution

Tcache Poisoning (glibc 2.26+):
1. Overflow tcache chunk's next pointer
2. Next malloc returns arbitrary address
3. Write-what-where primitive
4. Overwrite __free_hook or __malloc_hook
```

**Stack Overflow Exploitation**
```
Return Address Overwrite:
1. Calculate offset to saved EIP
2. Overflow with: padding + address
3. Control execution after function return
4. Bypass canaries if present

Canary Bypass:
1. Info leak: Read canary value
2. Brute force: Forking server (1/256)
3. Overwrite: Skip canary check
4. Jump over: Control flow after canary

SEH Overwrite (Windows):
1. Overflow to SEH chain
2. Overwrite SEH handler address
3. Trigger exception → handler
4. Bypass SafeSEH with pop/pop/ret
```

## Phase 4: Advanced Techniques

**Heap Spraying**
```
Goal: Predictable allocation at target address

Method:
1. Allocate many objects of same size
2. Fill heap with controlled data
3. Free/create holes at target locations
4. Trigger vulnerability
5. Land in sprayed heap

Targets:
- JavaScript engines (ArrayBuffer)
- Browser heaps (WebAssembly)
- PDF readers (object allocation)
```

**Heap Feng Shui**
```
Goal: Arrange heap for exploitation

Techniques:
1. Coalesce free chunks
2. Create holes at specific offsets
3. Control allocation order
4. Align objects precisely

Example:
- Allocate 100 objects
- Free every 10th object
- Trigger overflow
- Land in predictable location
```

**Race Condition Exploitation**
```
TOCTOU (Time-of-Check-Time-of-Use):
1. Thread A: Check permissions
2. Thread B: Swap file before use
3. Thread A: Use file with wrong permissions

Heap Race:
1. Thread A: free(object)
2. Thread B: realloc object
3. Thread A: use object (UAF)
4. Win race → exploitation

Exploit:
- Multi-threaded program
- Parallel operations
- Race to corrupt state
```

## Phase 5: Allocator Internals

**glibc Malloc (ptmalloc2)**
```
Chunk Structure:
+--------+--------+--------+--------+
| Prev   | Size   |  ...   |  ...   |
| size   | +flags | data   |  ...   |
+--------+--------+--------+--------+

Metadata:
- Size field (includes flags)
- PREV_INUSE (previous chunk in use)
- IS_MMAPPED (mmap'd chunk)
- NON_MAIN_ARENA (non-main arena)

Bins:
- Fastbin (size < 64, single-linked)
- Smallbin (size < 512, double-linked)
- Largebin (size >= 512, sorted)
- Tcache (per-thread cache, glibc 2.26+)
```

**Windows Heap**
```
Heap Header:
+-----------+-----------+-----------+
| Signature | Flags     | Size      |
| Encoding  | Segment   | Unusable |
+-----------+-----------+-----------+

Allocators:
- LFH (Low-Fragmentation Heap)
- Front-end allocator
- Back-end allocator

Exploitation:
- Overwrite heap header
- Corrupt lookaside list
- Front-end heap metadata corruption
```

**jemalloc**
```
Structure:
- Arenas (allocation contexts)
- Bins (size classes)
- Runs (contiguous pages)
- Chunks (allocations)

Metadata:
- Red-black trees for large allocations
- Per-thread caches (tcache)
- Size-class bins

Exploitation:
- Tcache poisoning
- Bin corruption
- Arena metadata overwrite
```

## Phase 6: Detection & Analysis

**Dynamic Analysis**
```
Tools:
- Valgrind (memcheck, addrcheck)
- AddressSanitizer (ASan)
- MemorySanitizer (MSan)
- Electric Fence
- GDB heap commands

Detection:
- Use-after-free
- Double-free
- Heap overflow
- Invalid access
```

**Static Analysis**
```
Code Review:
- free() usage patterns
- malloc() + memcpy() combinations
- Array bounds checking
- Pointer lifetime tracking

Tools:
- Coverity
- CodeQL
- Semgrep
- Custom grep patterns
```

**Runtime Instrumentation**
```
Techniques:
- Hook malloc/free
- Track allocations
- Detect corruption
- Log memory operations

Tools:
- LD_PRELOAD hooks
- Frida scripts
- Pin tools
- DynamoRIO
```

## Phase 7: Exploit Development

**Local Exploit**
```
1. Reproduce crash
2. Analyze corruption
3. Build primitive
4. Stabilize exploit
5. Bypass mitigations
6. Achieve code execution
```

**Remote Exploit**
```
1. Network input parsing
2. Heap groom for remote
3. Spray heap remotely
4. Trigger vulnerability
5. Remote code execution
6. Stabilize connection
```

**Mitigation Bypass**
```
ASLR: Info leak, partial overwrite
NX: ROP chains, DEP bypass
Canaries: Info leak, brute force
Stack protection: Pointer hijacking
Heap protection: Metadata corruption
Allocator hardening: Race conditions
```

## Final Report

```
[VULNERABILITY] Use-After-Free at 0x401234
Type: Use-After-Free
Severity: CRITICAL (code execution)
Allocator: glibc ptmalloc2

[Bug Details]
Location: vuln_func + 0x56
Object: 0x100 bytes heap allocation
Free: Line 42 (free(obj))
Use: Line 58 (obj->method())

[Exploitation]
1. Allocate object A (vtable @ 0x405000)
2. Trigger free(A)
3. Heap spray with fake vtable @ 0x41410000
4. Realloc at A's address (sprayed data)
5. Call obj->virtual_func()
6. Jumps to fake_vtable[0] → shellcode

[POC]
obj = allocate_object();
free(obj);
// Spray heap with fake vtable
fake_vtable[0] = shellcode_address;
trigger_realloc(); // Overlaps obj
obj->virtual_func(); // Hijacked!

Mitigations: ASLR (partial overwrite), NX (ROP), PIE (info leak)
Bypass: Heap spray + partial overwrite + ROP
