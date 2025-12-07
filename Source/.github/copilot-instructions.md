# GitHub Copilot Instructions for Converse Project (RISC OS)

You are an expert RISC OS developer using Acorn C/C++ (Norcroft).

## Project TODO List
The active TODO list for this project is in `TODO` at the workspace root. Check this file when asked about planned features, outstanding work, or what needs to be implemented next.

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
- **Filer**: Manages databases (UserDB, FileDB, MsgDB). See detailed architecture below.
- **Support**: Shared state module (`ConverseBBS`) for configuration and line state. Server pushes config values on startup; LineTask queries them. See Support Module section below.
- **Server**:
  - `Server/c/main` drives the listener, sockets, and DeskLib UI (`status` and `doors` windows). Icons for the main status window are created dynamically in rows of eight (line number, user, activity, hostname, timer, disconnect, view, logon) starting at icon index **13**; call `main_window_icon_index(line, column)` instead of hard-coding numbers so layout helpers stay in sync.
  - Each main-window row consumes 64 pixels of height, and the window reserves two 64-pixel header rows plus a 10-pixel padding margin. Update `MAIN_WINDOW_TOP_STATIC_ROWS`, `MAIN_WINDOW_PADDING`, or related helpers when adjusting layout.
  - **Status Header Icons**: Icon 1 = Connections Enabled (radio), Icon 2 = Chat Pager (radio), Icon 4 = Total Uptime (HH:MM:SS text), Icon 6 = Total Calls (5-digit counter). Use `Desk_Icon_Select()`/`Desk_Icon_Deselect()` for radio buttons, NOT raw `Desk_Wimp_SetIconState`.
  - **Status Updates**: 1-second timer updates uptime and call totals. Call totals read from Filer Statistics SWI 0x5AA44 reason 0. Uptime calculated from `server_start_time` (Unix timestamp).
  - **Connection Control**: `connections_enabled` flag checked in `check_listener()` to reject new connections when disabled.
  - Door window rows follow the same 64-pixel stepping with helper functions for calculating visible rows and extents. Always adjust both extent calculations and icon creation if the geometry changes.
  - Timers use `timer_set`/`timer_action` handles stored as `long`. When refreshing UI state (e.g., connection timelines or resolver text), respect the column assignments noted above so user text and hostname text do not overwrite each other.
  - The server listens for several Wimp messages from LineTask (see Wimp Messages section below).
  - The `waiting_user` and `user_activity` strings are loaded from the Messages file tokens `server.wait` and `server.nact`. Fallback values are provided if the tokens are missing.

- **LineTask / Script Engine**:
  - Scripts live under `<Converse$Dir>.BBS` and are parsed/executed by `LineTask/c/script`. Use backtick quoting for multi-word literals and `%{macro}` for runtime substitutions.
  - The interpreter exposes host callbacks for time, line info, doors, disconnect, and **`DOING <text>`**, which emits message `0x5AA01` so the server can show per-line activity (text is capped to ~96 bytes). `DOING` accepts macros/escapes; send an empty string to reset to the default "no activity" label.
  - **Authentication**: The `LOGON` script command prompts for username/password and authenticates via Filer SWI 0x5AA41. On success, it stores user_id, access_level, and keys in the task state, updates the Support module line state, and sends a `MESSAGE_LINE_USER` (0x5AA05) Wimp message to update the Server's status window.
  - **ONLINE command**: Shows all connected users with real name, online time, and activity. Queries Support module for line state and Filer userdb for user details. Sysops are tagged with `[SYSOP]`.
  - **Filebase Support** (`LineTask/c/filebase`): Provides `FILEBASE` script command for browsing/downloading files. Uses Filer SWIs at 0x5AA43. Commands: `list`, `select <id>`, `areas`, `area <id>`, `files`, `info <file_id>`, `download <file_id>`, `reset`. Access controlled by user level and keys.
  - **Messagebase Support** (`LineTask/c/messagebase`): Provides `MESSAGEBASE` script command for reading and posting messages. Uses Filer SWIs at 0x5AA42. Commands: `list`, `select <id>`, `areas`, `area <id>`, `messages`, `read [id]`, `info <id>`, `post`, `reset`. Supports local message areas, private user mail, FTN echomail, and FTN netmail. ANSI message viewer with paged display and navigation prompts. Message composer with To, Subject, Body input phases. Access controlled by user level, keys, and message type (private messages only visible to sender/recipient).
  - **Direct Mail Commands**: `SENDMAIL <username> <subject> <body>` sends a private message to a local user (requires Private area configured). `SENDNETMAIL <address> <name> <subject> <body>` queues a netmail to an FTN address for export (requires Netmail area configured). Both commands support macro expansion and backtick quoting. Use `\r\n` in body for line breaks. Netmail is exported when the FTN mailer runs Scan.
  - **File Transfer** (`LineTask/c/transfer`): Implements XMODEM, XMODEM-CRC, XMODEM-1K, YMODEM, YMODEM-G, and ZMODEM protocols for file downloads and uploads. Non-blocking state machine design integrates with Pipes module for I/O. The `SENDFILE <file_id> [protocol]` and `RECEIVEFILE <path> [protocol]` script commands initiate transfers. Protocol values: 0=XMODEM, 1=XMODEM-CRC, 2=XMODEM-1K, 3=YMODEM, 4=YMODEM-G, 5=ZMODEM. YMODEM includes block 0 header with filename/size and batch mode support. ZMODEM features: 32-bit CRC, ZDLE escape encoding, hex (ZHEX) and binary (ZBIN32) frame headers, streaming data with subpacket framing (ZCRCG/ZCRCE/ZCRCQ/ZCRCW), auto-start detection via ZRQINIT, and crash recovery via ZRPOS repositioning. During active transfers, the `transfer_active` flag is set in Support module line state to prevent idle timeout disconnection.
  - **Math Commands**: `ADD`, `SUB`, `MUL`, `DIV`, `MOD` perform integer arithmetic. Syntax: `add result op1 op2`. Division/modulo by zero returns 0.
  - **Random Numbers**: `RANDOM result min max` generates integer in [min, max] range inclusive.
  - **String Operations**: `STRLEN result source` stores length of source variable's value. `HASKEY result key` checks if user has access key.
  - **Terminal Detection**: `DETECTANSI result [timeout_ms]` sends ANSI DSR query (ESC[6n) and waits for cursor position report. Sets result to "1" if ANSI terminal detected, "0" if timeout (default 3000ms). The `ansi` variable is set in Prelogon and available throughout the session.
  - **Visual Control**: `FLASH <0|1>` toggles the blinking text attribute state. `ANYKEY [file]` displays a "Press any key" prompt, optionally loading a custom ANSI file (default: `<Converse$Dir>.BBS.Menus.Anykey` or internal fallback).
  - **Subscript Calls**: `SCRIPT <path>` loads and executes a subscript, then returns to the calling script. Supports up to 8 levels of nesting. Variables are shared between calling and called scripts. Use `return` or `stop` in the subscript to return early. Block IF/ELSE/ENDIF structures are fully supported in subscripts. Example: `script `<Converse$Dir>.BBS.Welcome``.
  - **Login Scan**: `LOGINSCAN` scans all accessible messagebases and filebases for new content since the user's last scan. Reports counts of new private messages addressed to the user (unread, by `receivedby` field) and new files uploaded since `lastscan`. After scanning, updates the user's `lastscan` timestamp in USER_STATS. Typically called in Postlogon script.
  - **System Macros**: `%{accesslevel}`, `%{userid}`, `%{registered}` (1 if logged in), `%{sysop}` (1 if sysop), `%{keys}` (user's key string), `%{hour}`, `%{minute}`, `%{dayofweek}` (0=Sun..6=Sat), `%{day}` (1-31), `%{month}` (1-12), `%{year}` (e.g., 2025).
  - **Selection Macros**: `%{filebaseid}`, `%{filebasename}`, `%{filebaseareaid}`, `%{filebaseareaname}`, `%{messagebaseid}`, `%{messagebasename}`, `%{messagebaseareaid}`, `%{messagebaseareaname}`. Returns current user's selected filebase/messagebase and area IDs and names. Returns empty string or 0 if nothing selected.
  - **User History Persistence**: When a user selects a filebase/messagebase/area via script commands, the selection is automatically saved to their `USER_HISTORY` record in the userdb. On next login, these selections are restored to the session state automatically.
  - **Conditional Operators**: IF command supports `==`, `!=` (string), `>`, `<`, `>=`, `<=` (numeric). Both operands are macro-expanded. Compound conditions supported with `&&` (AND) and `||` (OR): `if %{day} == 25 && %{month} == 12 goto christmas`.

- **LineTask / Terminal (`ansiterm`)**:
  - **Architecture**: The `ansiterm` module implements a custom ANSI terminal emulator. It maintains a grid of cells and handles rendering to a RISC OS window.
  - **Cell Structure**: `ansiterm_cell` uses a 16-bit attribute field (`unsigned short attr`) to support standard colors (FG/BG) plus a **Flash** bit (bit 8).
  - **Blinking Text**: The `ansiterm_blink()` function toggles the visibility of flashing characters. It uses an optimized row-scanning approach to only invalidate/redraw rows containing flashing characters, preventing full-window flicker. This is driven by a 0.5s timer in `main.c`.
  - **Sysop Snoop**: The terminal window mirrors the user's session.
    - **Output**: `pipes_output_write_string` feeds all data sent to the user (scripts, files, menus) into the local terminal emulator.
    - **Input**: `handle_plain_server_byte` echoes user input to the local terminal.
    - **Sysop Input**: `handle_terminal_key` injects local keystrokes into the input stream (local echo handled by `pipes_output_write_string` when the server echoes it back, or locally if needed).
  - **Focus**: The terminal window automatically claims input focus (`Wimp_SetCaretPosition`) when opened via the "View" button in the Server.

## Wimp Messages (LineTask <-> Server)

The Server and LineTask communicate via Wimp user messages. Message base is `0x5AA00`.

| Message | Value | Direction | Purpose |
|---------|-------|-----------|---------|
| `MESSAGE_LINE_BROADCAST` | 0x5AA00 | Server->All | Broadcast to all line tasks (word[0]=reason, 0=quit) |
| `MESSAGE_LINE_ACTIVITY` | 0x5AA01 | LineTask->Server | Update activity column (word[0]=line, bytes[4..]=text) |
| `MESSAGE_LINE_CONTROL` | 0x5AA02 | LineTask->Server | Control commands (word[0]=line, word[1]=reason: 1=logoff) |
| `MESSAGE_LINE_VIEW_WINDOW` | 0x5AA03 | Server->LineTask | Request to open line view window (word[0]=line) |
| `MESSAGE_LINE_REGISTER` | 0x5AA04 | LineTask->Server | LineTask registering with server (word[0]=line) |
| `MESSAGE_LINE_USER` | 0x5AA05 | LineTask->Server | Update user column (word[0]=line, bytes[4..]=realname or empty to reset) |

### MESSAGE_LINE_USER Details
- Sent when user authenticates successfully (contains real name)
- Sent with empty string when user logs off or disconnects (resets to `waiting_user`)
- Server updates the user column icon in the status window

## Filer Module Architecture

### Overview
The Filer module (`Filer/`) provides persistent storage for user accounts, filebases, and messagebases. It uses struct-based flat files with "copy-update-rename" for atomic updates.

### Configuration Files
| Purpose | Path |
|---------|------|
| System Config | `<Converse$Dir>.Resources.Config.System` |
| Lines Config | `<Converse$Dir>.Resources.Config.Lines` |
| MsgBases Master | `<Converse$Dir>.Resources.Config.MsgBases` |
| FileBases Master | `<Converse$Dir>.Resources.Config.FileBases` |
| FTN Config | `<Converse$Dir>.Resources.Config.FTN` |
| MsgBase Defs | `<Converse$Dir>.Resources.Config.MsgBases.<name>` |
| FileBase Defs | `<Converse$Dir>.Resources.Config.FileBases.<name>` |

### Configuration File Format
Configuration files use a simple key-value format with block structures:
- Comments start with `;`
- Global settings: `key value` or `key<tab>value`
- Include directive: `include <path>`
- Block structures: `messagebase N` ... `endmessagebase`, `filebase N` ... `endfilebase`
- Nested blocks: `area N` ... `endarea`, `address N` ... `endaddress`, `uplink N` ... `enduplink`

### File Paths (RISC OS system variables)
| Purpose | Path |
|---------|------|
| System Log | `<Converse$Dir>.Logs.System` |
| Call Log | `<Converse$Dir>.Logs.Calls` |
| Line Logs | `<Converse$Dir>.Logs.Line_<n>` |
| FTN Log | `<Converse$Dir>.Logs.FTN` |
| User Database | `<Converse$Dir>.Resources.Data.UserDB` |
| User Index | `<Converse$Dir>.Resources.Data.UserIDX` |
| User Temp DB | `<Converse$Dir>.Resources.Data.TempDB` |
| Filebase Registry | `<Converse$Dir>.Resources.Data.FileDB` |
| Filebase Index | `<Converse$Dir>.Resources.Data.FileIDX` |
| Messagebase Registry | `<Converse$Dir>.Resources.Data.MsgDB` |
| Messagebase Index | `<Converse$Dir>.Resources.Data.MsgIDX` |
| Call Count Stats | `<Converse$Dir>.Resources.Data.CallCount` |
| Filebase Root | `<Converse$Dir>.FileBases` |
| Messagebase Root | `<Converse$Dir>.MsgBases` |

### Database Layout
- **Base Registry**: Single flat file containing `FILEBASE_RECORD` or `MESSAGEBASE_RECORD` structs.
- **Per-Base Structure** (e.g., `<Converse$Dir>.FileBases.0001`):
  - `FileDB` / `MsgDB` – Item metadata records
  - `FileIDX` / `MsgIDX` – Next-ID counter (4-byte int)
  - `AreaDB` – Area metadata records
  - `AreaIDX` – Next-area-ID counter
  - `Files/` or `Messages/` – Payload directory with area subdirectories
- **Payload Grouping**: Files/messages are stored in group directories (`G00`, `G01`, ...) with 60 items per group to respect RISC OS directory limits (max 77 objects).

### Key Data Structures (`h/structs`)
```c
typedef struct {
    int id;
    char username[32], realname[64], email[64], password[32];
    char keys[128], userdir[256];
    USER_FLAGS user_flags;
    USER_HISTORY user_history;
    USER_STATS user_stats;
} USER_RECORD;
```

**USER_RECORD Field Offsets** (for direct memory access from SWI returns):
| Field | Offset | Size |
|-------|--------|------|
| id | 0 | 4 |
| username | 4 | 32 |
| realname | 36 | 64 |
| email | 100 | 64 |
| password | 164 | 32 |
| keys | 196 | 128 |
| userdir | 324 | 256 |
| user_flags | 580 | 76 |
| user_flags.sysop | 600 | 4 |
| user_flags.accesslevel | 640 | 4 |
| user_history | 656 | 16 |
| user_history.messagebase | 656 | 4 |
| user_history.messagebasearea | 660 | 4 |
| user_history.filebase | 664 | 4 |
| user_history.filebasearea | 668 | 4 |
| user_stats | 672 | 40 |

```c
typedef struct {
    int id, type, accesslevel;
    char keys[128], name[64], filebasedir[256];
} FILEBASE_RECORD;

typedef struct {
    int id, filebaseid, accesslevel;
    char keys[128], name[64];
} FILEBASE_AREA_RECORD;

typedef struct {
    int id, filebaseid, filebaseareaid, deleted, accesslevel;
    char keys[128], name[64], description[256];
    int uploadedby; time_t uploaddate;
    long filesize; int downloads;
} FILE_RECORD;

typedef struct {
    int id, type, accesslevel;
    char keys[128], name[64], messagebasedir[256];
} MESSAGEBASE_RECORD;

typedef struct {
    int id;
    char name[64], tag[64];
    int daystokeep, akause;
    short areatype; /* LOCAL=0, ECHO=1, NET=2, JUNK=3, OTHER=4, FILE=5, TICK=6 */
} MESSAGEBASE_AREA;

typedef struct {
    int id, messagebaseid, messagebaseareaid, type, deleted, accesslevel;
    char keys[128], subject[256];
    int sentby, receivedby;
    FTN_ADDRESS orgaddr, dstaddr;
    time_t imported, sent, read;
    int timesread; long bodysize;
} MESSAGE_RECORD;
```

### User Authentication
The `userdb_authenticate()` function returns one of:
- `FILER_USERDB_AUTH_SUCCESS` (0) – Valid credentials
- `FILER_USERDB_AUTH_NO_USER` (1) – Username not found
- `FILER_USERDB_AUTH_BAD_PASSWORD` (2) – Password mismatch
- `FILER_USERDB_AUTH_LOCKED` (3) – Account locked out

User records are XOR-encrypted at rest; `userdb_encrypt_payload()` / `userdb_decrypt_payload()` toggle the encoding.

### CLI Commands
| Command | Description |
|---------|-------------|
| `*Filer_Status` | Show managed files with existence/size |
| `*Filer_Stats` | Show database statistics |
| `*Filer_FileBases list` | List all filebases |
| `*Filer_FileBases files <base> [area]` | List files in base/area |
| `*Filer_FileBases upload <base> <area> <path> <name> [desc]` | Import a file |
| `*Filer_FileBases delete <base> <file>` | Soft-delete a file |
| `*Filer_FileBases edit <base> <file> <field> <value>` | Edit metadata (name/description/keys/access) |
| `*Filer_MessageBases list` | List all messagebases |
| `*Filer_MessageBases messages <base> [area]` | List messages |
| `*Filer_MessageBases import <base> <area> <path> <type> <subject>` | Import a message |
| `*Filer_MessageBases delete <base> <msg>` | Soft-delete a message |
| `*Filer_FileAreas list [base]` | List file areas |
| `*Filer_MessageAreas list [base]` | List message areas |

### Internal C API (non-SWI)
```c
/* Userbase */
int userdb_add_record(USER_RECORD *record);              /* Returns new ID or 0 */
int userdb_update_record(int id, USER_RECORD *record);   /* Returns 1 on success */
USER_RECORD *userdb_search_record(int id);               /* Returns cached ptr or NULL */
USER_RECORD *userdb_find_username(const char *username);
USER_RECORD *userdb_authenticate(const char *user, const char *pass, FILER_USERDB_AUTH_RESULT *result);
int userdb_delete_record(int id);

/* Filebase */
int filebase_upload_from_host(int base, int area, const char *path, const char *name, const char *desc, int uploader);
int filebase_delete_file(int base, int file, int remove_payload);
int filebase_get_file_record(int base, int file, FILE_RECORD *out);
int filebase_save_file_record(int base, const FILE_RECORD *rec);
int filebase_iterate_bases(int (*cb)(const FILEBASE_RECORD*, void*), void *ctx);
int filebase_iterate_areas(int base, int (*cb)(const FILEBASE_AREA_RECORD*, void*), void *ctx);
int filebase_iterate_files(int base, int (*cb)(const FILE_RECORD*, void*), void *ctx);

/* Messagebase */
int messagebase_store_from_host(int base, const char *path, MESSAGE_RECORD *template);
int messagebase_delete_message(int base, int msg, int remove_payload);
int messagebase_get_message_record(int base, int msg, MESSAGE_RECORD *out);
int messagebase_save_message_record(int base, const MESSAGE_RECORD *rec);
int messagebase_iterate_bases(int (*cb)(const MESSAGEBASE_RECORD*, void*), void *ctx);
int messagebase_iterate_areas(int base, int (*cb)(const MESSAGEBASE_AREA*, void*), void *ctx);
int messagebase_iterate_messages(int base, int (*cb)(const MESSAGE_RECORD*, void*), void *ctx);

/* Statistics */
void stats_initialise(void);
void stats_finalise(void);
int stats_get_call_totals(int *out);
int stats_set_call_totals(int total);
int stats_increment_call_totals(void);

/* Logging */
void log_system(char *entry);
void log_line(int line, char *entry);
void log_call(int line, int user, int status);  /* status: 0=Answered,1=Hungup,2=Aborted,3=Rejected */
void log_ftn(char *entry);
```

## Converse SWI Reference

### Pipes Module (Base 0x5AA00)
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

### Filer Module (Base 0x5AA40)
*R0 = Reason Code. Returns 0 on success, -1 on failure.*
- **Logging (0x5AA40)**:
  - 0 (System): R1=String
  - 1 (Line): R1=Line, R2=String
  - 2 (Call): R1=Line, R2=User, R3=Status
  - 3 (FTN): R1=String
- **Userbase (0x5AA41)**:
  - 0 (Add): R1=Record -> R0=ID
  - 1 (Update): R1=ID, R2=Record
  - 2 (Delete): R1=ID
  - 3 (Search): R1=ID -> R0=RecordPtr
  - 4 (Authenticate): R1=Username, R2=Password -> R0=AuthResult, R1=RecordPtr
  - 5 (UpdateHistory): R1=ID, R2=USER_HISTORY* -> R0=Success(1)/Failure(0)
  - 6 (UpdateStats): R1=ID, R2=USER_STATS* -> R0=Success(1)/Failure(0)
- **Messagebase (0x5AA42)**:
  - 0 (Create): R1=BaseRecord -> R0=ID
  - 1 (Update): R1=ID, R2=BaseRecord
  - 2 (Info): R1=ID -> R0=RecordPtr
  - 3 (BeginUpload): R1=ID, R2=ItemRecord -> R0=ItemID
  - 4 (UploadBlock): R1=ID, R2=ItemID, R3=Data, R4=Len
  - 5 (DownloadBlock): R1=ID, R2=ItemID, R3=Buf, R4=Off, R5=Len
  - 6 (StoreArea): R1=ID, R2=AreaRecord -> R0=AreaID
  - 7 (AreaInfo): R1=ID, R2=AreaID -> R0=AreaRecordPtr
  - 13 (FindUnexported): R1=BaseID, R2=AreaID, R3=Buffer, R4=MaxCount -> R0=Count
  - 14 (MarkExported): R1=BaseID, R2=MsgID -> R0=Success(1)/Failure(0)
- **Filebase (0x5AA43)**:
  - 0 (Create): R1=BaseRecord -> R0=ID
  - 1 (Update): R1=ID, R2=BaseRecord
  - 2 (Info): R1=ID -> R0=RecordPtr
  - 3 (BeginUpload): R1=ID, R2=ItemRecord -> R0=ItemID
  - 4 (UploadBlock): R1=ID, R2=ItemID, R3=Data, R4=Len
  - 5 (DownloadBlock): R1=ID, R2=ItemID, R3=Buf, R4=Off, R5=Len
  - 6 (StoreArea): R1=ID, R2=AreaRecord -> R0=AreaID
  - 7 (AreaInfo): R1=ID, R2=AreaID -> R0=AreaRecordPtr
- **Statistics (0x5AA44)**:
  - 0 (ReadCallTotals): Returns the persisted system call count in R0. The value lives in `<Converse$Dir>.Resources.CallCount`; the module auto-creates this file with `0` if it is missing.
  - 1 (WriteCallTotals): R1=New total. Persists the value back to `CallCount` and returns 0 on success, -1 on failure. Logging SWI reason 2 automatically increments this total after each call entry.

### Support Module (Base 0x5AA80)
*Shared state storage for configuration and line status. Server pushes values; LineTask queries them.*
- **Config (0x5AA80)**:
  - 0 (Get): R1=Key -> R0=ValuePtr (or 0 if not found)
  - 1 (Set): R1=Key, R2=Value
  - Keys: `bbs_name`, `sysop_name`, `contact`, `hostname`, `max_lines`, `listen_port`, `idle_timeout`, `botstopper`, `needlogin`, `closed`, `pager`, `anykey`, `chatstart`, `chatend`, `prelogon`, `postlogon`, `logoff`, `welcome`, `newuser`, `timeup`, `lockedout`, `closedsys`, `aftermail`
- **Line (0x5AA81)**:
  - 0 (Set): R1=Line, R2=Field, R3=Value
  - 1 (Get): R1=Line, R2=Field -> R0=Value
  - Fields: 0=configured, 1=connected, 2=user_id, 3=connect_time, 4=hostname, 5=transfer_active
- **Activity (0x5AA82)**:
  - 0 (Set): R1=Line, R2=TextPtr
  - 1 (Get): R1=Line -> R0=TextPtr
- **LineConfig (0x5AA83)**:
  - 0 (Set): R1=Line, R2=Field, R3=Value
  - 1 (Get): R1=Line, R2=Field -> R0=Value
  - Fields: 0=enabled, 1=botstopper (char*), 2=hello (char*)
- **MsgBaseConfig (0x5AA84)**:
  - 0 (GetGlobal): -> R0=MSGBASE_GLOBAL_CONFIG ptr
  - 1 (SetGlobal): R1=Field (0=retention, 1=accesslevel, 2=storage_root), R2=Value
  - 2 (GetBase): R1=BaseID -> R0=MSGBASE_CONFIG ptr
  - 3 (SetBase): R1=BaseID, R2=MSGBASE_CONFIG ptr
  - 4 (GetArea): R1=BaseID, R2=AreaID -> R0=MSGBASE_AREA_CONFIG ptr
  - 5 (SetArea): R1=BaseID, R2=AreaID, R3=MSGBASE_AREA_CONFIG ptr
  - 6 (CountBases): -> R0=Count
  - 7 (CountAreas): R1=BaseID -> R0=Count
- **FileBaseConfig (0x5AA85)**:
  - 0 (GetGlobal): -> R0=FILEBASE_GLOBAL_CONFIG ptr
  - 1 (SetGlobal): R1=Field (0=accesslevel, 1=storage_root, 2=max_upload), R2=Value
  - 2 (GetBase): R1=BaseID -> R0=FILEBASE_CONFIG ptr
  - 3 (SetBase): R1=BaseID, R2=FILEBASE_CONFIG ptr
  - 4 (GetArea): R1=BaseID, R2=AreaID -> R0=FILEBASE_AREA_CONFIG ptr
  - 5 (SetArea): R1=BaseID, R2=AreaID, R3=FILEBASE_AREA_CONFIG ptr
  - 6 (CountBases): -> R0=Count
  - 7 (CountAreas): R1=BaseID -> R0=Count
- **FTNConfig (0x5AA86)**:
  - 0 (GetGlobal): -> R0=FTN_GLOBAL_CONFIG ptr
  - 1 (SetGlobal): R1=Field, R2=Value
  - 2 (GetAddress): R1=AddrID -> R0=FTN_ADDRESS_CONFIG ptr
  - 3 (SetAddress): R1=AddrID, R2=FTN_ADDRESS_CONFIG ptr
  - 4 (GetUplink): R1=UplinkID -> R0=FTN_UPLINK_CONFIG ptr
  - 5 (SetUplink): R1=UplinkID, R2=FTN_UPLINK_CONFIG ptr
  - 6 (CountAddresses): -> R0=Count
  - 7 (CountUplinks): -> R0=Count

## ARCbbsDoors Emulator Module

### Overview
The ARCbbsDoors emulator (`ARCbbs/`) provides compatibility with legacy ARCbbs doors. It implements the original ARCbbsDoors SWI interface (chunk base `0x41040`) so that doors written for ARCbbs can run on Converse BBS.

### Architecture
- **Source**: `ARCbbs/c/arcbbs` (SWI handler), `ARCbbs/c/buffer` (buffer management)
- **CMHG**: `ARCbbs/cmhg/arcbbsHdr`
- **Max Lines**: 32 (matches Converse)
- **Buffer Size**: 1KB per direction per line

### Door Protocol
The ARCbbs door protocol uses three communication mechanisms:

1. **Status Byte** - Handshake control:
   - `0` = Idle / disconnect request
   - `1-254` = Door number (request pending)
   - `255` = Door active

2. **Request/Reply Protocol** - Doors query user data via 256-byte request blocks
3. **Input/Output Buffers** - 1KB circular buffers for terminal I/O

### Door Lifecycle
1. LineTask sets status to door number (1-254) and launches the door
2. Door polls `ReadStatus` looking for its door number
3. Door finds its number, writes `255` to accept the connection
4. Door uses `InputRead`/`OutputWrite` for I/O and `SendRequest`/`GetReply` for user data
5. When finished, door writes `0` to status
6. LineTask detects status=0 and resumes script execution

### Script Integration
Use `call arcbbsdoor <door_number> <command>` in scripts:
```
call arcbbsdoor 4 `<Converse$Dir>.BBS.Doors.ARCbbs.!SnakeDoor %{line}`
```
The door number must match the door's configured `DoorNumber` (usually in its `Config` file).

### ARCbbsDoors SWI Reference (Base 0x41040)

| Offset | Name | Entry | Exit |
|--------|------|-------|------|
| 0 | ReadStatus | R0=line | R0=status byte |
| 1 | WriteStatus | R0=line, R1=status | — |
| 2 | SendRequest | R0=line, R1=ptr to 256-byte request | — |
| 3 | GetReply | R0=line, R1=ptr to 256-byte buffer | R0=0 if ready, -1 if not |
| 4-5 | Reserved | — | — |
| 6 | InputStatus | R0=line | R0=bytes waiting |
| 7 | InputRead | R0=line | R0=byte or -1 |
| 8 | OutputStatus | R0=line | R0=bytes free |
| 9 | OutputWrite | R0=line, R1=byte | — |
| 10 | ClearInput | R0=line | — |
| 11 | ClearOutput | R0=line | — |
| 12 | HostWrite | R0=line, R1=byte | R0=0/-1 |
| 13 | HostRead | R0=line | R0=byte or -1 |
| 14 | Activate | R0=line | R0=0/-1 |
| 15 | Deactivate | R0=line | R0=0/-1 |

SWIs 12-15 are extensions for LineTask (host) use, not part of the original ARCbbs API.

### Request/Reply Protocol
Doors use `SendRequest` to query information. The request block format:
- Bytes 0-3: Request number (word)
- Bytes 4-255: Request-specific data

**Request 0 - Read General User Information** (reply format):
| Offset | Type | Description |
|--------|------|-------------|
| w0 | int | User number |
| w4 | int | Time of first logon |
| w8 | int | Time of last logon |
| w32 | int | Terminal type (0=tty, 1=vt52, 2=vt100, 3=ansi) |
| w52 | int | User level |
| w172 | int | Time left for call (seconds) |
| w176 | int | Time allocated for call (seconds) |
| w180 | int | Connection speed |
| b186 | byte | Page length |
| s187 | string | Username (31 bytes max) |

**Request 1 - Read User Address** (reply format):
| Offset | Type | Description |
|--------|------|-------------|
| s0 | string | Username |
| s31 | string | Real name |
| s62-s155 | strings | Address lines 1-4 |
| s186 | string | Postcode |
| s197 | string | Telephone |

**Requests 100-199** - Write operations (no reply):
- 100: Write uploads count
- 101: Write downloads count
- 102: Write ratio
- 103: Write time for call (seconds)
- 104: Write time per day (minutes)
- 105: Write user level

### CLI Commands
| Command | Description |
|---------|-------------|
| `*ARCbbsDoors_Status` | Show status of all active ARCbbs door lines |

## ConverseDoors Module (Native Door Support)

### Overview
The ConverseDoors module (`Doors/`) provides a native door interface for Converse BBS. Unlike the ARCbbsDoors emulator which provides backward compatibility with legacy doors, ConverseDoors offers a modern registration-based API with full user information and messaging support.

### Architecture
- **Source**: `Doors/c/doors` (SWI handler), `Doors/c/debug` (debug support)
- **CMHG**: `Doors/cmhg/doorsHdr`
- **Max Sessions**: 32 (one per line)
- **Buffer Size**: 4KB per direction per session
- **SWI Chunk**: 0x5AAC0

### Key Differences from ARCbbsDoors
| Feature | ARCbbsDoors | ConverseDoors |
|---------|-------------|---------------|
| Registration | Door number polling | Explicit Register/Deregister |
| User Info | Request/Reply protocol | Direct GetUserInfo SWI |
| System Info | Not available | GetSystemInfo SWI |
| Messaging | Not available | SendMessage/ReceiveMessage |
| Buffers | 1KB | 4KB |
| Block I/O | Not available | ReadBlock/WriteBlock |

### Door Lifecycle
1. Door calls `Register` with line number, returns session handle on success
2. Door uses I/O SWIs with session handle for terminal communication
3. Door queries user/system info as needed
4. When finished, door calls `Deregister` with session handle
5. LineTask receives notification and resumes script execution

### Script Integration
Use `call door <command>` in scripts:
```
call door `<Converse$Dir>.BBS.Doors.MyDoor %{line}`
```
The door receives the line number as a command-line argument and registers itself.

### Data Structures

```c
/* Door session (internal to module) */
typedef struct {
    int line;                       /* Line number (0-31) */
    int active;                     /* Session active flag */
    uint32_t flags;                 /* Door flags */
    uint8_t input_buffer[4096];     /* Input buffer (host->door) */
    uint8_t output_buffer[4096];    /* Output buffer (door->host) */
    int input_head, input_tail;     /* Input buffer pointers */
    int output_head, output_tail;   /* Output buffer pointers */
} DOOR_SESSION;

/* User information structure */
typedef struct {
    int user_id;                    /* User ID from database */
    char username[32];              /* Login name */
    char realname[64];              /* Full name */
    int access_level;               /* Access level (0-255) */
    int sysop;                      /* Sysop flag (1=yes) */
    char keys[128];                 /* Access keys string */
    time_t connect_time;            /* Connection timestamp */
    time_t session_start;           /* Session start time */
    int terminal_type;              /* 0=dumb,1=vt52,2=vt100,3=ansi */
    int screen_width;               /* Terminal width (usually 80) */
    int screen_height;              /* Terminal height (usually 24) */
} DOOR_USER_INFO;

/* System information structure */
typedef struct {
    char bbs_name[64];              /* BBS name */
    char sysop_name[64];            /* Sysop name */
    int max_lines;                  /* Maximum lines configured */
    int total_calls;                /* Total call count */
    time_t system_uptime;           /* Server start time */
} DOOR_SYSTEM_INFO;
```

### ConverseDoors SWI Reference (Base 0x5AAC0)

| Offset | Name | Entry | Exit |
|--------|------|-------|------|
| 0 | Register | R0=line, R1=flags | R0=session handle or -1 |
| 1 | Deregister | R0=session | R0=0/-1 |
| 2 | GetInfo | R0=session | R0=DOOR_SESSION* or 0 |
| 3 | ReadByte | R0=session | R0=byte or -1 |
| 4 | WriteByte | R0=session, R1=byte | R0=0/-1 |
| 5 | ReadLine | R0=session, R1=buffer, R2=maxlen | R0=length or -1 |
| 6 | WriteLine | R0=session, R1=string | R0=0/-1 |
| 7 | ReadBlock | R0=session, R1=buffer, R2=maxlen | R0=bytes read or -1 |
| 8 | WriteBlock | R0=session, R1=buffer, R2=length | R0=bytes written or -1 |
| 9 | InputStatus | R0=session | R0=bytes available |
| 10 | OutputStatus | R0=session | R0=bytes free |
| 11 | ClearInput | R0=session | R0=0/-1 |
| 12 | ClearOutput | R0=session | R0=0/-1 |
| 13 | GetUserInfo | R0=session, R1=DOOR_USER_INFO* | R0=0/-1 |
| 14 | GetSystemInfo | R0=session, R1=DOOR_SYSTEM_INFO* | R0=0/-1 |
| 15 | SendMessage | R0=session, R1=type, R2=data | R0=0/-1 |
| 16 | ReceiveMessage | R0=session, R1=buffer | R0=type or -1 |

### Host Integration Functions
LineTask uses these functions to integrate with the door module:

```c
/* Host writes data for door to read */
int doors_host_write(int session, const uint8_t *data, int len);

/* Host reads data written by door */
int doors_host_read(int session, uint8_t *buffer, int maxlen);

/* Check if session is active */
int doors_session_active(int session);

/* Force-close a session (on disconnect) */
void doors_force_close(int session);
```

### Message Types (SendMessage/ReceiveMessage)
| Type | Direction | Purpose |
|------|-----------|---------|
| 0 | Door->Host | Door exiting normally |
| 1 | Door->Host | Door exiting with error |
| 2 | Door->Host | Request chat with sysop |
| 3 | Host->Door | Sysop initiated chat |
| 4 | Host->Door | Time warning (5 min left) |
| 5 | Host->Door | Force disconnect requested |

### CLI Commands
| Command | Description |
|---------|-------------|
| `*ConverseDoors_Status` | Show status of all active door sessions |

### Example Door Code

```c
#include "kernel.h"

#define SWI_DOORS_BASE    0x5AAC0
#define SWI_Register      (SWI_DOORS_BASE + 0)
#define SWI_Deregister    (SWI_DOORS_BASE + 1)
#define SWI_ReadByte      (SWI_DOORS_BASE + 3)
#define SWI_WriteByte     (SWI_DOORS_BASE + 4)
#define SWI_WriteLine     (SWI_DOORS_BASE + 6)

int main(int argc, char *argv[])
{
    _kernel_swi_regs regs;
    int session, ch;
    
    if (argc < 2) return 1;
    
    /* Register with ConverseDoors */
    regs.r[0] = atoi(argv[1]);  /* Line number */
    regs.r[1] = 0;              /* No special flags */
    if (_kernel_swi(SWI_Register, &regs, &regs) != NULL || regs.r[0] < 0)
        return 1;
    session = regs.r[0];
    
    /* Write greeting */
    regs.r[0] = session;
    regs.r[1] = (int)"Welcome to my door!\r\n";
    _kernel_swi(SWI_WriteLine, &regs, &regs);
    
    /* Echo loop */
    while (1) {
        regs.r[0] = session;
        if (_kernel_swi(SWI_ReadByte, &regs, &regs) != NULL) break;
        ch = regs.r[0];
        if (ch < 0) continue;  /* No data */
        if (ch == 'q' || ch == 'Q') break;
        
        regs.r[0] = session;
        regs.r[1] = ch;
        _kernel_swi(SWI_WriteByte, &regs, &regs);
    }
    
    /* Deregister */
    regs.r[0] = session;
    _kernel_swi(SWI_Deregister, &regs, &regs);
    
    return 0;
}
```

## File Transfer Protocol Implementation Details

### Architecture Overview
File transfers are implemented in `LineTask/c/transfer` and `LineTask/h/transfer`. The design is a non-blocking state machine that integrates with the Pipes module for I/O and the Filer module for file access.

**Key Functions:**
- `filebase_download_block()` - Read file data from Filer (NOT `filebase_read_block`)
- `filebase_get_file_size()` - Get file size before transfer
- `pipe_write_byte()` / `pipe_read_byte()` - Single byte I/O via Pipes SWIs
- `pipe_write_block()` - Block write to output pipe
- `pipe_bytes_available()` / `pipe_space_available()` - Check pipe status
- `transfer_set_timeout()` / `transfer_timeout_expired()` - Timeout management
- `transfer_get_time()` - Returns OS_ReadMonotonicTime in centiseconds
- `set_transfer_state()` - Notify Support module (field 5) that transfer is active

### Protocol Enum (`transfer_protocol`)
```c
typedef enum {
    TRANSFER_PROTO_XMODEM,      /* 0 - Basic XMODEM with checksum */
    TRANSFER_PROTO_XMODEM_CRC,  /* 1 - XMODEM with CRC-16 */
    TRANSFER_PROTO_XMODEM_1K,   /* 2 - XMODEM with 1K blocks */
    TRANSFER_PROTO_YMODEM,      /* 3 - YMODEM with batch support */
    TRANSFER_PROTO_YMODEM_G,    /* 4 - YMODEM-G streaming */
    TRANSFER_PROTO_ZMODEM       /* 5 - ZMODEM full implementation */
} transfer_protocol;
```

### XMODEM Implementation

#### Constants
```c
#define XMODEM_SOH              0x01    /* Start of 128-byte block */
#define XMODEM_STX              0x02    /* Start of 1024-byte block */
#define XMODEM_EOT              0x04    /* End of transmission */
#define XMODEM_ACK              0x06    /* Acknowledge */
#define XMODEM_NAK              0x15    /* Negative acknowledge */
#define XMODEM_CAN              0x18    /* Cancel transfer */
#define XMODEM_CTRLZ            0x1A    /* Padding byte (EOF in CP/M) */
#define XMODEM_CRC_START        'C'     /* CRC mode request */

#define XMODEM_BLOCK_SIZE       128     /* Standard block size */
#define XMODEM_1K_BLOCK_SIZE    1024    /* Extended block size */
#define XMODEM_MAX_RETRIES      10      /* Max retry attempts per block */
#define XMODEM_START_RETRIES    6       /* Max start sequence retries */
#define XMODEM_TIMEOUT_MS       10000   /* 10 second timeout */
#define XMODEM_START_TIMEOUT_MS 60000   /* 60 second initial timeout */
```

#### Block Format
```
[SOH/STX] [Block#] [255-Block#] [Data (128/1024 bytes)] [Checksum/CRC]
```
- SOH (0x01) = 128-byte block, STX (0x02) = 1024-byte block
- Block# starts at 1, wraps at 255 back to 0
- Complement byte is `255 - Block#`
- Checksum: Simple sum of data bytes (mod 256)
- CRC-16: Polynomial 0x1021 (CCITT), sent MSB first

#### CRC-16 Calculation
```c
/* Precomputed CRC-16 table for polynomial 0x1021 */
static const uint16_t crc16_table[256];

uint16_t transfer_crc16(const uint8_t *data, int length)
{
    uint16_t crc = 0;
    while (length--) {
        crc = (crc << 8) ^ crc16_table[(crc >> 8) ^ *data++];
    }
    return crc;
}
```

#### Send State Machine
```
XFER_SEND_WAIT_START    → Wait for 'C' (CRC) or NAK (checksum)
XFER_SEND_BLOCK         → Send: SOH/STX + block# + ~block# + data + checksum/CRC
XFER_SEND_WAIT_ACK      → Wait for ACK/NAK
  - ACK: Advance to next block or EOT
  - NAK: Retransmit current block
XFER_SEND_EOT           → Send EOT (0x04)
XFER_SEND_WAIT_EOT_ACK  → Wait for final ACK
XFER_COMPLETE           → Done
```

#### Receive State Machine
```
XFER_RECV_SEND_START    → Send 'C' (CRC mode) or NAK (checksum mode)
XFER_RECV_WAIT_BLOCK    → Wait for SOH/STX/EOT
XFER_RECV_READ_BLOCK    → Read block# + ~block# + data + checksum/CRC
  - Validate block number and checksum/CRC
XFER_RECV_SEND_ACK      → Send ACK, write data to file
XFER_RECV_SEND_NAK      → Send NAK on error
  - On EOT: Send ACK, complete
XFER_COMPLETE           → Done
```

#### Protocol Detection
- Receiver sends 'C' for CRC mode, NAK (0x15) for checksum mode
- Sender detects based on first received byte
- XMODEM-1K: Sender can use STX for 1024-byte blocks, receiver must handle both

### YMODEM Implementation

#### Differences from XMODEM
- **Block 0 Header**: Contains filename and file size before data
- **Batch Mode**: Can transfer multiple files in sequence
- **1K Blocks**: Uses STX/1024-byte blocks by default
- **Empty Block 0**: Signals end of batch

#### Block 0 Format
```
[filename]\0[size in ASCII] [mod_time in octal]\0...
```
Example: `test.txt\0123456 12345678901\0`
- Filename is null-terminated
- File size in ASCII decimal
- Optional: modification time in octal (Unix timestamp)
- Remainder padded with nulls

#### YMODEM Send Flow
```
1. Wait for 'C' from receiver
2. Send Block 0 (header with filename/size)
3. Wait for ACK + 'C'
4. Send data blocks (1-N)
5. Send EOT
6. Wait for NAK, send EOT again, wait for ACK
7. For batch: Wait for 'C', send empty Block 0, wait for ACK
```

#### YMODEM Receive Flow
```
1. Send 'C' to request header
2. Receive Block 0, extract filename/size
3. ACK + send 'C' to request data
4. Receive data blocks, write to file
5. On EOT: NAK once, then ACK
6. Send 'C' for next file or receive empty Block 0 (end batch)
```

#### YMODEM-G (Streaming Mode)
- Receiver sends 'G' instead of 'C'
- Sender does not wait for per-block ACKs
- Streams blocks continuously
- Any error = abort (no retransmission)
- Much faster but requires reliable link

#### Key YMODEM Functions
```c
/* Build YMODEM block 0 header */
static int ymodem_build_header(uint8_t *buffer, const char *filename, 
                               long filesize, int block_size);

/* Parse received block 0 */
static int ymodem_parse_block0(const uint8_t *data, int data_len,
                               char *filename, long *filesize, time_t *modtime);

/* Send functions */
int transfer_start_send_ymodem(int line, transfer_protocol protocol,
                               int filebase_id, int file_id,
                               const char *filename, transfer_session *session);

/* Receive functions */
int transfer_start_receive_ymodem(int line, transfer_protocol protocol,
                                  const char *upload_dir, transfer_session *session);
```

#### YMODEM State Machine States
**Send states:**
```c
XFER_SEND_WAIT_START        /* Wait for 'C' */
XFER_SEND_HEADER_BLOCK      /* Send block 0 (filename/size) */
XFER_SEND_WAIT_HEADER_ACK   /* Wait for ACK + 'C' */
XFER_SEND_BLOCK             /* Send data blocks */
XFER_SEND_WAIT_ACK          /* Wait for ACK */
XFER_SEND_EOT               /* Send EOT */
XFER_SEND_WAIT_EOT_ACK      /* Wait for EOT ACK */
XFER_SEND_END_BATCH         /* Send empty block 0 */
XFER_SEND_WAIT_END_BATCH_ACK /* Wait for final ACK */
```

**Receive states:**
```c
XFER_RECV_SEND_START        /* Send 'C' or 'G' */
XFER_RECV_WAIT_HEADER       /* Wait for block 0 */
XFER_RECV_READ_HEADER       /* Read block 0 data */
XFER_RECV_ACK_HEADER        /* ACK header, send 'C' */
XFER_RECV_WAIT_BLOCK        /* Wait for data block */
XFER_RECV_READ_BLOCK        /* Read block data */
XFER_RECV_SEND_ACK          /* Send ACK */
XFER_RECV_SEND_NAK          /* Send NAK */
```

#### Session Fields for YMODEM
```c
int is_ymodem;                      /* Flag: using YMODEM protocol */
int ymodem_g;                       /* Flag: YMODEM-G streaming mode */
int header_sent;                    /* Flag: block 0 already sent */
int ymodem_batch_complete;          /* Flag: end-of-batch reached */
char ymodem_filename[128];          /* Filename from/for block 0 */
```

### ZMODEM Implementation

#### Constants (in `LineTask/h/transfer`)
```c
/* Frame types */
#define ZRQINIT     0   /* Request receiver init */
#define ZRINIT      1   /* Receiver init */
#define ZSINIT      2   /* Sender init */
#define ZACK        3   /* Acknowledge */
#define ZFILE       4   /* File info */
#define ZSKIP       5   /* Skip file */
#define ZNAK        6   /* NAK - retry */
#define ZABORT      7   /* Abort */
#define ZFIN        8   /* Finish session */
#define ZRPOS       9   /* Resume position */
#define ZDATA       10  /* Data packet follows */
#define ZEOF        11  /* End of file */
#define ZFERR       12  /* File error */
#define ZCRC        13  /* CRC request */
#define ZCHALLENGE  14  /* Challenge */
#define ZCOMPL      15  /* Complete */
#define ZCAN        16  /* Cancel */

/* Subpacket frame endings */
#define ZCRCE       'h'  /* CRC next, end of frame */
#define ZCRCG       'i'  /* CRC next, frame continues */
#define ZCRCQ       'j'  /* CRC next, frame continues, ZACK expected */
#define ZCRCW       'k'  /* CRC next, ZACK expected, end frame */

/* Escape characters */
#define ZPAD        '*'  /* Padding before header */
#define ZDLE        0x18 /* Data link escape */
#define ZDLEE       0x58 /* Escaped ZDLE */
#define ZBIN        'A'  /* Binary header (CRC-16) */
#define ZHEX        'B'  /* Hex header */
#define ZBIN32      'C'  /* Binary header (CRC-32) */

/* Receiver capability flags */
#define CANFDX      0x01 /* Full duplex */
#define CANOVIO     0x02 /* Can overlap I/O */
#define CANBRK      0x04 /* Can send break */
#define CANCRY      0x08 /* Can encrypt */
#define CANLZW      0x10 /* Can LZW compress */
#define CANFC32     0x20 /* Can use CRC-32 */
#define ESCCTL      0x40 /* Escape control chars */
#define ESC8        0x80 /* Escape 8-bit chars */

/* Timeouts */
#define ZMODEM_HEADER_TIMEOUT   10000  /* 10 seconds */
#define ZMODEM_DATA_TIMEOUT     15000  /* 15 seconds */
#define ZMODEM_MAX_BLOCK        1024   /* Max data block size */
```

#### State Machine States
**Send states (BBS → User download):**
```c
ZFER_SEND_ZRQINIT       /* Sending ZRQINIT to initiate */
ZFER_SEND_WAIT_ZRINIT   /* Waiting for receiver's ZRINIT */
ZFER_SEND_ZFILE         /* Sending ZFILE header */
ZFER_SEND_WAIT_ZRPOS    /* Waiting for ZRPOS position */
ZFER_SEND_ZDATA         /* Sending ZDATA header */
ZFER_SEND_DATA          /* Streaming data subpackets */
ZFER_SEND_ZEOF          /* Sending ZEOF */
ZFER_SEND_WAIT_ZEOF_ACK /* Waiting for ZEOF acknowledgement */
ZFER_SEND_ZFIN          /* Sending ZFIN */
ZFER_SEND_WAIT_ZFIN_ACK /* Waiting for receiver's ZFIN */
ZFER_SEND_OO            /* Sending "OO" final bytes */
```

**Receive states (User → BBS upload):**
```c
ZFER_RECV_WAIT_ZRQINIT  /* Waiting for sender's ZRQINIT */
ZFER_RECV_SEND_ZRINIT   /* Sending our ZRINIT */
ZFER_RECV_WAIT_ZFILE    /* Waiting for ZFILE header */
ZFER_RECV_SEND_ZRPOS    /* Sending ZRPOS to request data */
ZFER_RECV_WAIT_ZDATA    /* Waiting for ZDATA header */
ZFER_RECV_DATA          /* Receiving streaming data */
ZFER_RECV_WAIT_ZEOF     /* Waiting for ZEOF */
ZFER_RECV_SEND_ZRINIT_NEXT /* Sending ZRINIT for next file */
ZFER_RECV_WAIT_ZFIN     /* Waiting for sender's ZFIN */
ZFER_RECV_SEND_ZFIN     /* Sending our ZFIN response */
```

#### Session Fields (in `transfer_session`)
```c
int is_zmodem;              /* Flag: using ZMODEM protocol */
uint32_t zmodem_crc32;      /* Running CRC-32 value */
int zmodem_escctl;          /* Flag: escape control chars */
uint8_t zmodem_rxflags[4];  /* Received header flags */
uint8_t zmodem_rx_hdr[4];   /* Received header data */
uint8_t zmodem_rx_buf[2048];/* Receive buffer */
int zmodem_rx_state;        /* Header parser state */
int zmodem_zdle_pending;    /* ZDLE escape pending flag */
long zmodem_txpos;          /* Transmit file position */
long zmodem_rxpos;          /* Receive file position */
int zmodem_window_count;    /* Bytes since last ZACK */
```

#### CRC-32 Implementation
Uses reflected polynomial 0xEDB88320 with 256-entry lookup table:
```c
static const uint32_t crc32_table[256] = { /* precomputed */ };

uint32_t transfer_crc32(const uint8_t *data, int len)
{
    uint32_t crc = 0xFFFFFFFF;
    while (len--) {
        crc = crc32_table[(crc ^ *data++) & 0xFF] ^ (crc >> 8);
    }
    return crc ^ 0xFFFFFFFF;
}
```

#### Key Helper Functions
```c
/* Check if byte needs ZDLE escaping */
static int zmodem_needs_escape(uint8_t byte, int escctl);

/* Write byte with ZDLE escaping */
static int zmodem_write_escaped(transfer_session *session, uint8_t byte);

/* Send hex header (for negotiation) */
static int zmodem_send_hex_header(transfer_session *session, int type,
                                   uint8_t p0, uint8_t p1, uint8_t p2, uint8_t p3);

/* Send binary32 header (for data transfer) */
static int zmodem_send_bin32_header(transfer_session *session, int type,
                                     uint8_t p0, uint8_t p1, uint8_t p2, uint8_t p3);

/* Send position header (ZRPOS, ZACK, etc.) */
static int zmodem_send_pos_header(transfer_session *session, int type, long pos);

/* Send data subpacket with frame ending */
static int zmodem_send_data_subpacket(transfer_session *session,
                                       const uint8_t *data, int len, int frameend);

/* Parse received hex header */
static int zmodem_parse_hex_header(transfer_session *session,
                                    const uint8_t *buf, int len);

/* Get position from received header */
static long zmodem_get_header_pos(transfer_session *session);

/* Receive and parse header (returns frame type or -1) */
static int zmodem_receive_header(transfer_session *session);
```

#### Protocol Flow

**Send (Download from BBS):**
1. Send `ZRQINIT` hex header
2. Wait for receiver's `ZRINIT` (get capabilities)
3. Send `ZFILE` with filename/size in data subpacket
4. Wait for `ZRPOS` (receiver requests position)
5. Send `ZDATA` header with position
6. Stream data subpackets (ZCRCG for continuation, ZCRCE for end)
7. Send `ZEOF` with final position
8. Wait for receiver's `ZRINIT` (ready for next file)
9. Send `ZFIN` (no more files)
10. Wait for receiver's `ZFIN`
11. Send "OO" and complete

**Receive (Upload to BBS):**
1. Wait for sender's `ZRQINIT`
2. Send `ZRINIT` with capabilities (CANFDX | CANOVIO | CANFC32)
3. Wait for `ZFILE` header, parse filename/size
4. Send `ZRPOS 0` to request from start
5. Wait for `ZDATA` header
6. Receive streaming data, handle ZDLE escaping
7. On `ZEOF`, send `ZRINIT` for next file
8. Wait for sender's `ZFIN`
9. Send `ZFIN` response
10. Complete

#### Important Implementation Notes

1. **Use `filebase_download_block()` not `filebase_read_block()`** - The Filer module function for reading file data is `filebase_download_block()`.

2. **Use `transfer_timeout_expired()` not `transfer_check_timeout()`** - The timeout check function is `transfer_timeout_expired()`.

3. **ZDLE Escape Handling**: Bytes that need escaping: ZDLE itself, XON (0x11), XOFF (0x13), XON|0x80, XOFF|0x80. When `escctl` flag set, also escape all control chars (< 0x20).

4. **CRC-32 is sent LSB first** in binary headers.

5. **Hex headers end with CR LF** and optional XON.

6. **After ZEOF, receiver must wait for ZFIN**: The receiver sends `ZRINIT` after `ZEOF` but must then wait for the sender's `ZFIN` before sending its own `ZFIN` response. This was a bug that caused client hangs.

### Script Command Integration

**SENDFILE handler** (`LineTask/c/script`):
- Parses protocol string: `xmodem`, `xmodem-crc`, `xmodem-1k`, `ymodem`, `ymodem-g`, `zmodem`
- Maps to protocol numbers 0-5
- Calls `state->host.start_transfer()` callback
- Sets `state->status = SCRIPT_STATUS_WAIT_TRANSFER`

**RECEIVEFILE handler** (`LineTask/c/script`):
- Same protocol parsing
- `proto_names[]` array must include all 6 protocols for display
- Bounds check must be `protocol <= 5` not `protocol <= 4`

**Host callbacks** (`LineTask/c/main`):
- `script_host_start_transfer()` - Maps protocol to enum, calls appropriate start function
- `script_host_start_receive_transfer()` - Same for uploads
- Both check for `protocol == 5` to call ZMODEM-specific start functions

### BBS Script Updates

The `BBS/Filebase` script provides the user menu:
- Option [6] = ZMODEM (recommended)
- Default protocol changed from YMODEM to ZMODEM
- Added `dl_zmodem` and `ul_zmodem` labels

```
print `  [6] ZMODEM (recommended)\r\n`
...
if proto_choice == `6` goto dl_zmodem
...
label dl_zmodem
doing `Downloading file...`
sendfile `%{file_id}` zmodem
goto download_done
```

## Web Server Module

### Overview
The Web Server module (`Web/`) provides HTTP access to static files and filebase downloads. It runs as a Wimp application on port 80.

### Architecture
- **Source Files**:
  - `c/main`: Wimp application, socket handling, multi-client management, download handling
  - `c/http`: HTTP/1.0 protocol parser and response builder
  - `c/template`: Template engine for `{{filebase}}` substitution with hierarchical listing
  - `c/debug`: Debug logging via Reporter module
- **Resources**:
  - `Resources/Messages`: UI strings
  - `Resources/!Boot,feb`: Boot obey file
  - `Resources/!Run,feb`: Run obey file

### Configuration
- **Listen Port**: 80 (hardcoded in `WEB_DEFAULT_PORT`)
- **Document Root**: `<Converse$Dir>.Web`
- **Default File**: `index` (no extension)
- **Max Clients**: 16 simultaneous connections
- **Client Timeout**: 30 seconds
- **Server Enable**: `webserver yes` in System config runs `<Converse$Dir>.Resources.!RunFWeb`

### HTTP Features
- HTTP/1.0 protocol (Connection: close)
- Methods: GET only
- MIME types: HTML, CSS, TXT, PNG, JPG, GIF, JS, JSON, ICO
- Status codes: 200, 400, 403, 404, 500, 503

### Template Tags
HTML files (filetype 0xFAF) are scanned for template tags:
- `{{filebase}}`: Replaced with hierarchical HTML listing of all filebases, areas, and files

### Template Output Structure
The `{{filebase}}` tag generates:
```html
<div class="filebase-listing">
  <div class="filebase">
    <h3>Filebase Name</h3>
    <div class="filearea">
      <h4>Area Name</h4>
      <table class="file-table">
        <thead>
          <tr>
            <th>Name</th><th>Size</th><th>Description</th>
            <th>Downloads</th><th>Download</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>filename</td><td>1.5 MB</td><td>Description</td>
            <td>42</td><td><a href="/download/1/5/filename">Download</a></td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="filearea">
      <h4>Uncategorized</h4>
      <!-- Files with area_id = 0 -->
    </div>
  </div>
</div>
```

### Download URL Format
Files are downloaded via `/download/<base_id>/<file_id>/<filename>`:
- `base_id`: Filebase ID (integer)
- `file_id`: File ID within the filebase (integer)
- `filename`: Display name (ignored, used for browser filename)

### Download Handler (`handle_download_request`)
1. Parses base_id and file_id from URL
2. Calls Filer SWI `0x5AA43` with `FILER_FILEBASE_CMD_FILE_INFO` (11)
3. Checks file is not deleted
4. Builds filesystem path: `<Converse$Dir>.FileBases.<base_id>.Files[.A<area_id>].G<group>.<file_id>`
5. Group calculation: `(file_id - 1) / 60`
6. Serves file via `http_send_file()`

### FILE_RECORD Field Offsets
Used for parsing SWI return pointer:
| Field | Offset | Size |
|-------|--------|------|
| id | 0 | 4 |
| filebaseid | 4 | 4 |
| filebaseareaid | 8 | 4 |
| deleted | 12 | 4 |
| accesslevel | 16 | 4 |
| keys | 20 | 128 |
| name | 148 | 64 |
| uploadedby | 212 | 4 |
| uploaddate | 216 | 4 |
| description | 220 | 256 |
| filesize | 476 | 4 |
| downloads | 480 | 4 |

### Path Mapping
URL paths are converted to RISC OS paths:
- `/` → `<Converse$Dir>.Web.index`
- `/files/test` → `<Converse$Dir>.Web.files.test`
- `/about/` → `<Converse$Dir>.Web.about.index`
- `/download/1/5/test` → Filebase download (special handler)

### Security
- Path traversal blocked (rejects `..`, `:`, `@`, `$`, `%`, `^`, `&`, `\`)
- Request size limit: 4KB
- No CGI/script execution
- Download URLs validate base_id/file_id are numeric

### Logging
Web server logs to `<Converse$Dir>.Logs.Web` via Filer SWI:
- `SWI_FILER_LOGGING` (0x5AA40) with reason `FILER_LOG_CMD_WEB` (4)
- Logs: startup, shutdown, connections, requests with status codes, downloads

### Filer SWI Commands Used
| Command | Value | Purpose |
|---------|-------|---------|
| `FILER_FILEBASE_CMD_INFO` | 2 | Get filebase record by ID |
| `FILER_FILEBASE_CMD_ENUMERATE_BASES` | 8 | Iterate filebases by index |
| `FILER_FILEBASE_CMD_ENUMERATE_AREAS` | 9 | Iterate areas within filebase |
| `FILER_FILEBASE_CMD_ENUMERATE_FILES` | 10 | Iterate files within area |
| `FILER_FILEBASE_CMD_FILE_INFO` | 11 | Get file record by base_id/file_id |

### Integration
- Responds to `MESSAGE_LINE_BROADCAST` (0x5AA00) for shutdown (reason 0 = quit)
- Launched by Server via `launch_web_task()` when `webserver yes` in config
- Queries Filer module (SWI 0x5AA43) for filebase listings and downloads
- Uses Reporter module for debug output

### Example Web Content
Create files in `<Converse$Dir>.Web`:
```html
<!-- index file (filetype FAF) -->
<!DOCTYPE html>
<html>
<head>
  <title>Converse BBS</title>
  <style>
    .filebase { margin: 20px 0; }
    .filearea { margin-left: 20px; }
    .file-table { border-collapse: collapse; width: 100%; }
    .file-table th, .file-table td { border: 1px solid #ccc; padding: 8px; }
  </style>
</head>
<body>
  <h1>Welcome to Converse BBS</h1>
  <h2>File Downloads</h2>
  {{filebase}}
</body>
</html>
```

## FTN Mailer Module

### Overview
The FTN Mailer (`FTN/`) implements FidoNet Technology Network (FTN) mail exchange. It consists of:
- **Mailer** (`FTN/c/mailer`): Wimp application, BinkP sessions, event handling
- **BinkP** (`FTN/c/binkp`): BinkP protocol implementation for sessions
- **Tosser** (`FTN/c/tosser`): Inbound packet processing, echomail/netmail tossing
- **Scanner** (`FTN/c/scanner`): Outbound message scanning and routing
- **Packer** (`FTN/c/packer`): Outbound packet creation
- **Queue** (`FTN/c/queue`): Outbound file queue management
- **TIC** (`FTN/c/tic`): TIC file processing for file distribution
- **FREQ** (`FTN/c/freq`): File request processing

### Echomail Group Filtering
Areas can be assigned to groups (e.g., "A", "B", "C") and uplinks specify which groups they carry. When scanning outbound echomail, messages are only routed to uplinks whose groups overlap with the area's groups.

**Configuration:**
```
; In messagebase config
area 2
    name        BBS Discussion
    tag         BBS_DISCUSSION
    areatype    1
    groups      A,B
endarea

; In FTN config
uplink 1
    address     2:250/0.0
    groups      A,B,C
enduplink
```

The scanner compares area groups to uplink groups. If any group matches, the uplink receives echomail from that area. Empty groups on either side means "match all".

### Uplink Aliases (AKAs)
FTN hubs often have multiple addresses (AKAs). When a hub connects or we connect to it, it may report a different address than what we have configured. Use aliases to tell the mailer that multiple addresses refer to the same uplink.

**Configuration:**
```
uplink 1
    address     2:250/0.0
    host        hub.example.com
    port        24554
    password    secret
    groups      A,B,C
    alias       2:250/1.0
    alias       2:250/2.0
enduplink
```

When looking for files to send during a session, the mailer checks:
1. The primary address (from `address` field)
2. All configured aliases

This ensures that if the hub reports as `2:250/1.0` instead of `2:250/0.0`, we still find and send our queued files for that uplink.

### Transit Netmail
Netmail addressed to nodes other than our configured addresses is marked as transit and stored with `exported=0`. The scanner picks up unexported netmail and routes it to the appropriate uplink based on the destination address.

**Routing logic:**
1. If destination is a direct uplink → route to that uplink
2. Else → route via zone uplink (first uplink in same zone, or default uplink)

Points are handled by routing to the boss node (point=0).

### TIC File Processing
TIC files accompany files in FTN file distribution networks. The TIC module:

**Inbound processing:**
1. Scans inbound directory for `*.tic` files
2. Parses TIC metadata (filename, area, size, CRC, origin, etc.)
3. Verifies file CRC-32 if specified
4. Matches area tag to filebase area
5. Stores file via Filer SWI

**TIC file format:**
```
File myfile.lha
Area RETROCOMPUTING
Desc A cool retro computing file
Size 12345
CRC 12345678
Origin 2:250/1.0
From 2:250/0.0
To 2:250/9.0
Seenby 2:250/0.0
Seenby 2:250/1.0
Path 2:250/1.0
```

### Scanner Functions
```c
int scanner_get_area_info(int base_id, int area_id, char *tag, int *areatype, int *akause);
int scanner_get_area_info_full(int base_id, int area_id, char *tag, int *areatype, int *akause, char *groups);
int scanner_get_echomail_uplinks(const char *area_groups, FTN_ADDR *uplinks, int max_uplinks);
int scanner_route_netmail(const FTN_ADDR *dest, FTN_ADDR *uplink_out, char *password_out, size_t pw_size);
```

### TIC Functions
```c
int tic_parse_file(const char *tic_path, TIC_FILE *tic);
int tic_process_inbound(void);
int tic_store_file(const TIC_FILE *tic, const char *file_path);
int tic_match_area(const char *area_tag, int *filebase_id, int *filebase_area_id);
unsigned long tic_calculate_crc32(const char *file_path);
```

### File Requests (FREQ)
The mailer supports FTN file requests in both directions.

**Outbound FREQ (Requesting Files):**
- Use the FREQ window (Commands menu) to request files from remote nodes
- Creates a `.req` file in BSO outbound directory for the target address
- Queue scanning detects `.req` files as `QUEUE_FILE_REQ` type
- When connecting, `binkp_process_req_file()` reads the REQ file and sends M_GET with size=0, time=0

**Inbound FREQ (Responding to Requests):**
- Remote sends M_GET with size=0 and time=0 (FREQ convention)
- `binkp_handle_get()` detects this and calls `freq_process_request()`
- Searches configured `freqpath` directory for matching files
- Supports wildcards (* and ?) in filenames
- If found: queues file for send via `binkp_start_send_file()`
- If not found: sends M_SKIP to indicate unavailability

**Configuration:**
```
freqpath    <Converse$Dir>.FTN.Freq
freqexec    (reserved for external processor)
```

**FREQ Functions:**
```c
FREQ_STATUS freq_process_request(MAILER_SESSION *session, const char *filename);
int freq_lookup_file(const char *filename, FREQ_RESPONSE_FILE *response);
int freq_lookup_wildcard(const char *pattern, FREQ_RESPONSE_FILE *responses, int max);
int freq_queue_file(MAILER_SESSION *session, const FREQ_RESPONSE_FILE *file);
```

### Automatic Toss and Poll Intervals
The FTN config supports automatic tossing and polling on configurable intervals:

**Configuration (`Demo/Config/FTN`):**
```
tossinterval    300     ; Seconds between automatic toss runs (0 = disabled)
pollinterval    3600    ; Seconds between automatic uplink polls (0 = disabled)
```

**Implementation:**
- `FTN_GLOBAL_CONFIG` struct contains `toss_interval` and `poll_interval` fields
- Support module SWI 0x5AA86 (FTNConfig) fields 8 and 9 for get/set
- Server parses `tossinterval` and `pollinterval` from FTN config file
- FTN Mailer uses timers in null poll handler to trigger automatic operations
- Intervals are in seconds; timer comparison uses `time(NULL)`

**Support Module Fields (SWI 0x5AA86, SetGlobal reason 1):**
| Field | Value | Type | Description |
|-------|-------|------|-------------|
| toss_interval | 8 | int | Seconds between auto-toss (0=disabled) |
| poll_interval | 9 | int | Seconds between auto-poll (0=disabled) |

## Server Status Window

### Overview
The Server application (`Server/`) displays a status window with connection information and system statistics. The window is divided into a static header area and dynamic per-line rows.

### Window Layout
- **Window Width**: 1736 OS units (fixed)
- **Row Height**: 64 OS units per line
- **Header Rows**: 2 static rows (128 OS units) + 10-pixel padding
- **Static Icons**: Icons 0-12 are header elements created in template
- **Dynamic Icons**: Icons 13+ are created at runtime for each configured line

### Status Header Icons (`Server/h/iconnames`)
```c
#define STATUS_CONNECTIONSENABLED 1  /* Radio button: connections enabled */
#define STATUS_CHATPAGER          2  /* Radio button: chat pager enabled */
#define STATUS_TOTALTIME          4  /* Text: uptime HH:MM:SS */
#define STATUS_TOTALCALLS         6  /* Text: call counter 00000 */
```

### Per-Line Icon Columns
Each line row contains 8 icons (increased from 7 to add Logon button):

| Column | Index | Width (OS) | Purpose |
|--------|-------|------------|---------||
| 0 | 0 | 56 | Line number |
| 1 | 1 | 200 | Username/waiting |
| 2 | 2 | 430 | Activity text |
| 3 | 3 | 510 | Hostname |
| 4 | 4 | 169 | Connect timer |
| 5 | 5 | 56 | D (Disconnect) button |
| 6 | 6 | 56 | V (View) button |
| 7 | 7 | 56 | L (Logon) button |

**Icon Index Calculation:**
```c
#define ICONS_PER_LINE 8
#define FIRST_DYNAMIC_ICON 13

int main_window_icon_index(int line, int column)
{
    return FIRST_DYNAMIC_ICON + (line * ICONS_PER_LINE) + column;
}
```

### Status Update Functions (`Server/c/main`)

**Initialization:**
```c
static void status_initialise(void)
{
    server_start_time = time(NULL);
    connections_enabled = 1;
    status_set_icon_selected(STATUS_CONNECTIONSENABLED, 1);
    
    /* Set chat pager from config */
    if (str_casecmp(system_configuration[0].pager, "yes") == 0)
    {
        chat_pager_enabled = 1;
        status_set_icon_selected(STATUS_CHATPAGER, 1);
    }
    
    status_update_uptime();
    status_update_call_totals();
    status_update_timer = timer_set(100);  /* 1 second = 100cs */
}
```

**Periodic Update (in null poll handler):**
```c
static void status_poll_update(void)
{
    if (timer_action(status_update_timer))
    {
        status_update_uptime();
        status_update_call_totals();
        status_update_timer = timer_set(100);
    }
}
```

**Icon Selection (uses DeskLib properly):**
```c
static void status_set_icon_selected(Desk_icon_handle icon, int selected)
{
    if (selected)
    {
        Desk_Icon_Select(main_window, icon);
    }
    else
    {
        Desk_Icon_Deselect(main_window, icon);
    }
}
```

**Important:** Do NOT use raw `Desk_Wimp_SetIconState` for radio button selection. Use `Desk_Icon_Select()` and `Desk_Icon_Deselect()` from `Desk.Icon.h`.

**Uptime Display:**
```c
static void status_update_uptime(void)
{
    time_t now = time(NULL);
    int elapsed = (int)(now - server_start_time);
    int hours = elapsed / 3600;
    int minutes = (elapsed % 3600) / 60;
    int seconds = elapsed % 60;
    
    snprintf(time_str, sizeof(time_str), "%02d:%02d:%02d", hours, minutes, seconds);
    Desk_Icon_SetText(main_window, STATUS_TOTALTIME, time_str);
}
```

**Call Totals (queries Filer Statistics SWI):**
```c
static int filer_get_call_totals(void)
{
    _kernel_swi_regs regs;
    regs.r[0] = STATS_REASON_READ_CALL_TOTALS;  /* 0 */
    if (_kernel_swi(SWI_CONVERSEFILER_STATISTICS, &regs, &regs) != NULL)
        return 0;
    return regs.r[0];
}

static void status_update_call_totals(void)
{
    int total_calls = filer_get_call_totals();
    snprintf(calls_str, sizeof(calls_str), "%05d", total_calls);
    Desk_Icon_SetText(main_window, STATUS_TOTALCALLS, calls_str);
}
```

### Connection Enable/Disable
The `connections_enabled` flag controls whether the listener accepts new connections:

```c
/* In check_listener() */
if (!connections_enabled)
{
    /* Reject connection immediately */
    Desk_Socket_Close(client_socket);
    return;
}
```

Toggle via STATUS_CONNECTIONSENABLED icon click:
```c
static void status_handle_checkbox_click(Desk_icon_handle icon)
{
    if (icon == STATUS_CONNECTIONSENABLED)
    {
        connections_enabled = !connections_enabled;
        status_set_icon_selected(STATUS_CONNECTIONSENABLED, connections_enabled);
    }
}
```

### Global Variables (`Server/h/main`)
```c
extern int connections_enabled;      /* 1 = accepting connections */
extern int chat_pager_enabled;       /* 1 = chat pager active */
extern time_t server_start_time;     /* Unix timestamp of server start */
extern long status_update_timer;     /* Timer handle for 1-second updates */
```

## Call Logging and Statistics

### Call Counter Integration
The call counter increments on each successful user login via the Filer Logging SWI.

**LineTask Call Logging (`LineTask/c/main`):**
```c
/* Constants for call logging */
#define FILER_LOG_REASON_CALL        2
#define CALL_STATUS_ANSWERED         0
#define CALL_STATUS_HUNGUP           1
#define CALL_STATUS_ABORTED          2
#define CALL_STATUS_REJECTED         3

/* After successful authentication in script_host_authenticate_user(): */
{
    _kernel_swi_regs call_regs;
    call_regs.r[0] = FILER_LOG_REASON_CALL;
    call_regs.r[1] = state->line_id;
    call_regs.r[2] = user_id;
    call_regs.r[3] = CALL_STATUS_ANSWERED;
    _kernel_swi(SWI_CONVERSE_FILER_LOGGING, &call_regs, &call_regs);
}
```

**Filer Module Handler (`Filer/c/filer`):**
```c
case FILER_LOG_CMD_CALL:
    log_call((int)r->r[1], (int)r->r[2], (int)r->r[3]);
    r->r[0] = 0;
    break;
```

**Statistics Increment (`Filer/c/logging`):**
```c
void log_call(int line_id, int user_id, int status_id)
{
    /* ... write to call log file ... */
    (void)stats_increment_call_totals();
}
```

**Statistics Storage (`Filer/c/stats`):**
- File: `<Converse$Dir>.Resources.Data.CallCount`
- Format: Plain text integer
- Auto-created with value `0` if missing
- Persisted on each increment and module finalisation

### Call Log File Format
Path: `<Converse$Dir>.Logs.Calls`
```
DD/MM/YYYY,HH:MM:SS,line_id,user_id,status
```
Status values: `Answered`, `Hungup`, `Aborted`, `Rejected`

