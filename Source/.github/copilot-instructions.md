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
- **Filer**: Manages databases (UserDB, FileDB, MsgDB). See detailed architecture below.
- **Support**: Shared state module (`ConverseBBS`) for configuration and line state. Server pushes config values on startup; LineTask queries them. See Support Module section below.
- **Server**:
  - `Server/c/main` drives the listener, sockets, and DeskLib UI (`status` and `doors` windows). Icons for the main status window are created dynamically in rows of six (line number, user, activity, hostname, timer, action) starting at icon index **13**; call `main_window_icon_index(line, column)` instead of hard-coding numbers so layout helpers stay in sync.
  - Each main-window row consumes 64 pixels of height, and the window reserves two 64-pixel header rows plus a 10-pixel padding margin. Update `MAIN_WINDOW_TOP_STATIC_ROWS`, `MAIN_WINDOW_PADDING`, or related helpers when adjusting layout.
  - Door window rows follow the same 64-pixel stepping with helper functions for calculating visible rows and extents. Always adjust both extent calculations and icon creation if the geometry changes.
  - Timers use `timer_set`/`timer_action` handles stored as `long`. When refreshing UI state (e.g., connection timelines or resolver text), respect the column assignments noted above so user text and hostname text do not overwrite each other.
  - The server listens for Wimp message `0x5AA01` (line activity updates) from LineTask. The first word is the line number; the payload is a null-terminated string copied into the activity column. Reject updates for invalid line IDs.

- **LineTask / Script Engine**:
  - Scripts live under `<Converse$Dir>.BBS` and are parsed/executed by `LineTask/c/script`. Use backtick quoting for multi-word literals and `%{macro}` for runtime substitutions.
  - The interpreter exposes host callbacks for time, line info, doors, disconnect, and **`DOING <text>`**, which emits message `0x5AA01` so the server can show per-line activity (text is capped to ~96 bytes). `DOING` accepts macros/escapes; send an empty string to reset to the default "no activity" label.
  - **Filebase Support** (`LineTask/c/filebase`): Provides `FILEBASE` script command for browsing/downloading files. Uses Filer SWIs at 0x5AA43. Commands: `list`, `select <id>`, `areas`, `area <id>`, `files`, `info <file_id>`, `download <file_id>`, `reset`. Access controlled by user level and keys.

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
- **Messagebase (0x5AA42) & Filebase (0x5AA43)**:
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
  - Fields: 0=configured, 1=connected, 2=user_id, 3=connect_time, 4=hostname
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
