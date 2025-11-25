# GitHub Copilot Instructions for Converse Project (RISC OS)

You are an expert RISC OS developer using Acorn C/C++ (Norcroft).

## Environment & Constraints
- **OS**: RISC OS (Open).
- **Compiler**: Norcroft C/C++ (Acorn C/C++).
- **Standard**: C90 (ANSI C). Avoid C99/C11 features unless strictly necessary and supported.
- **Concurrency**: **NO Multithreading**. The environment is single-threaded cooperative multitasking.
- **POSIX**: **NOT POSIX compliant**. Do not use `<unistd.h>`, `<pthread.h>`, `<sys/stat.h>`, etc.
- **File System**:
  - **No file extensions** in the source tree (e.g., headers in `h/`, source in `c/`).
  - **Path Separator**: Use `.` (dot) for directory separation in RISC OS paths (e.g., `<Converse$Dir>.Logs.System`).
  - **Filenames**: Case-insensitive but case-preserving.

## Libraries
The workspace includes `SharedLibs` containing:
- **CLib**: Standard C library (RISC OS implementation).
- **OSLib**: High-level C wrappers for RISC OS SWIs. Prefer `oslib/*.h` over raw `_kernel_swi` where possible, but `kernel.h` is used for module entry points.
- **DeskLib**: Wimp/Desktop library (`Desk/*`).
- **TCPIPLibs**: BSD-style socket library.

**Rule**: Do not reference the `SharedLibs` file paths in code. Use standard include directives (e.g., `#include "kernel.h"`, `#include "oslib/osfile.h"`).

## Module Architecture
- **Structure**:
  - `c/`: Source files.
  - `h/`: Header files.
  - `cmhg/`: C Module Header Generator definitions (SWI tables, commands).
  - `o/`: Object files (not in git).
  - `Makefile`: Acorn makefile format.
- **Memory Management**:
  - Modules run in the RMA (Relocatable Module Area).
  - Use `OS_Module` (SWI 0x1E) for persistent allocations.
  - Avoid large stack allocations.
- **SWI Handling**:
  - Return `NULL` (0) on success, or a pointer to `_kernel_oserror` on failure for OS routines.
  - For internal Converse SWIs (Pipes/Filer), the convention is often:
    - Return `0` (or specific value) in R0 on success.
    - Return `-1` in R0 on logical failure (do not set V-flag).
    - Validate all inputs (pointers, handles).

## Coding Style
- **Headers**: Use `#include "header.h"` for local headers (mapped to `h/header`).
- **Types**: Use `stdint.h` types (`uint32_t`, `uint8_t`) where precise width matters.
- **Strings**: Always use `snprintf` and ensure null-termination.
- **Logging**: Use `debug_printf` (wraps `Report_Text0`) for debugging.

## Specific Modules
- **Pipes**: Manages circular buffers (lines 0-31). Uses watermarks (bits 6/7) for flow control.
- **Filer**: Manages databases (UserDB, FileDB, MsgDB). Uses struct-based flat files with "copy-update-rename" for safety.
- **Server**:
  - `Server/c/main` drives the listener, sockets, and DeskLib UI (`status` and `doors` windows). Icons for the main status window are created dynamically in rows of six (line number, user, activity, hostname, timer, action) starting at icon index **13**; call `main_window_icon_index(line, column)` instead of hard-coding numbers so layout helpers stay in sync.
  - Each main-window row consumes 64 pixels of height, and the window reserves two 64-pixel header rows plus a 10-pixel padding margin. Update `MAIN_WINDOW_TOP_STATIC_ROWS`, `MAIN_WINDOW_PADDING`, or related helpers when adjusting layout.
  - Door window rows follow the same 64-pixel stepping with helper functions for calculating visible rows and extents. Always adjust both extent calculations and icon creation if the geometry changes.
  - Timers use `timer_set`/`timer_action` handles stored as `long`. When refreshing UI state (e.g., connection timelines or resolver text), respect the column assignments noted above so user text and hostname text do not overwrite each other.
  - The server listens for Wimp message `0x5A581` (line activity updates) from LineTask. The first word is the line number; the payload is a null-terminated string copied into the activity column. Reject updates for invalid line IDs.

- **LineTask / Script Engine**:
  - Scripts live under `<Converse$Dir>.BBS` and are parsed/executed by `LineTask/c/script`. Use backtick quoting for multi-word literals and `%{macro}` for runtime substitutions.
  - The interpreter exposes host callbacks for time, line info, doors, disconnect, and **`DOING <text>`**, which emits message `0x5A581` so the server can show per-line activity (text is capped to ~96 bytes). `DOING` accepts macros/escapes; send an empty string to reset to the default "no activity" label.

## Converse SWI Reference

### Pipes Module (Base 0x5A580)
*Validates line (0-31). Returns -1 on failure/empty/full.*
- **Status/Control**:
  - `ReadStatus` (0): R0=Line -> R0=Status
  - `WriteStatus` (1): R0=Line, R1=Status -> R0=0
  - `ResetState` (A): R0=Line -> R0=0
  - `ClearInput` (6) / `ClearOutput` (7): R0=Line -> R0=0
- **Input (Host->Slave)**:
  - `InputStatus` (2): R0=Line -> R0=BytesUsed
  - `InputRead` (3): R0=Line -> R0=Byte/-1
  - `InputWrite` (8): R0=Line, R1=Byte -> R0=0/-1
  - `InputPeek` (B): R0=Line -> R0=Byte/-1
  - `InputWriteBlock` (D): R0=Line, R1=Ptr, R2=Count -> R0=Copied
- **Output (Slave->Host)**:
  - `OutputStatus` (4): R0=Line -> R0=BytesFree
  - `OutputWrite` (5): R0=Line, R1=Byte -> R0=0/-1
  - `OutputRead` (9): R0=Line -> R0=Byte/-1
  - `OutputPeek` (C): R0=Line -> R0=Byte/-1
  - `OutputReadBlock` (E): R0=Line, R1=Ptr, R2=Count -> R0=Copied

### Filer Module (Base 0x16F00)
*R0 = Reason Code. Returns 0 on success, -1 on failure.*
- **Logging (0x16F00)**:
  - 0 (System): R1=String
  - 1 (Line): R1=Line, R2=String
  - 2 (Call): R1=Line, R2=User, R3=Status
  - 3 (FTN): R1=String
- **Userbase (0x16F01)**:
  - 0 (Add): R1=Record -> R0=ID
  - 1 (Update): R1=ID, R2=Record
  - 2 (Delete): R1=ID
  - 3 (Search): R1=ID -> R0=RecordPtr
- **Messagebase (0x16F02) & Filebase (0x16F03)**:
  - 0 (Create): R1=BaseRecord -> R0=ID
  - 1 (Update): R1=ID, R2=BaseRecord
  - 2 (Info): R1=ID -> R0=RecordPtr
  - 3 (BeginUpload): R1=ID, R2=ItemRecord -> R0=ItemID
  - 4 (UploadBlock): R1=ID, R2=ItemID, R3=Data, R4=Len
  - 5 (DownloadBlock): R1=ID, R2=ItemID, R3=Buf, R4=Off, R5=Len
  - 6 (StoreArea): R1=ID, R2=AreaRecord -> R0=AreaID
  - 7 (AreaInfo): R1=ID, R2=AreaID -> R0=AreaRecordPtr
- **Statistics (0x16F04)**:
  - 0 (ReadCallTotals): Returns the persisted system call count in R0. The value lives in `<Converse$Dir>.Resources.CallCount`; the module auto-creates this file with `0` if it is missing.
  - 1 (WriteCallTotals): R1=New total. Persists the value back to `CallCount` and returns 0 on success, -1 on failure. Logging SWI reason 2 automatically increments this total after each call entry.
