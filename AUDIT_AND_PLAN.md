# Converse BBS — Code Audit & Development Plan

Audit date: 2026-07-07. Toolchain confirmed: Norcroft DDE C, `-apcs 3/32bit`,
OSLib32, cmhg modules, objasm block drivers. Target: RISC OS 5 (ARMv7, 32-bit).
Norcroft default `char` is **unsigned**. Module SWI handlers run privileged on a
small SVC stack.

This document has two parts: **(A) Findings register** (ranked, with file:line and
trigger) and **(B) Phased development plan**.

---

# PART A — FINDINGS REGISTER

Severity: **C**=crash/corruption or remote compromise · **H**=feature-breaking ·
**M**=correctness · **L**=minor/defensive.

## A0. Root cause: the FTN struct-layout drift (highest leverage)

A change to `MESSAGE_RECORD` and the message-base config structs in the Filer module
(`Filer/h/structs`) was **not propagated** to the FTN mailer, which carries private
duplicate copies and hard-coded offsets. Canonical `MESSAGE_RECORD`
(`Filer/h/structs:243-266`) now has `subject[256]` moved after `bodysize`, with
`flags` appended at offset 744; total size 748. The FTN copies predate this. Result:
the entire FTN mail pipeline reads/writes the wrong offsets.

| ID | Sev | Flow | Where | Symptom |
|----|-----|------|-------|---------|
| C2 | C | Inbound echomail area match | caller `FTN/c/tosser:834-857,887,898` vs master `Support/h/msgbaseconfig:58` | Mirror struct inserts phantom `readonly`+`path[256]`, drops `groups[64]`; `area_count` read 260 bytes off → **inbound echomail silently dropped**, or garbage count → OOB walk → data abort |
| C3 | C | Outbound echomail scan | `FTN/c/scanner:969-980,1007,1012` | Same phantom fields → outbound echomail **never scanned/sent** (count 0) or crash. (Scanner's other two mirrors at `:191`,`:956` are correct — only outbound broken) |
| C4 | C | Outbound netmail routing | `FTN/c/scanner:306` (`record+532`), `:358` (`record+664`) vs canonical `dstaddr@276`,`flags@744` | Reads dstaddr/flags from inside `subject[256]` → **netmail routed to garbage nodes / dropped**, flavour (crash/hold/direct) random |
| H2 | H | AreaFix/FileFix reply | `FTN/c/echofix:1111-1133,1171` vs `Filer/c/messagebase:408,426` | Local `MSG_REC` puts `subject` after `keys`, omits `flags`; module copies 748 in canonical order → **subscription reply netmail corrupted, never delivered** (+4-byte over-read) |
| H3 | H | FileFix config read | `FTN/c/echofix:703-710,734,742,745` | Reads FILEBASE config through a MSGBASE-shaped struct → file-echo allow/deny garbled |
| H4 | H | Outbound origin AKA | `LineTask/c/messagebase:3939-3947,3957` vs `Support/h/ftnconfig:25` | Reads `FTN_ADDRESS_CONFIG` as raw `int[]` at wrong offsets (`zone` is word 17, not 0) → **wrong origin address stamped on outbound mail** |
| M6 | M | Toss import | `FTN/c/tosser:928-950` vs `Filer/c/messagebase:426` | MSG_REC 744 bytes, module copies 748 → 4-byte over-read, imported msgs get uninitialised routing flags |
| M9(web) | L | Web msg read | `Web/c/template:121-143` | Omits trailing `flags`; safe today (read-only), latent |

**Fix:** delete every private/duplicate copy of `MESSAGE_RECORD`, `MSGBASE_CONFIG`,
`FILEBASE_CONFIG`, `FTN_ADDRESS_CONFIG` and every magic offset; include the single
canonical `Filer/h/structs` / `Support/h/*config` headers everywhere. This one change
resolves C2, C3, C4, H2, H3, H4, M6 and the web latent.

## A1. Remote, unauthenticated — memory/file compromise

| ID | Sev | Where | Trigger → impact |
|----|-----|-------|------------------|
| C1 | C | `Server/c/main:1884-1896` (no `return`) → `:1964-1988` | All telnet lines busy + one more connection → writes `line_configuration[32]` OOB (~3.9KB struct) at 32 configured lines; else phantom "connected" line + writes to fd 0. Repeatable each over-capacity connect |
| SEC1 | C | `FTN/c/unzip:784-789` + `FTN/c/tosser:1347-1362` | Arcmail ZIP entry keeps RISC OS metachars `^ $ :` → **remote arbitrary file write** (overwrite `!Boot`, configs, scripts). Reachable by passwordless node |
| SEC2 | H | `FTN/c/freq:201` via `FTN/c/binkp:1490,1513` | Unsanitised `M_GET` filename, no auth/state check → **remote arbitrary file read** (passwords, config) |
| SEC3 | H | `FTN/c/tosser:661-816` (overflow `:812`) | Any tossed message whose last body line lacks CRLF → 1-byte NUL heap overflow → Norcroft heap-metadata corruption in the toss loop |
| SEC4 | M | `FTN/c/echofix:822-833,1188` | `vsnprintf` return misused → `body_len` overshoots 8192 `body[]` → adjacent-memory disclosure mailed back to remote |
| SEC5 | M | `Web/c/session:31-61` | 32-bit LCG seeded from monotonic time → predictable session tokens → **web auth bypass** (impersonate, POST /upload) |
| SEC6 | M | `Web/c/main:1116-1121` (`json[4096]`, margin 100) | Unauth `GET /api/areas?filebase=N` with long area names → ~50B stack overflow (`sprintf` not `snprintf`) |
| SEC7 | M | `FTN/c/scanner:104-141`,`:162,165` | Config group token ≥32 chars → 32-byte stack buffer smash |
| SEC8 | M | `FTN/c/unzip:886,942` | Untrusted ZIP sizes → unchecked `malloc` → zip-bomb DoS |
| SEC9 | L | `FTN/c/binkp` `BINKP_MAX_FRAME 32767` vs `rx_buffer 32768` | Frame declaring len 32767 never completes → session stall/DoS |

## A2. RISC OS 5 / 32-bit specific crashes

| ID | Sev | Where | Detail |
|----|-----|-------|--------|
| RO1 | C | `Serial/c/serial:176-195` | Block-driver code `fread` into data buffer then called as ARM code with **no `OS_SynchroniseCodeAreas`** → stale I-cache on ARMv7 → abort/wild branch. Worked on old cores, crashes on RO5 |
| RO2 | M | `Pipes/blockdrivers/s/host`,`s/client` | Uses **non-X** Pipes SWIs; `BVS` error checks are dead (non-X SWI enters error handler); `func_getbyte` returns error-block pointer as a data byte. Use X forms |
| RO3 | H | `Filer/c/filebase` (`1248,1520`+~30 `char[300]`), `Filer/c/logging:231,253` (`[500]`), `cache` | >1.1KB of stack locals in one SWI-handler chain on the small SVC stack → overflow risk. Same pattern (shallower) in Support/Doors/Pipes. Move scratch to workspace/heap |

## A3. Privileged-module memory safety (Filer / Support)

| ID | Sev | Where | Trigger |
|----|-----|-------|---------|
| MOD1 | H | `Filer/c/filebase:625` (DOWNLOAD_BLOCK), `:508` (UPLOAD), `messagebase:567,493` | `fread`/`fwrite` with **unbounded caller length** (R5/R4) → privileged memory corruption/abort |
| MOD2 | H | `Support/c/msgbaseconfig:169`, `filebaseconfig:159` | SET_BASE memcpy copies caller `area_count`/`base_count` **unclamped**; persisted → later GET/CLI walks ~1e9 records → data abort |
| MOD3 | H | `Filer/c/messagebase:922` (FIND_UNEXPORTED) + all record-input SWIs | Trust caller count/pointer → caller-array overflow / SVC read fault |
| MOD4 | M | `Filer` file-static buffers `filebase:48`, `messagebase:48`, `userdb:22` | Shared read-scratch also returned as SWI result pointer → reentrancy corruption / password disclosure |
| MOD5 | M | `Support/c/accessconfig:35-93` | No `default` case → invalid reason leaves R0 unchanged, caller can't detect error |
| MOD6 | M | `Filer/c/filer:1050-1064` | `snprintf("%s", caller_ptr)` over-reads unterminated caller string |
| MOD7 | M | Support `SET_*` memcpy leaves string fields unterminated → CLI `%s` over-read (`msgbaseconfig:169` etc.) |

## A4. LineTask caller-side crashes & correctness

| ID | Sev | Where | Detail |
|----|-----|-------|--------|
| LT1 | C | `LineTask/c/messagebase:1155,2996,3101,3215,3226,3237,3982,4492,4592`; `script:5455,5473,5560,5586`; `filebase:473` | Filer signals failure with **both `0` and `-1`**; these sites check only one, then deref → data abort kills all lines. Template that does it right: `transfer:125` |
| LT2 | H | `messagebase:1346-1382` (`viewer_show_body`), `3124-3165` (`quote_original`) | CRLF handling advances `i` twice but `body_offset` once → multi-page messages & quoted replies corrupt. **Core reader broken** |
| LT3 | H | `messagebase:3982` | `get_area_type` on `-1` returns garbage areatype → drives `can_read_message` → private/netmail exposure (also LT1 crash) |
| LT4 | H | Freezes: `filebase:932-943` (upload copy, from `main:906`); `script:5352-5675` (LOGINSCAN); `script:5264` (OSCLI `system()`); `messagebase` reader O(n) scans | Block the Wimp poll → whole desktop + all lines frozen |
| LT5 | M | `script`: loop state not reset in `script_clear_program:1957` (only IF is) | Aborted FOR/WHILE leaks `script_loop_depth` into next sub-script |
| LT6 | M | `script:2542-2555` | Any line ending `:` becomes a label → `print Choose an option:` never prints |
| LT7 | M | `script` expansion buffers 512B (`3731,4109,2028,3819`), msgbase/filebase args 256B | Values >511 silently truncated; truncation in IF/WHILE operand can flip comparison |
| LT8 | M | `messagebase:748-754` (`entries[256]`≈21.5KB), `composer_send` 8KB+record | Very large single stack frames in a small-stack cooperative task |
| LT9 | M | `messagebase:3884-3899` | UPLOAD_BLOCK failure returns without END_UPLOAD → leaks module upload handle / partial message |
| LT10 | M | `messagebase:3835,3855` | Outbound msg `orgaddr` never set → zeroed `0:0/0` origin (compounds H4) |
| LT11 | M | Enumeration `while(1)` loops (`messagebase:631,773,2166,4008`; `filebase:310,462,597`) don't apply `MAX_ENUM_ITERATIONS` → corrupt module data → permanent freeze |
| LT12 | L | Overflows: `transfer:457` (`bytes*100` >21MB), `filebase:241-243` (GB fractional); unchecked mallocs `script:153-162`; stale statics `script:60,63`; `main:989` deref before NULL guard; decl-after-stmt `main:894` |

## A5. Session lifecycle (leaks into the *next* caller)

| ID | Sev | Where | Detail |
|----|-----|-------|--------|
| LC1 | H | `LineTask/c/main:653-719` `perform_session_disconnect` never calls `transfer_cleanup` (`transfer:400`) | Carrier drop mid-transfer → leaked FILE*/malloc, `xfer_session.active` stays 1 → transfer_poll runs into next caller |
| LC2 | H | `Server/c/main:1277-1280` | On 1-line board, logoff returns before `close_line_connection:1297` → line stuck busy forever |
| LC3 | M | `main:653-719` never calls `chat_reset_state`/`chat_close_pager` (`chat:115`) | Drop while paging → leaked chat state routes next caller's bytes into chat |
| LC4 | M | `main:1091-1108` CONNECT handler | No defensive state reset; `pipes_reset_line` ClearInput can drop DISCONNECT byte → next caller inherits prior user's access/name/base pointers |
| LC5 | M | `LineTask/c/main:283-343` | No atexit/exit handler; a crash leaves line stuck "connected" in Support until restart |
| LC6 | L | `Server/c/main:1997-2002` | Only closes on graceful FIN; ECONNRESET ignored → line reclaimed only by idle timeout (or never if disabled) |

## A6. Door subsystem (native path wired but non-functional)

| ID | Sev | Where | Detail |
|----|-----|-------|--------|
| DR1 | C | `LineTask/c/main:1142-1167` has no `native.active` input branch; poll drains pipe (`main:963`) before `door_native_process:967` | Native doors get **no user input** — hang at first prompt |
| DR2 | C | `door_native:336,341` set user info before Wimp_StartTask; Register does `memset` (`Doors/c/doors:343`) wiping it | Native doors always see user_id=0, access=0, is_sysop=0 → in-door access bypass |
| DR3 | H | `ARCbbs/Doors/c/buffer:795-887` | Hard-codes Guest / userlevel=100; real user never pushed → ARCbbs doors see phantom sysop |
| DR4 | M | `door_native:123` username from realname; `:332` no line number appended (contra `Doors/h/doors:11`) → door Register times out |
| DR5 | L | `Doors/c/doors:787` GetSystemInfo hard-codes 32 lines; `:418` ReadByte ignores timeout; time_online/remaining hard 0/-1 |

## A7. Auth / access-control correctness

| ID | Sev | Where | Detail |
|----|-----|-------|--------|
| AC1 | H | `LineTask/c/script:1830-1857` + `input_complete_newuser_confirm:916-952` | New-user "Create account? (Y/N)" ignores the key → **N still creates the account**, echoes "Y" |
| AC2 | M | `script:5898-5933` `filebase download <id>` + host stub `main:1982-2004` | No `filebase_check_access` (unlike select/area) → per-file access-level/keys bypass |
| AC3 | M | `main:2222` loads `user.flags.ratios` but no download path ever reads it | Up/download ratios are dead — sysops relying on them get none |
| AC4 | L | `script:5476-5483` newscan requires `receivedby==user_id` | Login "new messages" scan never counts new **public** posts |

## A8. Documented-but-missing / dead features (decide: build vs cut from docs)

| ID | Where documented | Reality |
|----|------------------|---------|
| F1 | `Docs/Scripting:652-676`, README:35, `NewSysop:1289` | `SENDMAIL`/`SENDNETMAIL` — no enum, token, or handler anywhere. Real path: `messagebase compose netmail` |
| F2 | README:46-53 | YMODEM / YMODEM-G / ZMODEM (incl. the "recommended" ZMODEM) are stubs returning "Protocol not implemented" (`transfer:168-174,288-297`). Only XMODEM/-CRC/-1K work. `ymodem.c`/`zmodem.c` don't exist |
| F3 | `Docs/Doors:229-254`, README:57 | ConverseDoors SendMessage/ReceiveMessage return -1 stubs (`Doors/c/doors:836-847`) |
| F4 | `Docs/ARCbbs/Doors:24-37` | Entire door-facing SWI table (GetBuffer/GetByte/PutByte/GetLine/PutLine/GetStatus/SetStatus/Flush) is fictional; real SWIs are ReadStatus/WriteStatus/SendRequest/GetReply/… |

## A9. Documentation drift (see full per-area audit; summary)

- **Config paths wrong everywhere**: docs say `Resources.Config.*`, code reads `<Converse$Dir>.Config.*` (`NewSysop`, `FTN/Configuration`). Data is under `Resources.Data`.
- **Wrong config keys**: `listen`→`port`, `idle_timeout`→`timeout`, `max_lines` not read, System `botstopper` is yes/no not a string, msgbase `type` values, area types.
- **FTN**: `packet_password` doesn't exist; uplink limit 8→16; default toss/poll intervals 0 not 300/3600; `downlink`/`domain` blocks, AreaFix/FileFix command language, FileFix, nodelists all undocumented.
- **SWI docs**: `FTN_ADDRESS` 8→116 bytes; `USER_STATS`/`USER_FLAGS` wrong; Scripting "Internal Command Codes" enum entirely wrong; counts "60+ commands/macros" actually 51/51.
- **Undocumented working features**: entire Web app (login/sessions/upload/API/8 template tags), FTN domains/downlinks/FileFix, Support SerialConfig SWI group, Doors host SWIs, RiscBBS doors.
- BlockDrivers doc self-contradicts on port count (31 vs 32).

---

# PART B — PHASED DEVELOPMENT PLAN

Ordering principle: stop the bleeding (remote compromise, crashes) → make the machine
stable on RO5 → fix the data-corruption root cause → complete/repair features →
reconcile docs. Each phase is independently shippable and testable.

## Phase 0 — FTN struct unification (root-cause, unblocks the mail pipeline)
Fixes A0 (C2,C3,C4,H2,H3,H4,M6). Delete all private copies of `MESSAGE_RECORD`,
`MSGBASE_CONFIG`, `FILEBASE_CONFIG`, `FTN_ADDRESS_CONFIG` and all magic offsets in
FTN + LineTask; include the canonical Filer/Support headers. Add compile-time
`assert(sizeof(...))`/offset guards so this can never silently drift again.
*Test:* toss a real packet in + scan one out; verify area match, netmail routing,
AreaFix reply delivery.

## Phase 1 — Remote security hotfixes (ship ASAP)
- C1 Server accept fall-through: `return;` after busy branch; run connect block only inside the successful-accept `if`; guard index `< MAX_LINES`.
- SEC1/SEC2 Path traversal: one shared `ftn_sanitise_filename()` rejecting `^ $ : & @` and leading/embedded `.`; apply to arcmail extract and FREQ; add auth/state gate to `binkp_handle_get`.
- SEC3 packet body heap overflow: size `clean_body` `raw_len+2` (or bound the terminator write).
- SEC6 `/api/areas`: `snprintf` with remaining space, break on would-truncate.
- SEC4 echofix over-read: clamp `body_len` to buffer size (don't trust vsnprintf return).
- SEC5 session tokens: seed from `OS_ReadMonotonicTime` + address entropy + counter, widen state; or gate web-auth behind an opt-in flag until hardened.
- SEC7 scanner group token bound; SEC8 ZIP size cap + compressed/uncompressed sanity; SEC9 frame-buffer sizing.

## Phase 2 — RISC OS 5 stability
- RO1 Serial: call `OS_SynchroniseCodeAreas` after loading a block driver, before first call. **Highest single RO5 crash fix.**
- RO2 Block drivers: switch to X-form Pipes SWIs, keep `BVS` handling, fix `func_getbyte` error path.
- RO3 SVC stack: move large scratch buffers in Filer (and Support/Doors) SWI handlers to module workspace/heap.
- MOD1 bound Filer up/download `fread`/`fwrite` lengths; MOD2 clamp area_count/base_count after SET_BASE; MOD3 bound FIND_UNEXPORTED count; MOD5 add missing `default`; MOD4/6/7 buffer termination + reentrancy.

## Phase 3 — LineTask caller-side crash/robustness
- LT1 audit every inline Filer/msgbase/filebase SWI result — treat **both 0 and -1** as failure before deref (use `transfer:125` pattern). Consider a single wrapper helper.
- LT2 fix CRLF `body_offset` desync (reader + quote).
- LT11 apply `MAX_ENUM_ITERATIONS` to all `while(1)` enumeration loops.
- LT8 move oversized stack arrays to heap; LT7 raise expansion buffers to documented size or clamp+document; LT12 unchecked mallocs, integer overflows, NULL-guard ordering.

## Phase 4 — Session lifecycle correctness
- LC1 call `transfer_cleanup` in `perform_session_disconnect`; LC3 chat reset; LC5 install exit handler that runs disconnect.
- LC4 defensive full state-reset on CONNECT (don't trust prior DISCONNECT).
- LC2 single-line logoff must close the socket; LC6 detect ECONNRESET.
*Test:* connect→drop mid-transfer→reconnect on same line; verify clean state.

## Phase 5 — Door subsystem repair
- DR1 add native-door input branch + reorder poll so the door reads before the stream drain.
- DR2 re-send user info after the door registers (or have Register preserve pre-set info).
- DR3 push real logged-in user to ARCbbs doors; DR4 line number + username source; DR5 real system info.

## Phase 6 — Access-control & feature correctness
- AC1 honour N in new-user confirm; AC2 add access check to `filebase download <id>`; AC3 wire ratios or remove the claim; AC4 newscan public posts.
- LT4 de-block the freezes: chunk the post-upload file copy across polls; make LOGINSCAN incremental; async/confirm OSCLI.
- LT10 set outbound `orgaddr`.

## Phase 7 — Big features: BUILD or CUT (DECIDED 2026-07-07)
- **F1 SENDMAIL/SENDNETMAIL — BUILD** (thin wrapper over `messagebase compose netmail`).
- **F2 YMODEM / YMODEM-G / ZMODEM — BUILD** (full state machines; CRC-32 helpers already exist).
- **F3 ConverseDoors messaging — BUILD** (implement SendMessage/ReceiveMessage SWIs).
- **F4 ARCbbs door SWI table — CUT**: do NOT build the fictional GetBuffer/GetByte/…
  set; instead Phase 8 rewrites `Docs/ARCbbs/Doors` to document the real API
  (ReadStatus/WriteStatus/SendRequest/GetReply/InputRead/OutputWrite/…).

## Phase 8 — Documentation reconciliation
Fix A9: config paths/keys, FTN limits/defaults/undocumented blocks, SWI struct
layouts, script counts & enum table, ARCbbs door SWI table; document the working-but-
undocumented surface (Web app, FTN domains/downlinks/FileFix, SerialConfig, host SWIs,
RiscBBS doors). Add the "update Docs when changing SWIs" rule to CI/review.

---

## Progress log
- **Phase 0 — DONE** (except deferred H3): tosser/scanner/echofix struct copies corrected to canonical + magic offsets fixed + `sizeof==748` guards; LineTask FTN address read (H4) and outbound `orgaddr` (LT10) fixed. **Deferred:** H3 FileFix filebase config read (fail-closed now; needs filebase structs + a FileFix access-policy decision).
- **Phase 1 — DONE** (branch `security-hotfixes`): C1, SEC1/2 (shared `ftn_filename_safe` + FREQ auth gate), SEC3, SEC4, SEC5, SEC6, SEC7/8/9.
- **Phase 2 — mostly DONE**: RO1 (Serial `OS_SynchroniseCodeAreas`), MOD1 (Filer block length caps), MOD2 (Support area/base count clamp), MOD3 (FIND_UNEXPORTED clamp), MOD5 (AccessConfig default), RO2 (block-driver X-form SWIs + BVS), RO3 logging-buffer slice.
  - **RO2 caveat:** block drivers ship as pre-assembled `,ffa` binaries — the `.s` fix needs re-assembly via `Pipes/blockdrivers/Mk,feb` (objasm) to take effect.
  - **RO3b deferred:** ~30 `char[300]` path buffers in `Filer/c/{filebase,messagebase,cache}` still on the SVC stack (MEDIUM). Follow-up.
- **Verification note:** all edits reviewed structurally (brace balance, includes, C90 decl order). Not yet compiled — needs the Norcroft DDE toolchain on a RISC OS build host.

## Suggested milestones
- **M1 "Safe":** Phases 1+2 → no remote compromise, no RO5 boot-crash.
- **M2 "Correct":** Phases 0+3+4 → FTN works, no caller crashes, clean sessions.
- **M3 "Complete":** Phases 5+6+7 → doors, access control, feature decisions.
- **M4 "Documented":** Phase 8 → docs match reality.
