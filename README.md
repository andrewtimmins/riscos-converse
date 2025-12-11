# Converse BBS for RISC OS

**The modern multi-line bulletin board system for RISC OS.**

Converse brings the classic BBS experience to your Archimedes, A7000, RiscPC, or Raspberry Pi running RISC OS. Whether you're building a retro computing community, hosting file archives, or connecting with FidoNet networks worldwide, Converse provides everything you need in a native RISC OS application.

---

## Key Features

### True Multi-Line Support
Run up to **32 simultaneous connections** across multiple connection types:
- **Telnet** - TCP/IP connections over your network
- **Serial** - BlockDriver-based modem/serial connections for that authentic dial-up experience
- **Local** - Desktop-only access via sysop View/Logon buttons

Each caller gets a dedicated LineTask application, ensuring responsive ANSI art, scripts, and door games even under heavy load. The cooperative multitasking design keeps your desktop smooth and usable.

### Desktop Server Application
Monitor your entire BBS from a clean Wimp interface:
- **Live status display** - See every connected line at a glance: username, activity, hostname/phone, and connection timer
- **Line type indicators** - IP (telnet), BD (BlockDriver/serial), or LC (local)
- **One-click controls** - Disconnect troublesome users, view their terminal session, or force a logon
- **System statistics** - Track uptime, total calls, and connection states
- **Connection toggle** - Enable/disable new connections without stopping the server
- **Chat pager** - Users can page you for real-time sysop chat with a split-screen terminal interface

### Full Messaging System
- **Local message areas** - Community discussions, announcements, private mail
- **FTN echomail** - Connect to FidoNet, RetroNet, or any FTN-compatible network
- **FTN netmail** - Point-to-point mail across the network with routing support
- **Private user mail** - Secure user-to-user messaging with dedicated inbox
- **Continuous message reader** - Navigate with Next/Previous/Reply, jump to Start/End, switch areas
- **Rich composer** - To, Subject, Body fields with line-by-line editing
- **Direct mail commands** - `SENDMAIL` and `SENDNETMAIL` for script-driven messaging
- **Login scan** - Automatic notification of new private messages and files

### Filebase Management
- **Multiple filebases** - Organise files into themed collections
- **Area-based structure** - Group files within each filebase by category
- **Access control** - Restrict areas by access level or key codes
- **Upload/download tracking** - Per-file statistics and user download counts
- **New file scanning** - Automatic detection of uploads since last visit
- **User history** - Remembers last selected filebase/area between sessions

### File Transfer Protocols
Complete implementation of industry-standard protocols:
- **XMODEM** - Classic 128-byte blocks with checksum
- **XMODEM-CRC** - Enhanced error detection with CRC-16
- **XMODEM-1K** - Faster 1024-byte blocks
- **YMODEM** - Batch transfers with filename/size headers
- **YMODEM-G** - Streaming mode for reliable connections
- **ZMODEM** - Full implementation with CRC-32, streaming, and crash recovery *(recommended)*

### Door Game Support
Run external programs that interact with your callers:
- **Native ConverseDoors** - Modern API with full user info, system queries, and messaging
- **RiscBBS compatibility** - Run doors written for the classic RiscBBS system
- **ARCbbs compatibility** - Full emulation layer for ARCbbs doors
- **26-bit door support** - Run legacy RISC OS 3.x doors via Aemulor integration

### FidoNet Technology Network (FTN)
Connect to the worldwide FidoNet or compatible networks:
- **BinkP mailer** - Modern FTN transport protocol with full session management
- **Multi-address support** - Up to 8 AKAs for different networks
- **Uplink management** - Configure multiple uplinks with group filtering and aliases
- **Downlink support** - Feed echomail and fileecho to points and downstream nodes
- **Automatic toss/scan** - Configurable intervals for mail processing
- **TIC file support** - Full file distribution network integration (inbound and outbound)
- **File requests (FREQ)** - Request and serve files during BinkP sessions
- **Echomail groups** - Route areas to appropriate uplinks based on group membership
- **EchoFix/AreaFix** - Automatic subscription management for downlinks
- **Nodelist support** - FTS-0005 nodelist compilation with on-demand lookup and caching
- **Transit netmail** - Route netmail through your system to downstream destinations
- **Message priorities** - CRASH, HOLD, DIRECT, and IMMEDIATE routing flags
- **Configurable origins** - Multiple origin lines with random selection

### Powerful Scripting Engine
Create dynamic, interactive sessions with 60+ built-in commands:

**Flow Control Example**
```
if %{accesslevel} >= 100 then
    print `Welcome, Administrator!\r\n`
    script `<Converse$Dir>.BBS.AdminMenu`
else
    print `Welcome back, %{realname}!\r\n`
endif
```

**Loop Example**
```
for i = 1 to 10
    print `Line %{i}\r\n`
endfor

while %{tries} < 3
    readline answer
    if answer == `secret` goto success
    add tries %{tries} 1
endwhile
```

**Scripting Features:**
- Block IF/THEN/ELSE/ENDIF with 16-level nesting
- FOR/WHILE loops with BREAK and CONTINUE
- Compound conditions with && (AND) and || (OR)
- 60+ macro variables for runtime substitution
- Subscript calls with 8-level call stack
- Integer arithmetic: ADD, SUB, MUL, DIV, MOD
- RANDOM number generation
- String operations: STRLEN, HASKEY
- ANSI terminal detection with DETECTANSI
- Visual control: FLASH, BOLD, STD, CLS, FGBG
- Input handling: PROMPT, READLINE, YESNO, ANYKEY
- More prompt control with configurable screen height
- Mix ANSI art with embedded script blocks

**User Management:**
- LOGON - Authenticate existing users
- NEWUSER - Guided new user registration with validation
- LOGINSCAN - Check for new messages and files
- ONLINE - Display all connected users

### Web Server Module
Serve your filebase to the world via HTTP:
- Static file hosting from `<Converse$Dir>.Web`
- Dynamic filebase listings with `{{filebase}}` template tag
- Hierarchical display of filebases, areas, and files
- Direct download links with proper MIME types
- Runs alongside the BBS on port 80

### Security and Access Control
- **User authentication** - Username/password with XOR-encrypted storage
- **Access levels** - 0-255 granular permission system
- **Access keys** - Letter-based feature flags (A-Z)
- **IP banning** - Block troublesome addresses with CIDR support
- **Idle timeout** - Automatic disconnection of inactive users (paused during transfers)
- **Bot stopper** - Challenge prompts to prevent automated connections
- **Locked accounts** - Disable problem users without deletion
- **New user registration** - Guided signup with username availability checking

### Comprehensive Logging
- **System log** - Module events and errors
- **Call log** - CSV format with timestamps, users, and status
- **Per-line logs** - Detailed session activity
- **FTN log** - Mail processing and network events
- **Web log** - HTTP requests and downloads

---

## Architecture

Converse is built as a suite of cooperating modules and applications:

| Component | Description |
|-----------|-------------|
| **ConversePipes** | SWI &5AA00 - Circular buffer I/O for 32 lines |
| **ConverseFiler** | SWI &5AA40 - Persistent storage for users, files, messages |
| **ConverseBBS** | SWI &5AA80 - Shared configuration and line state |
| **ConverseDoors** | SWI &5AAC0 - Native door game interface |
| **ARCbbsDoors** | SWI &41040 - ARCbbs door compatibility layer |
| **Server** | Wimp application - Listener, status UI, sysop tools |
| **LineTask** | Wimp application - Per-caller session handler with ANSI terminal |
| **Serial** | Wimp application - BlockDriver serial line handler |
| **UserEd** | Wimp application - User database editor |
| **FTN Mailer** | Wimp application - BinkP sessions, tossing, scanning, nodelist management |
| **Web Server** | Wimp application - HTTP file serving with template support |

All SWI allocations are officially registered with RISC OS Open Ltd.

---

## Documentation

Comprehensive documentation is included in the `Docs/` directory:

- **NewSysop** - Getting started guide for new sysops
- **Scripting** - Complete script language reference (60+ commands)
- **Doors** - Door game development guide
- **SWIs/** - Technical documentation for all module interfaces
  - Filer - User, file, and message storage
  - Pipes - Inter-process communication buffers
  - Support - Configuration and state management
- **FTN/** - FidoNet configuration and operation
  - Configuration - Setting up addresses, uplinks, and downlinks
  - BinkP - Protocol details and session management
- **ARCbbs/** - ARCbbs compatibility layer documentation

---

## Getting Started

1. Copy the Converse application to your hard disc
2. Double-click `!Converse` to install modules and set system variables
3. Edit configuration files in `Resources.Config`:
   - `System` - BBS name, ports, timeouts, script paths
   - `Lines` - Per-line settings (type, bot stopper, hello message)
   - `MsgBases` - Message area definitions with FTN tags
   - `FileBases` - File area definitions with TIC tags
   - `FTN` - Network addresses, uplinks, downlinks (optional)
4. Create your scripts in the `BBS` directory
5. Run the Server application
6. Connect via telnet to port 23!

---

## System Requirements

- RISC OS 3.5 or later (RISC OS 5 recommended)
- 4MB RAM minimum (8MB+ recommended for multiple lines)
- TCP/IP stack (Freeway, EtherK, or similar)
- Hard disc with sufficient space for your filebases
- BlockDrivers for serial line support (optional)
- Aemulor for 26-bit legacy doors (optional)

**Tested Platforms:**
- Raspberry Pi (RISC OS 5)
- RiscPC / A7000
- RPCEmu / Arculator

---

## Contributing

We welcome contributions! Whether it's new scripts, door games, bug fixes, or documentation improvements:

- Stick to **ANSI C90** (no POSIX headers) and keep stack usage modest
- Validate all line numbers (0-31) and buffer lengths before touching memory
- Update the relevant `Docs/` page when changing SWIs or Wimp messages
- Include test notes describing which scripts or examples you ran
- Submit issues describing your hardware setup and goals

---

## Contact

Questions? Open an issue on GitHub describing your setup and what you're trying to achieve. We love seeing Converse run on new machines and hearing about your BBS communities!

---

*Bringing the BBS spirit to RISC OS - one connection at a time.*
