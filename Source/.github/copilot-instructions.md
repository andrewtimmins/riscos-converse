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
The workspace includes `Reference/` containing:
- **CLib** (`Reference/CLib`): Standard C library headers (`h/`) and objects (`o/`).
- **OSLib** (`Reference/OSLib`): High-level C wrappers for RISC OS SWIs (`oslib/h/oslib`). Prefer `oslib/*.h` over raw `_kernel_swi` where possible.
- **DeskLib** (`Reference/Desk`): Wimp/Desktop library (`Desk/h`).
- **TCPIPLibs** (`Reference/TCPIPLibs`): BSD-style socket library (including `sys/`, `netinet/`, `arpa/`, etc.).

**Rule**: Do not reference the `Reference` file paths in code. Use standard include directives (e.g., `#include "kernel.h"`, `#include "oslib/osfile.h"`, `#include "Desk/Icon.h"`, `#include "sys/socket.h"`).

## Reference Material
The workspace `Reference/` directory contains source code for legacy RISC OS applications. Use these as a reference for protocol implementation, reverse-engineering legacy behaviors, or understanding RISC OS idioms:
- **Reference/Code/ARCbbs**: Original source for ARCbbs. Critical for `ARCbbsDoors` emulator accuracy.
- **Reference/Code/!ArmBBS**: Another major RISC OS BBS reference.
- **Reference/Code/BinkD**: Reference for BinkP/FTN implementation.

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

- **Server / Line Types**:
  - Lines are configured with a `type` keyword in the Lines config file. Each line can be one of three types:
    - **telnet** (default): Accepts incoming TCP connections via the network listener. The hostname column shows the remote IP or resolved hostname.
    - **serial**: Uses a BlockDriver for modem/serial communication. Handled by the separate Serial app. Requires additional config: `driver`, `port`, `speed`, `format`, `flow`. The hostname column shows "SERIAL".
    - **local**: Reserved for desktop-only access via the View/Logon buttons. Never accepts external connections. The hostname column shows "LOCAL".
  - **Serial Configuration Example**:
    ```
    line 1
        enabled     1
        type        serial
        driver      InternalPC
        port        0
        speed       115200
        format      8N1
        flow        rts
        botstopper  (Press ENTER to continue...)
    endline
    ```
  - **Local Lines**: Simply excluded from `check_listener()`. Users access local lines via the L (Logon) button which launches LineTask, and the V (View) button which opens the sysop terminal window.

- **Serial Handler** (`Serial/`):
  - Standalone Wimp application launched by Server via `<Converse$Dir>.Resources.!RunSerial`.
  - Only launched if at least one serial line is configured.
  - Queries Support module for serial line configuration via SWI 0x5AA88.
  - Loads BlockDrivers and initialises ports on startup.
  - Polls for carrier detect (DCD) and pumps data between serial port and Pipes module.
  - Sends `MESSAGE_SERIAL_CONNECT` (0x5AA06) and `MESSAGE_SERIAL_DISCONNECT` (0x5AA07) Wimp messages to Server for UI updates.
  - Responds to `MESSAGE_LINE_BROADCAST` (0x5AA00) reason 0 for quit.
  - **Serial Driver Keywords**:
    - `driver <name>`: BlockDriver module name (e.g., InternalPC, Internal32, Dual, Atomwide, etc.)
    - `port <n>`: Port number for multi-port drivers (0-based)
    - `speed <baud>`: Baud rate (300-115200)
    - `format <fmt>`: Word format: `8N1`, `7N1`, `7N2`, `7E1`, `7O1`, `8E1`, `8O1`, `8N2`
    - `flow <type>`: Flow control: `none`, `rts` (RTS/CTS), `xon` (XON/XOFF), `dtr` (DTR/DSR)
  - **BlockDriver Functions Used** (`Serial/c/serial`):
    - `DRIVER_PUTBYTE` (0) / `DRIVER_GETBYTE` (1): Single byte I/O
    - `DRIVER_PUTBLOCK` (2) / `DRIVER_GETBLOCK` (3): Block I/O
    - `DRIVER_CHECKTX` (4) / `DRIVER_CHECKRX` (5): Check buffer status
    - `DRIVER_FLUSHTX` (6) / `DRIVER_FLUSHRX` (7): Flush buffers
    - `DRIVER_MODEMCONTROL` (9): Read modem control lines (CTS/DSR/RI/DCD)
    - `DRIVER_TXSPEED` (13) / `DRIVER_RXSPEED` (14): Set baud rates
    - `DRIVER_WORDFORMAT` (15): Set data bits, parity, stop bits
    - `DRIVER_FLOWCONTROL` (16): Set handshaking mode
    - `DRIVER_INITIALISE` (17): Initialize port
    - `DRIVER_CLOSEDOWN` (18): Close port
    - `DRIVER_POLL` (19): Poll driver (cooperative multitasking)
  - **Modem Control Line Bits** (from function 9, per BlockDriver Spec v2.31):
    - Bit 0 = CTS (Clear To Send)
    - Bit 1 = DSR (Data Set Ready)
    - Bit 2 = RI (Ring Indicator)
    - Bit 3 = DCD (Data Carrier Detect)
  - **Flow Control Values** (for function 16):
    - 0 = None, 1 = RTS/CTS, 2 = XON/XOFF, 3 = DTR/DSR
  - **Word Format Encoding** (for function 15):
    - Bits 0-1 = data length (0=8, 1=7, 2=6, 3=5)
    - Bit 2 = stop bits (0=1 stop, 1=2 stop)
    - Bit 3 = parity enable, Bit 4 = even parity
  - **Carrier Detection**: Serial lines detect carrier via DCD (bit 3 of modem status). When carrier drops, the line is disconnected and the port is reinitialized for the next connection.

- **LineTask / Script Engine**:
  - Scripts live under `<Converse$Dir>.BBS` and are parsed/executed by `LineTask/c/script`. Use backtick quoting for multi-word literals and `%{macro}` for runtime substitutions. Comments use C-style `/* comment */` syntax (NOT semicolons).
  - **Escape Sequences**: String literals support these escapes: `\r\n` or `\n` (newline), `\r` (carriage return), `\t` (tab), `\\` (literal backslash), `` \` `` (literal backtick). Unrecognized escapes like `\_` or `\/` are preserved literally, making ASCII art safe in print statements.
  - The interpreter exposes host callbacks for time, line info, doors, disconnect, and **`DOING <text>`**, which emits message `0x5AA01` so the server can show per-line activity (text is capped to ~96 bytes). `DOING` accepts macros/escapes; send an empty string to reset to the default "no activity" label.
  - **Authentication**: The `LOGON` script command prompts for username/password and authenticates via Filer SWI 0x5AA41. On success, it stores user_id, access_level, and keys in the task state, updates the Support module line state, and sends a `MESSAGE_LINE_USER` (0x5AA05) Wimp message to update the Server's status window.
  - **New User Registration**: The `NEWUSER` script command guides users through account creation. It prompts for: username (3-31 chars, checked for availability), password (4-31 chars, confirmed), real name (2-63 chars), and email (optional). Shows summary and asks for Y/N confirmation before creating the account via Filer SWI 0x5AA41. Empty username cancels. New accounts get sensible defaults: ANSI terminal, ZMODEM, 60 min/day, access level 10.
  - **ONLINE command**: Shows all connected users with real name, online time, and activity. Queries Support module for line state and Filer userdb for user details. Sysops are tagged with `[SYSOP]`.
  - **Filebase Support** (`LineTask/c/filebase`): Provides `FILEBASE` script command for browsing/downloading files. Uses Filer SWIs at 0x5AA43. Commands: `list`, `select <id>`, `areas`, `area <id>`, `files`, `info <file_id>`, `download <file_id>`, `reset`. Access controlled by user level and keys.
  - **Messagebase Support** (`LineTask/c/messagebase`): Provides `MESSAGEBASE` script command for reading and posting messages. Uses Filer SWIs at 0x5AA42. Commands: `list`, `select <id>`, `areas`, `area <id>`, `messages`, `read [id]`, `info <id>`, `compose`, `inbox`, `reset`. Supports local message areas, private user mail, FTN echomail, and FTN netmail. Access controlled by user level, keys, and area type.
  - **Continuous Message Reader**: The `messagebase messages` command enters a continuous reader (like ArmBBS) instead of showing a table listing. Starts at the newest unread message or first message if all read. Messages are marked as read automatically when viewed. Header format:
    ```
    Area    : General Discussion (003)
    Message : #514320 (Read 86 times, 191 bytes)
    Date    : 25 Jun 23 21:00:12
    From    : Username
    To      : All
    Subject : Test Subject
    ```
    Navigation keys:
    - Enter/Space/N: Next message (in current direction)
    - F: Set direction to Forward
    - B: Set direction to Backward  
    - C: Re-display current message
    - S: Go to Start of area (first message)
    - E: Go to End of area (last message)
    - +: Next area in messagebase
    - -: Previous area in messagebase
    - R: Reply (public)
    - P: Private reply
    - A: Abort (return to menu)
  - **Private Inbox**: The `messagebase inbox` command auto-selects the Private area (areatype 4) and enters the continuous reader. Saves/restores the user's previous messagebase/area selection when done.
  - **Area Type Filtering**: Private (areatype 4) and Netmail (areatype 2) areas only show messages where `receivedby == user_id`. This creates a personal inbox - users only see mail addressed to them, not mail they sent or mail for others. Public/Local (areatype 0) and Echo (areatype 1) areas show all messages to everyone.
  - **Direct Mail Commands**: `SENDMAIL <username> <subject> <body>` sends a private message to a local user (requires Private area configured). `SENDNETMAIL <address> <name> <subject> <body>` queues a netmail to an FTN address for export (requires Netmail area configured). Both commands support macro expansion and backtick quoting. Use `\r\n` in body for line breaks. Netmail is exported when the FTN mailer runs Scan.
  - **File Transfers**: See "File Transfer System" section below for full architecture. Script commands: `SENDFILE <file_id> [protocol]` for downloads, `RECEIVEFILE [filename] [protocol]` for uploads. Currently implements XMODEM-CRC. The `transfer_active` flag in Support module prevents idle timeout during transfers.
  - **Math Commands**: `ADD`, `SUB`, `MUL`, `DIV`, `MOD` perform integer arithmetic. Syntax: `add result op1 op2`. Division/modulo by zero returns 0.
  - **Random Numbers**: `RANDOM result min max` generates integer in [min, max] range inclusive.
  - **String Operations**: `STRLEN result source` stores length of source variable's value. `HASKEY result key` checks if user has access key.
  - **Terminal Detection**: `DETECTANSI result [timeout_ms]` sends ANSI DSR query (ESC[6n) and waits for cursor position report. Sets result to "1" if ANSI terminal detected, "0" if timeout (default 3000ms). The `ansi` variable is set in Prelogon and available throughout the session.
  - **Visual Control**: `FLASH <0|1>` toggles the blinking text attribute state. `BOLD` enables bold/bright ANSI attribute. `STD` resets all attributes to white on black with no bold/flash. `ANYKEY [file]` displays a "Press any key" prompt, optionally loading a custom ANSI file (default: `<Converse$Dir>.BBS.Menus.Anykey` or internal fallback). `MORE <0|1>` temporarily disables (0) or enables (1) the "More?" prompt for the current session, overriding the user's preference.
  - **Input Commands**: `PROMPT varname mode echo` requests input (mode: `char`/`line`, echo: `echo`/`noecho`). `READLINE varname [echo|noecho]` is shorthand for `prompt varname line echo`. `YESNO varname` waits for Y/y/N/n keypress and stores "1" or "0".
  - **Loop Commands**: FOR, WHILE, BREAK, CONTINUE provide structured iteration:
    - `FOR var = start TO end [STEP n]` ... `ENDFOR` or `NEXT`: Counts from start to end (inclusive). STEP defaults to 1. Negative STEP counts down. Variable is updated each iteration.
    - `WHILE condition` ... `ENDWHILE`: Repeats while condition is true. Uses same condition syntax as IF (supports `==`, `!=`, `>`, `<`, `>=`, `<=`, `&&`, `||`).
    - `BREAK`: Exits innermost loop immediately, continuing after ENDFOR/ENDWHILE.
    - `CONTINUE`: Skips to next iteration. For FOR loops, goes to ENDFOR (increment happens). For WHILE loops, goes to condition re-test.
    - Loops can be nested up to 16 levels deep.
    - Example FOR: `for i = 1 to 10` ... `print %{i}` ... `endfor`
    - Example WHILE: `set x 1` ... `while x <= 100` ... `mul x %{x} 2` ... `endwhile`
    - Example BREAK: `for i = 1 to 100` ... `if i == 50 then` `break` `end if` ... `endfor`
    - Example CONTINUE: `for i = 1 to 10` ... `mod r %{i} 2` ... `if r == 1 then` `continue` `end if` ... `print %{i}` ... `endfor`
  - **More Prompts**: When enabled (user's `more` flag = 1), the script engine automatically pauses after displaying `lines` lines of output (default 24) and shows a "More?" prompt in reverse video. Any key continues; Q/N/Ctrl+C aborts and disables further prompts for the session. The line counter resets on CLS. Use `more 0` in scripts to disable prompts during file listings or other bulk output.
    - **Implementation**: Uses `script_state` fields: `more_override` (-1=not set, 0=disabled, 1=enabled), `more_line_count` (current line count), `more_screen_lines` (user's configured screen height).
    - **Status**: When awaiting More? response, script status is `SCRIPT_STATUS_WAIT_MORE`.
    - **Output Counting**: `script_write_output()` counts newlines via `script_count_lines()` and triggers pause when `more_line_count >= more_screen_lines - 1`.
  - **Subscript Calls**: `SCRIPT <path>` loads and executes a subscript, then returns to the calling script. Supports up to 8 levels of nesting. Variables are shared between calling and called scripts. Use `return` or `stop` in the subscript to return early. Block IF/ELSE/ENDIF structures are fully supported in subscripts. Example: `script `<Converse$Dir>.BBS.Welcome``.
  - **Login Scan**: `LOGINSCAN` scans all accessible messagebases and filebases for new content since the user's last scan. Reports counts of new private messages addressed to the user (unread, by `receivedby` field) and new files uploaded since `lastscan`. After scanning, updates the user's `lastscan` timestamp in USER_STATS. Typically called in Postlogon script.
  - **System Macros**: `%{accesslevel}`, `%{userid}`, `%{registered}` (1 if logged in), `%{sysop}` (1 if sysop), `%{keys}` (user's key string), `%{hour}`, `%{minute}`, `%{dayofweek}` (0=Sun..6=Sat), `%{day}` (1-31), `%{month}` (1-12), `%{year}` (e.g., 2025).
  - **Selection Macros**: `%{filebaseid}`, `%{filebasename}`, `%{filebaseareaid}`, `%{filebaseareaname}`, `%{messagebaseid}`, `%{messagebasename}`, `%{messagebaseareaid}`, `%{messagebaseareaname}`. Returns current user's selected filebase/messagebase and area IDs and names. Returns empty string or 0 if nothing selected.
  - **User History Persistence**: When a user selects a filebase/messagebase/area via script commands, the selection is automatically saved to their `USER_HISTORY` record in the userdb. On next login, these selections are restored to the session state automatically.
  - **Conditional Operators**: IF command supports `==`, `!=` (string), `>`, `<`, `>=`, `<=` (numeric). Both operands are macro-expanded. Compound conditions supported with `&&` (AND) and `||` (OR): `if %{day} == 25 && %{month} == 12 goto christmas`.

  - **LineTask / Terminal (`ansiterm`)**:
    - **Architecture**: The `ansiterm` module implements a custom ANSI terminal emulator. It maintains a grid of cells and handles rendering to a RISC OS window.
    - **Terminal Dimensions**: Standard 80x25 character grid (defined in `LineTask/h/ansiterm`):
      - `ANSITERM_COLS` = 80, `ANSITERM_ROWS` = 25
      - `ANSITERM_CHAR_WIDTH` = 16, `ANSITERM_CHAR_HEIGHT` = 32 (OS units per cell)
      - `ANSITERM_WIDTH` = 1280, `ANSITERM_HEIGHT` = 800 (total OS units)
    - **Window Opening**: The `show_main_window()` function opens the terminal at full 80x25 size, centered on screen. It calculates screen dimensions via `OS_ReadModeVariable` and explicitly sets the visible area to match the terminal extent, rather than relying on template defaults.
    - **Cell Structure**: `ansiterm_cell` uses a 16-bit attribute field (`unsigned short attr`) to support standard colors (FG/BG) plus a **Flash** bit (bit 8).
    - **Blinking Text**: The `ansiterm_blink()` function toggles the visibility of flashing characters. It uses an optimized row-scanning approach to only invalidate/redraw rows containing flashing characters, preventing full-window flicker. This is driven by a 0.5s timer in `main.c`.
    - **Control Characters**: Strictly matches ArmBBS reference handling:
      - `BS` (8): Backspaces, clamping at column 0.
      - `TAB` (9): Jumps to next 8-char tabstop, clamping at column 79.
      - `LF` (10) / `VT` (11): Moves cursor down, scrolling if at bottom.
      - `FF` (12): Triggers Clear Screen (`ansiterm_clear`) if byte is exactly 12, otherwise treats as line feed.
      - `CR` (13): Returns cursor to column 0.
    - **ANSI Support**: Robust `ESC[...]` parser.
      - `ESC[m` and `ESC[0m` correctly trigger full attribute reset.
      - Supports cursor movement (`A`,`B`,`C`,`D`,`H`,`f`), clearing (`J`,`K`), scrolling (`L`,`M`), and device status (`6n`).
    - **Sysop Snoop**: The terminal window mirrors the user's session.
      - **Output**: `pipes_output_write_string` feeds all data sent to the user (scripts, files, menus) into the local terminal emulator.
      - **Input**: `handle_plain_server_byte` echoes user input to the local terminal.
      - **Sysop Input**: `handle_terminal_key` injects local keystrokes into the input stream (local echo handled by `pipes_output_write_string` when the server echoes it back, or locally if needed).
    - **Focus**: The terminal window automatically claims input focus (`Wimp_SetCaretPosition`) when opened via the "View" button in the Server.

- **LineTask / Script Call Stack**:
  - **Purpose**: Supports `SCRIPT` command for subscript nesting up to 8 levels deep.
  - **Structure**: `script_call_frame` array stores saved script state (path, line number, file pointer, block stack) for each nesting level. `call_depth` tracks current depth (0 = top-level script).
  - **Push/Pop**: `script_push_call_stack()` saves current state before loading subscript. `script_pop_call_stack()` restores parent state when subscript ends via `RETURN` or EOF.
  - **Session Cleanup**: The call stack is cleared in `script_reset_session()` (called only on disconnect), NOT in `script_stop()`. This is critical because `script_stop()` is also called internally when loading subscripts, so clearing the stack there would break subscript support.
  - **Overflow Protection**: If `call_depth >= MAX_CALL_DEPTH` (8), the `SCRIPT` command fails with "[Script Error: Script stack overflow]".

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
| `MESSAGE_SERIAL_CONNECT` | 0x5AA06 | Serial->Server | Serial line connected (word[0]=line) |
| `MESSAGE_SERIAL_DISCONNECT` | 0x5AA07 | Serial->Server | Serial line disconnected (word[0]=line) |

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
    int exported;
    unsigned short flags; /* MSG_FLAG_* routing flags */
} MESSAGE_RECORD;

/* Message routing flags (bit flags) */
#define MSG_FLAG_PRIVATE    0x0001  /* Private message */
#define MSG_FLAG_CRASH      0x0002  /* Crash priority (send immediately) */
#define MSG_FLAG_HOLD       0x0004  /* Hold for pickup only */
#define MSG_FLAG_DIRECT     0x0008  /* Direct delivery, no routing */
#define MSG_FLAG_IMMEDIATE  0x0010  /* Immediate priority (highest) */
#define MSG_FLAG_KILLSENT   0x0020  /* Delete after sending */
#define MSG_FLAG_FILE_ATTACH 0x0040 /* Has file attachment */
#define MSG_FLAG_FILE_REQUEST 0x0080 /* File request */
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
  - 8 (EnumerateBases): R1=Index -> R0=RecordPtr or -1
  - 9 (EnumerateAreas): R1=BaseID, R2=Index -> R0=AreaRecordPtr or -1
  - 10 (EnumerateMessages): R1=BaseID, R2=AreaID (0=all), R3=Index -> R0=RecordPtr or -1
  - 11 (MessageInfo): R1=BaseID, R2=MsgID -> R0=RecordPtr
  - 12 (SaveMessageRecord): R1=BaseID, R2=RecordPtr -> R0=Success(1)/Failure(0)
  - 13 (FindUnexported): R1=BaseID, R2=AreaID, R3=Buffer, R4=MaxCount -> R0=Count
  - 14 (MarkExported): R1=BaseID, R2=MsgID -> R0=Success(1)/Failure(0)
  - 15 (EndUpload): R1=BaseID, R2=MsgID -> R0=0 (flushes/closes cached file handle)
- **Filebase (0x5AA43)**:
  - 0 (Create): R1=BaseRecord -> R0=ID
  - 1 (Update): R1=ID, R2=BaseRecord
  - 2 (Info): R1=ID -> R0=RecordPtr
  - 3 (BeginUpload): R1=ID, R2=ItemRecord -> R0=ItemID
  - 4 (UploadBlock): R1=ID, R2=ItemID, R3=Data, R4=Len
  - 5 (DownloadBlock): R1=ID, R2=ItemID, R3=Buf, R4=Off, R5=Len
  - 6 (StoreArea): R1=ID, R2=AreaRecord -> R0=AreaID
  - 7 (AreaInfo): R1=ID, R2=AreaID -> R0=AreaRecordPtr
  - 8 (EnumerateBases): R1=Index -> R0=RecordPtr or -1
  - 9 (EnumerateAreas): R1=BaseID, R2=Index -> R0=AreaRecordPtr or -1
  - 10 (EnumerateFiles): R1=BaseID, R2=AreaID (0=all), R3=Index -> R0=RecordPtr or -1
  - 11 (FileInfo): R1=BaseID, R2=FileID -> R0=RecordPtr
  - 12 (EndUpload): R1=BaseID, R2=FileID -> R0=0 (flushes/closes cached file handle)
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
  - Fields: 0=configured, 1=connected, 2=user_id, 3=connect_time, 4=hostname, 5=transfer_active, 6=line_type (0=telnet,1=serial,2=local)
- **Activity (0x5AA82)**:
  - 0 (Set): R1=Line, R2=TextPtr
  - 1 (Get): R1=Line -> R0=TextPtr
- **LineConfig (0x5AA83)**:
  - 0 (Set): R1=Line, R2=Field, R3=Value
  - 1 (Get): R1=Line, R2=Field -> R0=Value
  - Fields: 0=enabled, 1=botstopper (char*), 2=hello (char*)
- **MsgBaseConfig (0x5AA84)**:
  - 0 (GetGlobal): -> R0=MSGBASE_GLOBAL_CONFIG ptr
  - 1 (SetGlobal): R1=Field (0=retention, 1=accesslevel, 2=storage_root, 3=origin), R2=Value
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
  - 8 (GetDownlink): R1=DownlinkID -> R0=FTN_DOWNLINK_CONFIG ptr
  - 9 (SetDownlink): R1=DownlinkID, R2=FTN_DOWNLINK_CONFIG ptr
  - 10 (CountDownlinks): -> R0=Count
  - 11 (GetDomain): R1=DomainID -> R0=FTN_DOMAIN_CONFIG ptr
  - 12 (SetDomain): R1=DomainID, R2=FTN_DOMAIN_CONFIG ptr
  - 13 (CountDomains): -> R0=Count
  - 14 (FindDomainByName): R1=NamePtr -> R0=FTN_DOMAIN_CONFIG ptr or 0
  - 15 (FindDomainByZone): R1=Zone -> R0=FTN_DOMAIN_CONFIG ptr or 0
- **SerialConfig (0x5AA88)**:
  - 0 (Get): R1=Line -> R0=SERIAL_CONFIG ptr
  - 1 (Set): R1=Line, R2=SERIAL_CONFIG ptr
  - SERIAL_CONFIG contains: enabled (int), driver_name (char[32]), port_number (int), baud_rate (int), word_format (int), flow_control (int)

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
Use `call arcbbsdoor <door_number> <command> [26bit]` in scripts:
```
call arcbbsdoor 4 `<Converse$Dir>.BBS.Doors.ARCbbs.!SnakeDoor %{line}`
```
The door number must match the door's configured `DoorNumber` (usually in its `Config` file).
Add the optional `26bit` keyword to run legacy 26-bit doors via Aemulor.

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
Use `call door <command> [26bit]` in scripts:
```
call door `<Converse$Dir>.BBS.Doors.MyDoor %{line}`
```
The door receives the line number as a command-line argument and registers itself.
Add the optional `26bit` keyword to run legacy 26-bit doors via Aemulor.

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

## 26-bit Door Support (Aemulor)

### Overview
Legacy 26-bit doors (compiled for RISC OS 3.x and earlier) can be run on 32-bit RISC OS systems using the Aemulor module. Converse BBS supports this via the optional `26bit` keyword on door script commands.

### Requirements
- **Aemulor** module must be loaded (available from R-Comp at https://www.rcomp.co.uk/)
- LineTask checks for Aemulor presence using `OS_Module 18` before launching

### Script Syntax
Add the `26bit` keyword at the end of any door command to run it via Aemulor:

**Native doors:**
```
call door `<Converse$Dir>.BBS.Doors.MyOldDoor %{line}` 26bit
```

**ARCbbs doors:**
```
call arcbbsdoor 4 `<Converse$Dir>.BBS.Doors.ARCbbs.!SnakeDoor %{line}` 26bit
```

**RiscBBS doors:**
```
call riscbbsdoor `<Converse$Dir>.BBS.Doors.RiscBBS.OldDoor %{line}` 26bit
```

### How It Works
1. Script parser detects `26bit` keyword in the final argument position
2. Host callback receives `use_26bit` flag
3. If `use_26bit` is set, LineTask calls `is_aemulor_loaded()` via `OS_Module 18`
4. If Aemulor is present, the command is prefixed with `AemuExecute `
5. Door is launched with Wimp_StartTask as normal

### Error Handling
If `26bit` is specified but Aemulor is not loaded, the user sees:
```
[26-bit door requires Aemulor module]
```
and the door launch is aborted.

### Implementation Details
```c
/* Check if Aemulor module is loaded */
static int is_aemulor_loaded(void)
{
    _kernel_swi_regs regs;
    regs.r[0] = 18;  /* OS_Module reason: Lookup */
    regs.r[1] = (int)"Aemulor";
    return (_kernel_swi(0x1E, &regs, &regs) == NULL) ? 1 : 0;
}

/* If 26bit flag set and Aemulor available, prepend AemuExecute */
if (use_26bit && is_aemulor_loaded())
{
    snprintf(final_command, sizeof(final_command), "AemuExecute %s", command_line);
}
```

## File Transfer System

### Overview
The file transfer system enables users to download files from filebases and upload files to the BBS using standard protocols. The implementation spans multiple modules with careful handling of telnet binary transparency.

**Current Status:**
- ✅ XMODEM-CRC: Fully implemented and working (downloads and uploads)
- 🔲 XMODEM (checksum): Not yet implemented
- 🔲 XMODEM-1K: Not yet implemented  
- 🔲 YMODEM: Not yet implemented
- 🔲 YMODEM-G: Not yet implemented
- 🔲 ZMODEM: Not yet implemented

### Architecture

**Components:**
| Module | File | Purpose |
|--------|------|---------|
| LineTask | `c/xmodem` | XMODEM protocol state machine |
| LineTask | `c/transfer` | Transfer session management, file I/O |
| LineTask | `c/script` | SENDFILE/RECEIVEFILE command handlers |
| LineTask | `c/main` | Host callbacks, transfer initiation |
| Server | `c/main` | Telnet IAC handling, socket↔pipe pumping |
| Support | SWI 0x5AA81 | `transfer_active` flag (field 5) |
| Filer | SWI 0x5AA43 | File data read/write via reason 5 |

**Data Flow (Download):**
```
Filer DB → transfer.c → xmodem.c → Pipes Output → Server pump → Socket
                                                      ↓
                                            IAC doubling (0xFF → 0xFF 0xFF)
```

**Data Flow (Upload):**
```
Socket → Server pump → Pipes Input → xmodem.c → transfer.c → Temp File → Filer DB
              ↓
    IAC un-doubling (0xFF 0xFF → 0xFF)
```

### CRITICAL: Telnet Binary Transparency

File transfers over telnet require special handling of the IAC byte (0xFF). This is the **most important implementation detail** and the cause of many subtle bugs.

#### The Problem
Telnet uses 0xFF (IAC - Interpret As Command) as an escape byte. When binary file data contains 0xFF:
- **Without handling**: The telnet client/server interprets it as a command, corrupting data
- **Result**: CRC mismatches, transfer failures, data corruption

#### The Solution

**OUTPUT (Downloads - BBS → User):**
In `Server/c/main` function `pump_pipe_to_socket()`:
- Every 0xFF byte must be doubled to 0xFF 0xFF before sending to socket
- The user's terminal un-doubles them automatically
- Buffer must be 2x size to handle worst case (all 0xFF data)

```c
/* In pump_pipe_to_socket() */
if (transfer_active)
{
    /* Double all IAC (0xFF) bytes for telnet transparency */
    for (i = 0; i < copied; i++)
    {
        unsigned char byte = (unsigned char)buffer[i];
        send_buffer[send_len++] = byte;
        if (byte == 0xFF)
        {
            send_buffer[send_len++] = 0xFF;  /* Double it */
        }
    }
}
```

**INPUT (Uploads - User → BBS):**
In `Server/c/main` function `pump_socket_to_pipe()`:
- User's terminal doubles 0xFF bytes when sending binary data
- We must un-double them: 0xFF 0xFF → single 0xFF
- Must NOT strip NUL bytes (normal telnet filter does this)

```c
/* Binary-safe IAC un-doubling for file transfers */
static int telnet_undouble_iac(char *buffer, int length)
{
    int read_index = 0;
    int write_index = 0;

    while (read_index < length)
    {
        unsigned char byte = (unsigned char)buffer[read_index++];

        if (byte == 0xFF && read_index < length && 
            (unsigned char)buffer[read_index] == 0xFF)
        {
            read_index++;  /* Skip the doubled byte */
        }

        buffer[write_index++] = (char)byte;
    }

    return write_index;
}
```

**Usage in pump_socket_to_pipe():**
```c
if (transfer_active)
{
    read_bytes = telnet_undouble_iac(buffer, read_bytes);
}
else
{
    read_bytes = telnet_filter_input(socket, buffer, read_bytes);
}
```

#### Why Two Different Functions?

| Function | Used When | Strips NUL | Handles IAC | Handles Commands |
|----------|-----------|------------|-------------|------------------|
| `telnet_filter_input()` | Normal text mode | Yes | Yes | Yes |
| `telnet_undouble_iac()` | File transfers | No | Yes | No |

Binary files often contain NUL (0x00) bytes. The normal telnet filter strips these (telnet sends CR-NUL for plain carriage return). For file transfers, we must preserve all bytes.

### XMODEM-CRC Implementation

**Source Files:**
- `LineTask/c/xmodem` - Protocol state machine
- `LineTask/h/xmodem` - Constants and structures

#### Protocol Constants
```c
#define XMODEM_SOH          0x01    /* Start of 128-byte block */
#define XMODEM_STX          0x02    /* Start of 1024-byte block (1K) */
#define XMODEM_EOT          0x04    /* End of transmission */
#define XMODEM_ACK          0x06    /* Acknowledge */
#define XMODEM_NAK          0x15    /* Negative acknowledge */
#define XMODEM_CAN          0x18    /* Cancel transfer */
#define XMODEM_CTRLZ        0x1A    /* Padding byte */

#define XMODEM_BLOCK_SIZE   128     /* Standard block size */
#define XMODEM_MAX_RETRIES  10      /* Retries per block */
```

#### Block Format (133 bytes for CRC mode)
```
[SOH] [Block#] [~Block#] [128 data bytes] [CRC-Hi] [CRC-Lo]
  1      1         1           128            1        1
```

- Block# starts at 1, wraps at 256 back to 0
- ~Block# is 255 - Block# (complement for validation)
- CRC-16: Polynomial 0x1021 (CCITT), init=0, sent MSB first

#### CRC-16 Calculation
```c
static const uint16_t crc16_table[256]; /* Precomputed */

uint16_t xmodem_crc16(const uint8_t *data, int length)
{
    uint16_t crc = 0;
    while (length--) {
        crc = (crc << 8) ^ crc16_table[(crc >> 8) ^ *data++];
    }
    return crc;
}
```

#### Send State Machine (Downloads)
```
XMODEM_STATE_WAIT_START     Wait for 'C' (CRC mode) from receiver
XMODEM_STATE_SEND_BLOCK     Build and send packet
XMODEM_STATE_WAIT_ACK       Wait for ACK (advance) or NAK (retry)
XMODEM_STATE_SEND_EOT       Send EOT after last block
XMODEM_STATE_WAIT_EOT_ACK   Wait for final ACK
XMODEM_STATE_COMPLETE       Transfer done
XMODEM_STATE_ERROR          Transfer failed
```

#### Receive State Machine (Uploads)
```
XMODEM_STATE_SEND_START     Send 'C' to request CRC mode
XMODEM_STATE_WAIT_BLOCK     Wait for SOH/EOT
XMODEM_STATE_READ_BLOCK     Read remaining 132 bytes
XMODEM_STATE_VALIDATE       Check block# and CRC
XMODEM_STATE_SEND_ACK       ACK good block, write to file
XMODEM_STATE_SEND_NAK       NAK bad block for retry
XMODEM_STATE_COMPLETE       EOT received, transfer done
XMODEM_STATE_ERROR          Transfer failed
```

#### Key Implementation Functions

```c
/* Initialize send transfer */
int xmodem_start_send(int line, int filebase_id, int file_id,
                      const char *filename, xmodem_session *session);

/* Initialize receive transfer */
int xmodem_start_receive(int line, const char *dest_path,
                         xmodem_session *session);

/* Poll state machine (called from main loop) */
int xmodem_poll_send(xmodem_session *session);
int xmodem_poll_receive(xmodem_session *session);

/* Check if transfer complete */
int xmodem_is_complete(xmodem_session *session);
int xmodem_is_error(xmodem_session *session);
```

### Script Commands

#### SENDFILE (Downloads)
```
sendfile <file_id> [protocol]
```
- `file_id`: File ID from current filebase selection
- `protocol`: `xmodem`, `xmodem-crc` (default), `xmodem-1k`, `ymodem`, `ymodem-g`, `zmodem`

**Implementation (`LineTask/c/script`):**
1. Parse file_id and protocol from arguments
2. Call `state->host.start_transfer(line, protocol, file_id)` callback
3. Set `state->status = SCRIPT_STATUS_WAIT_TRANSFER`
4. Script execution pauses until transfer completes

#### RECEIVEFILE (Uploads)
```
receivefile [filename] [protocol]
```
Three modes based on arguments provided:
- No arguments: Prompt for filename, description, and protocol
- Protocol only: Prompt for filename and description
- Filename and protocol: Prompt for description only

**Implementation:**
1. Determine which arguments are provided
2. Set `input_context` to `CTX_UPLOAD_FILE`, `CTX_UPLOAD_DESC`, or `CTX_PROTOCOL`
3. Collect missing information via prompts
4. Call `state->host.start_receive_transfer()` callback
5. On completion, file is moved from temp location to filebase

### Transfer Session Management

**Session Structure (`LineTask/h/transfer`):**
```c
typedef struct {
    int line;                   /* Line number */
    int protocol;               /* Protocol enum value */
    int filebase_id;            /* Filebase for download/upload */
    int file_id;                /* File ID (downloads) */
    char filename[256];         /* Display filename */
    char temp_path[256];        /* Temp file path (uploads) */
    char description[256];      /* File description (uploads) */
    long file_size;             /* Total bytes */
    long bytes_transferred;     /* Progress */
    int state;                  /* Protocol state machine state */
    int block_number;           /* Current block */
    int retry_count;            /* Retries for current block */
    int use_crc;                /* Using CRC mode (vs checksum) */
    uint8_t buffer[1024];       /* Block buffer */
    int buffer_pos;             /* Position in buffer */
    unsigned long timeout;      /* Timeout timestamp */
} transfer_session;
```

**Temp File Paths:**
- Uploads go to: `<Converse$Dir>.Temp.Upload_<line>_<timestamp>`
- On success: Moved to filebase via Filer SWI
- On failure: Deleted

### Support Module Integration

**transfer_active Flag (SWI 0x5AA81, field 5):**
- Set to 1 when transfer starts
- Set to 0 when transfer completes/fails
- Prevents idle timeout during transfers
- Controls telnet IAC handling in Server

```c
/* Set transfer active */
void set_transfer_state(int line, int active)
{
    _kernel_swi_regs regs;
    regs.r[0] = 0;  /* Set reason */
    regs.r[1] = line;
    regs.r[2] = 5;  /* Field: transfer_active */
    regs.r[3] = active;
    _kernel_swi(0x5AA81, &regs, &regs);
}
```

### Adding New Protocols (YMODEM/ZMODEM)

When implementing additional protocols, follow this pattern:

1. **Create protocol source file** (e.g., `LineTask/c/ymodem`)
2. **Implement state machine** with poll function
3. **Handle telnet transparency** - IAC is already handled in Server
4. **Add to script command** - Update protocol parsing in `script.c`
5. **Add host callbacks** - Update `main.c` transfer initiation

**YMODEM Differences from XMODEM:**
- Block 0 contains filename and size (null-terminated string)
- Uses 1K blocks (STX instead of SOH) by default
- Batch mode: multiple files, empty block 0 ends batch
- Receiver sends ACK + 'C' after block 0

**ZMODEM Differences:**
- Streaming protocol (no per-block ACK)
- 32-bit CRC
- ZDLE escape encoding for control characters
- Auto-start with ZRQINIT
- Crash recovery via ZRPOS

### Common Pitfalls

1. **Forgetting IAC handling**: Binary transfers WILL fail without proper 0xFF handling
2. **Stripping NUL bytes**: Use `telnet_undouble_iac()` not `telnet_filter_input()` during transfers
3. **Buffer sizing**: Output buffer needs 2x size for IAC doubling worst case
4. **Timeout handling**: Use `OS_ReadMonotonicTime` (centiseconds), not `time()`
5. **Block number wrapping**: Block# goes 1,2,...,255,0,1,... (wraps at 256)
6. **CRC byte order**: XMODEM CRC is sent MSB first (high byte, then low byte)
7. **Padding**: Last block padded with CTRL-Z (0x1A) if file size not multiple of 128

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
- **Tosser** (`FTN/c/tosser`): Inbound packet processing, echomail/netmail tossing, arcmail extraction
- **Scanner** (`FTN/c/scanner`): Outbound message scanning and routing
- **Packer** (`FTN/c/packer`): Outbound packet creation, arcmail bundling
- **Queue** (`FTN/c/queue`): Outbound file queue management
- **TIC** (`FTN/c/tic`): TIC file processing for file distribution
- **FREQ** (`FTN/c/freq`): File request processing
- **EchoFix** (`FTN/c/echofix`): AreaFix/FileFix subscription management
- **Unzip** (`FTN/c/unzip`): ZIP/DEFLATE extraction for inbound arcmail
- **Zip** (`FTN/c/zip`): ZIP/DEFLATE compression for outbound arcmail

### Arcmail (ZIP) Support
The FTN module includes native ZIP/DEFLATE compression and decompression for handling arcmail bundles.

**Inbound Arcmail (Extraction):**
- Tosser automatically detects arcmail files by extension: `.mo0`-`.su9` (FTN day codes) and `.zip`
- Uses `unzip.c` to extract contained `.pkt` files
- Extracted packets are processed normally, then the arcmail is moved to Processed/
- Supports DEFLATE compression (method 8) and Store (method 0)

**Outbound Arcmail (Creation):**
- `packer_create_arcmail()` compresses a single packet into an arcmail bundle
- `packer_create_arcmail_multi()` bundles multiple packets into one archive
- Uses DEFLATE with fixed Huffman codes for good compression/speed balance
- Day-of-week extensions: `mo0`-`su9` cycling through 0-9

**ZIP Functions (`FTN/h/unzip`, `FTN/h/zip`):**
```c
/* Extraction */
int unzip_open(UNZIP_ARCHIVE *archive, const char *path);
void unzip_close(UNZIP_ARCHIVE *archive);
int unzip_get_entry(UNZIP_ARCHIVE *archive, int index, UNZIP_ENTRY *entry);
int unzip_extract_entry(UNZIP_ARCHIVE *archive, UNZIP_ENTRY *entry, const char *dest_path);
int unzip_extract_to_memory(UNZIP_ARCHIVE *archive, UNZIP_ENTRY *entry, unsigned char *buffer, unsigned long size);
int unzip_is_zip_file(const char *path);

/* Creation */
int zip_create(ZIP_ARCHIVE *archive, const char *path);
int zip_add_file(ZIP_ARCHIVE *archive, const char *src_path, const char *arc_name, int compress);
int zip_add_memory(ZIP_ARCHIVE *archive, const unsigned char *data, unsigned long len, const char *arc_name, int compress);
int zip_close(ZIP_ARCHIVE *archive);
void zip_abort(ZIP_ARCHIVE *archive);

/* Arcmail helpers (packer.h) */
int packer_create_arcmail(const char *packet_path, const FTN_ADDR *dest_addr);
int packer_create_arcmail_multi(const char **packet_paths, int count, const FTN_ADDR *dest_addr);
```

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

### Echomail Origin Lines
When locally posted echomail is exported, the packer adds a tearline and origin line. The origin text is configurable in the MsgBases config file.

**Configuration (`Demo/Config/MsgBases`):**
```
; Multiple origin lines can be specified - one is randomly selected
origin `The Yellow Toaster BBS`
origin `Your friendly neighbourhood BBS`
origin `We're not dead yet!`
```

**Format:**
- Tearline: `---` (just three dashes)
- Origin: ` * Origin: <text> (<zone:net/node[.point]>)`

**Example output:**
```
---
 * Origin: The Yellow Toaster BBS (2:250/1.0)
```

**Behaviour:**
- Only locally posted messages get tearline/origin added
- Forwarded echomail retains its original tearline/origin
- The FTN address uses the area's `akause` setting to pick the correct AKA
- If no origins are configured, falls back to `system_name` from FTN config
- Random selection uses `time(NULL) % origin_count`

**Implementation:**
- Origins stored in Support module via `MSGBASE_GLOBAL_FIELD_ORIGIN` (field 3)
- Max 16 origins, 128 chars each
- `PACKER_MESSAGE.is_local` flag controls whether to add tearline/origin
- Locally posted messages have empty origin address in MESSAGE_RECORD (zone=0, net=0)

### Multi-Network Domain Support
The FTN module supports multiple FTN networks (e.g., Fidonet, CNet, RetroNet) with separate inbound/outbound directories per network. This is achieved through domain configuration blocks.

**Domain Structure (`FTN_DOMAIN_CONFIG`):**
```c
typedef struct {
    int id;                      /* Domain ID (0-based) */
    char name[32];               /* Domain name (e.g., "fidonet") */
    char inbound[256];           /* Inbound path for this domain */
    char outbound[256];          /* Outbound path for this domain */
    int default_zone;            /* Default zone (for matching addresses) */
    int idomain;                 /* Internal domain ID for 5D addressing */
    int alias_for;               /* Domain ID this is an alias for (0=not alias) */
} FTN_DOMAIN_CONFIG;
```

**Configuration (`BBS/Config/FTN`):**
```
domain 1
    name            fidonet
    zone            2
    inbound         <Converse$Dir>.FTN.Inbound.Fidonet
    outbound        <Converse$Dir>.FTN.Outbound.Fidonet
enddomain

domain 2
    name            cnet
    zone            64
    inbound         <Converse$Dir>.FTN.Inbound.Cnet
    outbound        <Converse$Dir>.FTN.Outbound.Cnet
enddomain
```

**Directory Structure with Domains:**
```
<Converse$Dir>.FTN/
├── Inbound/
│   ├── Fidonet/
│   │   └── 002/
│   │       ├── Temp/
│   │       ├── Processed/
│   │       └── Bad/
│   ├── Cnet/
│   │   └── 040/
│   └── ... (other domains)
├── Outbound/
│   ├── Fidonet/
│   │   └── 002/
│   ├── Cnet/
│   │   └── 040/
│   └── ... (other domains)
└── Netmail/
```

**Address to Domain Matching:**
When routing mail or receiving files, the mailer determines the domain by:
1. Check the address's `domain` field (5D addressing)
2. If empty, look up domain by zone number via `ftn_get_domain_for_addr()`
3. Fall back to legacy global paths if no domain matches

**Key Functions (`FTN/c/mailer`):**
```c
/* Address matching - includes domain comparison */
int ftn_addr_match(const FTN_ADDR *a, const FTN_ADDR *b);
int ftn_addr_match_ignore_domain(const FTN_ADDR *a, const FTN_ADDR *b);

/* Domain lookup */
FTN_DOMAIN_CONFIG *ftn_get_domain_for_addr(const FTN_ADDR *addr);
int ftn_get_inbound_for_addr(const FTN_ADDR *addr, char *buffer, size_t size);
int ftn_get_outbound_for_addr(const FTN_ADDR *addr, char *buffer, size_t size);
void ftn_expand_address(FTN_ADDR *addr);
```

**Backward Compatibility:**
- If no domains are configured, the mailer uses the legacy global `inbound`/`outbound` paths
- The queue scanner checks for domains first, then falls back to legacy paths
- Existing single-network configurations continue to work unchanged

### TIC File Processing
TIC files accompany files in FTN file distribution networks. The TIC module provides
full support for inbound and outbound file echo distribution.

**Directory Structure:**
```
<Converse$Dir>.FTN/
├── Inbound/
│   └── <zone>/
│       ├── Bad/            ← Failed TIC imports (CRC error, unknown area)
│       ├── Processed/      ← Successfully imported files
│       └── Temp/           ← Partial receives
└── Outbound/<zone>/        ← Outbound TIC and attached files
```

**Inbound Processing:**
1. Scans zone inbound directories for `*.tic` files
2. Parses TIC metadata (filename, area, size, CRC, origin, etc.)
3. Verifies file CRC-32 if specified
4. Matches area tag to filebase area (using `tag` field in area config)
5. Stores file via Filer SWI
6. Moves TIC and file to `Processed/` on success, `Bad/` on failure

**Filebase Area Tags:**
To receive TIC files, configure filebase areas with matching FTN file echo tags:
```
filebase 1
    name    Main Files
    area 1
        name    RISC OS Software
        tag     RISCOS_SOFT
    endarea
endfilebase
```
The `tag` field is matched case-insensitively against the TIC file's Area field.

**Outbound TIC Creation:**
The `tic_create_for_file()` function creates TIC files for outbound distribution:
1. Gets file info from Filer (name, description, size)
2. Calculates CRC-32 of the file
3. Populates TIC structure with origin, SEENBY, PATH
4. Writes TIC file to outbound zone directory
5. Queues both file and TIC for sending to destination

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
int scanner_get_message_flags(int base_id, int message_id, unsigned short *flags_out);
SCANNER_FLAVOUR scanner_flags_to_flavour(unsigned short flags);
```

### Message Priority/Flavour
Messages can have priority flags that determine packet placement in BSO:

| Flag | Flavour | BSO Extension | Priority | Description |
|------|---------|---------------|----------|-------------|
| (none) | NORMAL | `out`, `pkt` | Lowest | Send during scheduled poll |
| MSG_FLAG_HOLD | HOLD | `hut`, `hpkt` | Low | Hold for remote pickup only |
| MSG_FLAG_DIRECT | DIRECT | `dut`, `dpkt` | Medium | Direct delivery, no hub routing |
| MSG_FLAG_CRASH | CRASH | `cut`, `cpkt` | High | Send immediately |
| MSG_FLAG_IMMEDIATE | IMMEDIATE | `iut`, `ipkt` | Highest | Interrupt current session |

**RISC OS Note**: File extensions are appended without dots (e.g., `00fa0001pkt`, `00fa0001cpkt` for crash priority).

**Packet Naming**: `<timestamp><prefix>pkt` where prefix is empty for normal, `c` for crash, `h` for hold, etc.

### TIC Functions
```c
int tic_parse_file(const char *tic_path, TIC_FILE *tic);
void tic_free(TIC_FILE *tic);
int tic_process_inbound(void);
int tic_process_single(const char *tic_path, const char *file_path);
int tic_store_file(const TIC_FILE *tic, const char *file_path);
int tic_match_area(const char *area_tag, int *filebase_id, int *filebase_area_id);
int tic_create_for_file(int filebase_id, int file_id, const char *area_tag,
                        const FTN_ADDR *dest, const char *password);
int tic_write_file(const TIC_FILE *tic, const char *tic_path);
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

### Downlinks and EchoFix

#### Overview
Downlinks are points or nodes that we feed echomail/fileecho to. The EchoFix module (`FTN/c/echofix`) handles AreaFix and FileFix requests from downlinks, allowing them to subscribe/unsubscribe from areas.

#### Downlink Configuration
```
; In FTN config
downlink 1
    address         2:250/1.1
    name            Johns Point
    areafix_password    Point1PW
    filefix_password    Point1FilePW
    allowed_groups      A,B
    allowed_echoes      RETROCOMPUTING,RISCOS*
    allowed_files       RISCOS_SOFT
    max_echoes          50
    max_files           10
enddownlink
```

#### Configuration Fields
| Field | Description |
|-------|-------------|
| address | Downlink's FTN address (zone:net/node.point) |
| name | Descriptive name for logging |
| areafix_password | Password for AreaFix requests |
| filefix_password | Password for FileFix requests |
| allowed_groups | Group letters they can subscribe to (A,B,C) |
| allowed_echoes | Specific echo area tags (wildcards supported) |
| allowed_files | Specific fileecho area tags (wildcards supported) |
| max_echoes | Maximum echo subscriptions (0=unlimited) |
| max_files | Maximum fileecho subscriptions (0=unlimited) |

#### EchoFix Request Processing
When a netmail arrives addressed to AreaFix/FileFix/AreaMgr/etc.:
1. Tosser calls `echofix_detect_recipient()` to identify request type
2. If detected, tosser calls `echofix_process_message()` instead of storing
3. EchoFix parses the password and commands from message body
4. Password is validated against downlink configuration
5. Commands are processed (+AREA, -AREA, %LIST, %QUERY, %HELP, etc.)
6. Response netmail is generated and queued for sending

#### Supported Commands
| Command | Description |
|---------|-------------|
| +AREA_TAG | Subscribe to area |
| -AREA_TAG | Unsubscribe from area |
| AREA_TAG | Toggle subscription |
| %LIST | List available areas |
| %QUERY | List current subscriptions |
| %HELP | Show help text |
| %PAUSE | Pause feed (keep subscriptions) |
| %RESUME | Resume paused feed |

#### Subscription Storage
Subscriptions are stored in `<Converse$Dir>.Config.FTNLinks` as a binary file of `ECHOFIX_SUBSCRIPTION` records.

#### EchoFix Functions
```c
/* Initialization */
void echofix_initialise(void);
void echofix_finalise(void);

/* Detection and processing */
ECHOFIX_TYPE echofix_detect_recipient(const char *to_name);
int echofix_process_message(const FTN_ADDR *from, ECHOFIX_TYPE type,
                            const char *subject, const char *body);

/* Subscription management */
int echofix_add_subscription(const FTN_ADDR *addr, const char *area_tag, ECHOFIX_TYPE type);
int echofix_remove_subscription(const FTN_ADDR *addr, const char *area_tag, ECHOFIX_TYPE type);
int echofix_is_subscribed(const FTN_ADDR *addr, const char *area_tag, ECHOFIX_TYPE type);

/* Subscriber queries (for scanner/TIC routing) */
int echofix_get_subscribers(ECHOFIX_TYPE type, const char *area_tag,
                            FTN_ADDR *addrs, int max_addrs);

/* Downlink queries */
ECHOFIX_DOWNLINK_CONFIG *echofix_find_downlink(const FTN_ADDR *addr);
int echofix_downlink_has_access(const ECHOFIX_DOWNLINK_CONFIG *dl, 
                                 const char *area_tag, ECHOFIX_TYPE type);
```

#### Echomail Routing to Downlinks
The scanner (`FTN/c/scanner`) automatically routes echomail to subscribed downlinks:
1. When scanning unexported echomail, calls `echofix_get_subscribers(ECHOFIX_TYPE_AREAFIX, area_tag, ...)`
2. Creates packets for each subscribed downlink
3. Uses `scanner_find_downlink_by_address()` to lookup downlink session passwords

#### TIC/Fileecho Routing to Downlinks
The TIC module (`FTN/c/tic`) forwards files to subscribed downlinks:
1. Call `tic_forward_to_subscribers(filebase_id, file_id, area_tag)` after storing a new file
2. Queries `echofix_get_subscribers(ECHOFIX_TYPE_FILEFIX, area_tag, ...)`
3. Creates TIC files for each subscriber and queues for sending

#### Support Module SWI (0x5AA86) Downlink Reasons
| Reason | Value | Description |
|--------|-------|-------------|
| GET_DOWNLINK | 8 | R1=id → R0=FTN_DOWNLINK_CONFIG ptr |
| SET_DOWNLINK | 9 | R1=id, R2=config ptr |
| COUNT_DOWNLINKS | 10 | → R0=count |

### Nodelist Processing

#### Overview
The nodelist module (`FTN/c/nodelist`) provides FTS-0005 nodelist parsing, compilation, and on-demand lookup for routing and hostname discovery. Networks are derived from the configured FTN addresses.

**Source Files:**
- `FTN/c/nodelist` - Parsing, compilation, caching, lookup
- `FTN/h/nodelist` - Data structures and prototypes
- `FTN/c/ftnupload` - Drag-and-drop import window

#### Directory Structure
```
<Converse$Dir>.FTN.Nodelists/
├── 0/                      ← Network 0 (first network from config)
│   ├── Nodelist            ← Raw nodelist file (text)
│   ├── NodeIDX             ← Compiled binary index
│   └── Diffs/              ← Nodediff files (future)
├── 1/                      ← Network 1 (second network)
│   └── ...
└── ...
```

#### Configuration
Set the nodelists path in FTN config:
```
nodelists   <Converse$Dir>.FTN.Nodelists
```

The path defaults to `<Converse$Dir>.FTN.Nodelists` if not specified.

#### Usage
1. Open the Commands menu on the FTN Mailer iconbar icon
2. Select "Nodelist..."
3. Use the up/down arrows to select the target network
4. Drag a nodelist file onto the drop zone
5. Click "Upload" to compile

Compilation progress is shown in the FTN status window.

#### Data Structures

**Node Entry (124 bytes):**
```c
typedef struct {
    unsigned short zone, net, node, point;
    unsigned char status;           /* NODELIST_STATUS enum */
    unsigned char flags;            /* NODE_FLAG_* bits */
    unsigned short hub;             /* Hub node for routing */
    unsigned short port;            /* BinkP port (0=24554) */
    char name[40];                  /* System name */
    char sysop[24];                 /* Sysop name */
    char hostname[48];              /* From IBN/INA flag */
} NODELIST_ENTRY;
```

**Node Status Values:**
| Status | Value | Nodelist Keyword |
|--------|-------|------------------|
| NODE_STATUS_NORMAL | 0 | (comma/empty) |
| NODE_STATUS_ZONE | 1 | Zone |
| NODE_STATUS_REGION | 2 | Region |
| NODE_STATUS_HOST | 3 | Host |
| NODE_STATUS_HUB | 4 | Hub |
| NODE_STATUS_PVT | 5 | Pvt |
| NODE_STATUS_HOLD | 6 | Hold |
| NODE_STATUS_DOWN | 7 | Down |

**Node Flags:**
| Flag | Bit | Source |
|------|-----|--------|
| NODE_FLAG_CM | 0x0001 | CM flag (24/7) |
| NODE_FLAG_MO | 0x0002 | MO flag |
| NODE_FLAG_LO | 0x0004 | LO flag |
| NODE_FLAG_BINKP | 0x0008 | IBN flag |
| NODE_FLAG_TELNET | 0x0010 | ITN flag |

#### Key Functions
```c
/* Initialisation */
void nodelist_initialise(void);
void nodelist_finalise(void);

/* Network enumeration (from FTN config addresses) */
int nodelist_get_configured_networks(NODELIST_NETWORK *networks, int max);
int nodelist_get_network_count(void);
const char *nodelist_get_network_name(int network_id);
int nodelist_network_has_index(int network_id);

/* Compilation */
int nodelist_import_and_compile(int network_id, const char *source_path,
                                 NODELIST_COMPILE_STATS *stats);
int nodelist_compile(int network_id, NODELIST_COMPILE_STATS *stats);

/* Lookup (on-demand with 64-entry LRU cache) */
NODELIST_ENTRY *nodelist_lookup(int network_id, const FTN_ADDR *addr);
NODELIST_ENTRY *nodelist_lookup_any(const FTN_ADDR *addr, int *found_network);
int nodelist_get_hostname(int network_id, const FTN_ADDR *addr,
                          char *hostname, size_t size, int *port);

/* Routing */
NODELIST_ROUTE_RESULT nodelist_find_route(int network_id, const FTN_ADDR *dest,
                                           FTN_ADDR *route_via);
NODELIST_ENTRY *nodelist_find_hub(int network_id, int zone, int net, int hub_node);
NODELIST_ENTRY *nodelist_find_host(int network_id, int zone, int net);

/* Path helpers */
int nodelist_get_base_path(char *buffer, size_t size);
void nodelist_format_network_path(char *buffer, size_t size, int network_id);
void nodelist_format_index_path(char *buffer, size_t size, int network_id);
```

#### IBN Flag Parsing
The nodelist parser extracts hostname and port from the IBN (Internet BinkP Node) flag:
- `IBN` - Node supports BinkP but no hostname specified
- `IBN:hostname.example.com` - BinkP with hostname
- `IBN:hostname.example.com:24555` - BinkP with hostname and non-default port

The hostname is stored in `NODELIST_ENTRY.hostname` and port (if specified) in `NODELIST_ENTRY.port`. Default port is 24554.

#### Cache Behaviour
- 64 entries per network, LRU eviction
- Cache is cleared when index is reloaded
- Cache hits/misses tracked for debugging: `nodelist_get_cache_stats()`

#### Integration with Queue/Scanner
The queue and scanner modules can use nodelist lookups to:
1. Find hostnames for nodes without configured uplinks
2. Determine routing paths (direct, via hub, via host)
3. Check if a node is online (not Hold/Down)

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
|--------|-------|------------|---------|
| 0 | 0 | 88 | Line number |
| 1 | 1 | 88 | Type (IP/BD/LC) |
| 2 | 2 | 300 | Username/waiting |
| 3 | 3 | 430 | Activity text |
| 4 | 4 | 510 | Hostname/Phone |
| 5 | 5 | 169 | Connect timer |
| 6 | 6 | 56 | D (Disconnect) button |
| 7 | 7 | 56 | V (View) button |
| 8 | 8 | 56 | L (Logon) button |

**Type Column Values:**
- **IP** - Telnet (TCP/IP connection)
- **BD** - BlockDriver (Serial/modem)
- **LC** - Local (desktop-only access)

**Icon Index Calculation:**
```c
#define ICONS_PER_LINE 9
#define FIRST_DYNAMIC_ICON 15

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

