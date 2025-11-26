# Converse for RISC OS

Bring a modern multi-line BBS back to your Archimedes, A7000, or RISC OS Pi. Converse handles telnet connections, the user database, message/file stores, and the classic “doors” experience while letting you keep full control of scripts and content.

## Why run Converse?
- **True multi-line**: Each caller gets a dedicated LineTask, so ANSI art, scripts, and doors stay responsive even when several people are online.
- **Scriptable sessions**: The bundled interpreter (see `Docs/Scripting`) lets you greet users, launch doors, or run maintenance actions using simple macros.
- **Robust storage**: The ConverseFiler module persists users, messages, and uploads using transaction-style copy/update semantics.
- **Desktop app**: The server app shows every line at a glance — caller info, live activity text, timers, and quick actions.
- **Clean OS integration**: Official SWI allocations (`ConversePipes &5AA00`, `ConverseFiler &5AA40`) and matching Wimp messages mean other tools can hook in easily.

## Contributing
We welcome fixes to the scripts, new sample doors, and tooling around the SWIs. Please:
- Stick to ANSI C90 (no POSIX headers) and keep stack usage modest.
- Validate all line numbers (0–31) and buffer lengths before touching memory.
- Update the relevant `docs/` page whenever you add or change a SWI reason or Wimp message.
- Include test notes (which scripts or examples you ran) in your merge request.

Questions? Open an issue describing your hardware setup and what you’re trying to achieve — we love seeing Converse run on new machines.
