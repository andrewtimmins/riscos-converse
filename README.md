# Converse BBS for RISC OS

**The modern multi-line bulletin board system for RISC OS.**

Converse brings the classic BBS experience to your Archimedes, A7000, RiscPC, or Raspberry Pi running RISC OS. Whether you're building a retro computing community, hosting file archives, or connecting with FidoNet networks worldwide, Converse provides everything you need in a native RISC OS application.

---

## Key Features

### True Multi-Line Support
Run up to **32 simultaneous connections**. Each caller gets a dedicated LineTask application, ensuring responsive ANSI art, scripts, and door games even under heavy load. The cooperative multitasking design keeps your desktop smooth and usable.

### Desktop Server Application
Monitor your entire BBS from a clean Wimp interface:
- **Live status display** - See every connected line at a glance: username, activity, hostname, and connection timer
- **One-click controls** - Disconnect troublesome users, view their terminal session, or force a logon
- **System statistics** - Track uptime, total calls, and connection states
- **Chat pager** - Users can page you for real-time sysop chat with a split-screen terminal interface

### Full Messaging System
- **Local message areas** - Community discussions, announcements, private mail
- **FTN echomail** - Connect to FidoNet, RetroNet, or any FTN-compatible network
- **FTN netmail** - Point-to-point mail across the network
- **Private user mail** - Secure user-to-user messaging
- **ANSI message viewer** - Paginated display with Next/Previous/Reply navigation
- **Rich composer** - To, Subject, Body fields with line-by-line editing

### Filebase Management
- **Multiple filebases** - Organise files into themed collections
- **Area-based structure** - Group files within each filebase by category
- **Access control** - Restrict areas by access level or key codes
- **Upload/download tracking** - Per-file statistics and user download counts
- **New file scanning** - Automatic detection of uploads since last visit

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

### FidoNet Technology Network (FTN)
Connect to the worldwide FidoNet or compatible networks:
- **BinkP mailer** - Modern FTN transport protocol
- **Multi-address support** - Up to 8 AKAs for different networks
- **Uplink management** - Configure multiple uplinks with group filtering
- **Automatic toss/scan** - Configurable intervals for mail processing
- **TIC file support** - File distribution network integration
- **Echomail groups** - Route areas to appropriate uplinks

### Powerful Scripting Engine
Create dynamic, interactive sessions with 40+ built-in commands:

**Flow Control Example**
```
if %{accesslevel} >= 100 then
    print `Welcome, Administrator!\r\n`
    script `<Converse$Dir>.BBS.AdminMenu`
else
    print `Welcome back, %{realname}!\r\n`
endif
```

**Scripting Features:**
- Block IF/THEN/ELSE/ENDIF with 16-level nesting
- Compound conditions: `if %{hour} >= 9 && %{hour} < 17 goto open`
- 50+ macro variables for runtime substitution
- Subscript calls with 8-level call stack
- Integer arithmetic and random numbers
- String operations and key checking
- ANSI terminal detection
- Mix ANSI art with embedded script blocks

### Web Server Module
Serve your filebase to the world via HTTP:
- Static file hosting from `<Converse$Dir>.Web`
- Dynamic filebase listings with `{{filebase}}` template tag
- Direct download links for all files
- Runs alongside the BBS on port 80

### Security and Access Control
- **User authentication** - Username/password with encrypted storage
- **Access levels** - 0-255 granular permission system
- **Access keys** - Letter-based feature flags (A-Z)
- **IP banning** - Block troublesome addresses with CIDR support
- **Idle timeout** - Automatic disconnection of inactive users
- **Bot stopper** - Challenge prompts to prevent automated connections
- **Locked accounts** - Disable problem users without deletion

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
| **LineTask** | Wimp application - Per-caller session handler |
| **UserEd** | Wimp application - User database editor |
| **FTN Mailer** | Wimp application - BinkP sessions and mail processing |
| **Web Server** | Wimp application - HTTP file serving |

All SWI allocations are officially registered with RISC OS Open Ltd.

---

## Documentation

Comprehensive documentation is included in the `Docs/` directory:

- **NewSysop** - Getting started guide for new sysops
- **Scripting** - Complete script language reference (40+ commands)
- **SWIs/** - Technical documentation for all module interfaces
  - Filer - User, file, and message storage
  - Pipes - Inter-process communication buffers
  - Support - Configuration and state management

---

## Getting Started

1. Copy the Converse application to your hard disc
2. Double-click `!Converse` to install modules and set system variables
3. Edit configuration files in `Resources.Config`:
   - `System` - BBS name, ports, timeouts
   - `Lines` - Per-line settings
   - `MsgBases` - Message area definitions
   - `FileBases` - File area definitions
   - `FTN` - Network configuration (optional)
4. Create your scripts in the `BBS` directory
5. Run the Server application
6. Connect via telnet to port 23!

---

## System Requirements

- RISC OS 3.5 or later (RISC OS 5 recommended)
- 4MB RAM minimum (8MB+ recommended for multiple lines)
- TCP/IP stack (Freeway, EtherK, or similar)
- Hard disc with sufficient space for your filebases

**Tested Platforms:**
- Raspberry Pi (RISC OS 5)
- RiscPC / A7000
- RPCEmu / Arculator
- Original Archimedes (A5000, A540)

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
