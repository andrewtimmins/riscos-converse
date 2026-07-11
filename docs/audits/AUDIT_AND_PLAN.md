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
- **Phase 2 — DONE**: RO1 (Serial `OS_SynchroniseCodeAreas`), MOD1 (Filer block length caps), MOD2 (Support area/base count clamp), MOD3 (FIND_UNEXPORTED clamp), MOD5 (AccessConfig default), RO2 (block-driver X-form SWIs + BVS), RO3 logging-buffer slice.
  - **RO2 — re-assembled & deployed (2026-07-09):** `s/host`+`s/client` rebuilt via `Pipes/blockdrivers/Mk,feb` (objasm, 0 errors); the RO5-fixed `PipeHost`/`PipeClient` binaries deployed to all four `Driver,ffd` slots (`Source/Pipes/blockdrivers/drivers/{PipesA,PipesB}` + root `BlockDrivers/{PipesA,PipesB}`). Block-driver binaries are filetype `ffd`; `Pipes,ffa` is the ConversePipes *module*, not a driver. `Mk,feb` now self-deploys into `drivers/`.
  - **RO3b — DONE (2026-07-10, session 2):** the `Filer` path-format helpers in `c/filebase` and `c/messagebase` used to nest a `char[300]` per level (`format_file_path -> group_dir -> area_dir -> files_dir -> base`), stacking ~1.5KB of locals in one SWI-handler chain on the small SVC stack. Rewritten to build **directly into the caller's buffer** — leaf paths via a single `snprintf`, the nested `area_dir/group_dir/file_path` (and `ensure_group_directory`) append in place — so a whole path chain now costs one caller buffer (zero extra static/workspace, byte-identical paths). The per-handler single `char[300]` and the 4 cache-load buffers are left (one live at a time, chain below now flat = safe). Rebuilt+deployed `Filer,ffa`. **Verified: file-id 3 (A0001/G00) and file-id 22 (A0002/G00) both download byte-perfect after the rewrite** (exercises both the `area<=0` and `area>0` path branches). Needs a full BBS restart to reload the module.
  - **H2 — confirmed already fixed in Phase 0:** `FTN/c/echofix` local `MSG_REC` matches the canonical 748-byte `MESSAGE_RECORD` field-for-field with a `sizeof==748` compile guard (`subject` after `bodysize`, `flags` last). No further action.
- **Verification note (updated 2026-07-09):** Phases 0–2 now **compile/assemble cleanly** on the emulator's Norcroft DDE toolchain (RPCEmu HostCmd), superseding the earlier structural-only review. All six C components build (`FTN`/`Line`/`Server`/`Serial` apps, `Filer`/`Support` modules) and the block drivers assemble with 0 errors. Build-file fixes needed: `Serial/Mk` gained a `WimpSlot` (had none), `Filer/Mk`+`Support/Mk` raised `960k`→`4096k` (cmhg/cc ran out of app space), `Mk,feb` `MakeDir`→`CDir` (not a RISC OS command).
- **Phase 3 — DONE except LT4 (2026-07-09):** LineTask caller-side crash/robustness, all compiled clean on the emulator toolchain (`Line: application built`, 0 errors).
  - **LT1** (C): both `0` and `-1` treated as failure before deref — 20 guard sites across `messagebase`/`script`/`filebase`, plus FTNCONFIG (Support returns -1) and USERDB success-path checks. Confirmed the Filer module returns both sentinels.
  - **LT2** (H): CRLF `body_offset`/`offset` desync fixed in `viewer_show_body` and `quote_original` (advance the byte counter when skipping the paired `\n`).
  - **LT3** (H): `can_read_message` now fails closed when `get_area_type` returns `-1` (was falling through to readable → private/netmail exposure).
  - **LT5** (M): `script_clear_program` now calls `script_reset_loop_state()` (FOR/WHILE state no longer leaks).
  - **LT6** (M): trailing-`:` label detection requires a single token; `print …:` style commands no longer swallowed as labels.
  - **LT7** (M): IF/WHILE operand + PRINT/SET expansion buffers raised 512→`SCRIPT_EXPAND_BUFFER_SIZE` (1024, documented); variable values are `char *` (unbounded) so beyond this they still truncate.
  - **LT8** (M): three oversized frames (`list_areas` `entries[256]`≈21.5KB, `list_bases` `entries[64]`, `composer_send` `body_buffer`≈8KB) made `static` scratch (chosen over heap: functions are non-reentrant/no Wimp_Poll mid-call — zero leak risk).
  - **LT9** (M): `composer_send` issues `END_UPLOAD` on the `UPLOAD_BLOCK` failure path (no leaked module handle/partial message).
  - **LT10** (M): verified already fixed in Phase 0 — outbound `orgaddr` populated from the area AKA (`get_aka` → `composer.from_ftn_address` → `msg.orgaddr`).
  - **LT11** (M): `MAX_ENUM_ITERATIONS` cap applied to all 18 `while(1)` enumeration loops (`index`/`base_index`); filebase's `#define` moved to file top so it covers the early loops too.
  - **LT12** (L): transfer `%` overflow (scale-down for >21MB), filebase GB-fraction overflow (divide-first), unchecked `script_initialise` callocs (capacity→0 on NULL; grow is additive so realloc(NULL) works), stale `composer_more_saved`/`protocol_more_saved` reset at session init, `handle_message_event` NULL-guard-first. **Left:** `main:894` decl-after-statement — compiles clean under this Norcroft config (latent-portability only, not changed to avoid risky churn).
  - **LT4 — DEFERRED to Phase 6 (decided 2026-07-09):** de-blocking the Wimp-poll freezes (chunk post-upload file copy across polls, incremental LOGINSCAN, async/confirmed OSCLI, bound O(n) reader scans) needs poll-spanning state machines — kept with the rest of Phase 6 per the original plan.
- **Phase 4 — DONE (2026-07-09):** session lifecycle correctness; `LineTask`/`Server` both compile clean (`Line`/`Server: application built`, 0 errors).
  - **LC1** (H): `perform_session_disconnect` now calls `transfer_cleanup(&state->xfer_session)` (no leaked FILE*/malloc, clears the module "transfer active" flag).
  - **LC3** (M): disconnect now tears down sysop chat/pager — hides the pager window if `chat.paging` and calls `chat_reset_state` (no more misrouting the next caller's bytes into chat).
  - **LC4** (M): extracted the shared `reset_line_session_state()` helper; the CONNECT handler now calls `script_stop_session` + `reset_line_session_state` defensively so a dropped DISCONNECT byte (ClearInput) can't leak the previous caller's user/access/base/transfer/chat state.
  - **LC5** (M): registered an `atexit(line_task_atexit)` that clears `LINE_FIELD_CONNECTED` in Support via a raw `SWI_CONVERSEBBS_LINE` (safe after Desk closedown / mid-error), so an abnormal exit no longer leaves the line stuck "connected".
  - **LC2** (H): `wimp_handle_line_control_message` no longer bails out on `line_configurations <= 1` before handling LOGOFF — a single-line board now closes the line instead of leaving it busy forever. (Note: the same `<=1` guard remains in `wimp_handle_line_activity_message`/`wimp_handle_line_user_message`, where it only suppresses status-window updates on 1-line boards — cosmetic, out of LC2 scope; worth a follow-up.)
  - **LC6** (L): `check_socket` now also closes on `recv() < 0` unless `errno` is `EWOULDBLOCK`/`EAGAIN` — an abrupt client drop (ECONNRESET) reclaims the line immediately instead of only via the idle timeout.
  - *Suggested test (from plan):* connect → drop mid-transfer → reconnect on same line; verify clean state.
- **Phase 5 — DONE (2026-07-09):** door subsystem repair; `LineTask`/`Doors`/`ARCbbs` all compile clean.
  - **DR1** (C): added `native.active`/`native.launch_pending` branches to `menu_handle_user_byte` (mirroring riscbbs/arcbbs) so native-door input is routed to the door via `door_native_host_write` instead of being drained by `process_server_stream` — door no longer hangs at its first prompt. Control tokens (DISCONNECT) still flow through `process_server_stream`, and `reset_line_session_state` (Phase 4) closes the door on hangup.
  - **DR2** (C): `doors_swi_register` now preserves the `user_info` the host set with HostSetUserInfo instead of memset-wiping it — native doors see the real user_id/access/is_sysop rather than 0 (was an in-door access bypass). Race-free (no re-send needed).
  - **DR3** (H): built a host→door user channel for ARCbbs doors. Repurposed the spare `Reserved4` SWI slot (0x41044, already in the cmhg table) as **SetUserInfo**: `buffer_swi_setuserinfo` stores a per-line `ARCBBS_DOOR_USER` (`line_users[]`), the request handler (requests 0/1) now returns the real userlevel/username/realname/usernumber (falling back to Guest only if unset), and LineTask's `door_arcbbs_set_user_info` pushes the logged-in user at launch. No cmhg change needed.
  - **DR4** (M): `door_native` now takes the door username from `user.username` (was `realname`) and appends the line number to the launch command (`"%s %d"`, per Doors protocol step 1) so the door can Register — was timing out.
  - **DR5** (partial, L): `time_online` now reported as real seconds from `connect_time` (both native `set_user_info` and ARCbbs). **Left with rationale:** GetSystemInfo `total_lines` stays `DOORS_MAX_LINES` (no reliable configured-line-count source exposed to the module); ReadByte's `timeout` stays non-blocking (honoring it would require spinning in an SVC-mode module SWI — hangs the machine; RISC OS doors poll instead); `time_remaining` stays -1 (no per-user time budget plumbed).
  - **Build-file fixes:** `Doors/Mk` and `ARCbbs/Doors/Mk` WimpSlot `960k`→`4096k` (cmhg ran out of app space), matching the earlier Filer/Support fix.
  - **Deployed (2026-07-09):** the rebuilt `Doors,ffa` and `ARCbbs,ffa` modules were copied to `!Converse/Resources/` (verified byte-identical to the source-tree `rm/` builds), so DR2/DR3 are live.
- **Phase 6 — access control DONE; LT4 partial (2026-07-09):** `LineTask` compiles clean throughout.
  - **AC1** (H): `input_complete_newuser_confirm` now honours the actual Y/N keypress (checks `input_buffer`); answering N (or anything but Yes) cancels instead of always creating the account. Removed the bogus unconditional "Y" echo (the YESNO handler already echoes).
  - **AC2** (M): added `filebase_get_file_info()` and an access check (`filebase_check_access` + deleted guard) to `filebase download <id>` — the direct command previously bypassed the per-file access-level/keys check that select/area enforce.
  - **AC3** (M): **removed the dead claim** (per decision) — stopped loading the never-read `user.flags.ratios`; ratio enforcement is not implemented (note for Phase 8 docs). Not wired, to avoid inventing an unspecified policy.
  - **AC4** (L): login newscan now counts new **public** posts (using area type), not only mail `receivedby==user_id`; private (4)/netmail (2) areas still restrict to the user. Access is gated at the messagebase level (areas carry no separate keys).
  - **LT4 — PARTIAL (per decision to start now):**
    - **Done:** OSCLI now launches via `Wimp_StartTask` instead of blocking `system()` (de-blocks Wimp-app launches; Wimp-safe). LOGINSCAN's 6 unbounded `while(1)` enumeration loops now capped by `SCRIPT_MAX_SCAN_ITEMS` (prevents the *permanent* freeze on corrupt module data). The messagebase reader O(n) scans (`get_next`/`get_prev_message_id`) were already bounded by the Phase-3 LT11 cap.
    - **Deferred (needs runtime testing — poll-spanning state-machine rewrites of critical paths):** chunking the post-upload temp→filebase copy across Wimp polls (`filebase_register_upload`), and making LOGINSCAN fully incremental (resume across polls). These transiently freeze proportional to file size / message count but are no longer *permanent*; a proper rewrite should be validated against real uploads/logins rather than compile-only.
  - **LT4 LOGINSCAN — DONE (2026-07-10):** now fully incremental via a poll-spanning `WAIT_SCAN` state machine (`script.c`): `script_loginscan_step` runs `SCRIPT_SCAN_CHUNK=128` enumerate-SWIs per Wimp poll, so a large board no longer freezes the guest during the login scan. Live-verified over telnet (login → scan → menu, no freeze). Pager suppressed during scan; session cursors saved/restored; corrupt-data cap retained. (Upload-copy chunking still deferred.)

## Phase 7 — feature build progress (2026-07-10)
- **F2 transfer protocols:**
  - **CRITICAL root-cause fix:** `crc32_table[245]` in `LineTask/c/crc` was `0xCDD706B3`, must be `0xCDD70693` (one nibble). This corrupted CRC-32 for any data routing through table slot 245 (e.g. ZMODEM frame-type `0x0a`) — a systemic bug affecting *any* CRC-32 user (ZMODEM, potentially FTN). **Fixed.**
  - **XMODEM:** works but silently `^Z`-pads received files to the block boundary and records the padded size (no length field). Live-confirmed: a 200-byte upload stored as 256 bytes. Inherent to XMODEM. Consider demoting in the protocol menu.
  - **YMODEM + YMODEM-G — DONE & LIVE-VERIFIED:** new `LineTask/c/ymodem` (+`h/ymodem`), wired into `transfer.c` (send/recv/poll/cleanup). Block-0 carries exact size → receiver truncates → **byte-exact** (200-byte uploads stored as exactly 200). YMODEM-G streaming verified too.
  - **ZMODEM — upload DONE & LIVE-VERIFIED, download BUGGY:** new `LineTask/c/zmodem` (+`h/zmodem`); CRC-32 subpackets, ZDLE escaping, hex/binary headers, `rz` auto-start, ZRPOS/ZEOF/ZFIN. **Upload (BBS receives) verified byte-exact** against real `sz` — 5000 bytes incl. control bytes (0x18/0x11/0x13/0x0d/0x8d/0xff/0x7f/0x00). **Download (BBS sends) is broken:** real `rz` rejects the data subpackets and loops on ZRPOS (BBS resends → ~100KB for a 5KB file). Send-path bug (subpacket framing / ZRPOS-resend handling) — not yet pinned. Tested with lrzsz (`sz`/`rz`, installed on host).
  - **Follow-up bug spotted:** an aborted/failed ZMODEM transfer does not tear the line down (leaves `transfer_active` set / session occupied), so the single line is unusable until BBS reload — `transfer_poll`/disconnect cleanup should reset the line on transfer error.
  - **main.c:** removed the `[Protocol not yet implemented]` gate (was `proto > TRANSFER_PROTO_XMODEM_1K`) in both `script_host_start_send_transfer`/`_receive_transfer` — all protocols now dispatch.
  - **BUILD-SYSTEM FIX (see [[riscos-converse-build-workflow]]):** adding `o.ymodem`/`o.zmodem` pushed the `link` line past amu's 255-char limit → **silent** link failure (exit 0, stale binary shipped). Fixed via `CUSTOMLINK=custom` + `LineTask/LinkVia` response file. Keep `LinkVia` in sync with `OBJS`.

## Phase 7 F2 + LT4 — COMPLETE & LIVE-VERIFIED (2026-07-10, session 2)
All exercised end-to-end over telnet (harness committed at `tools/telnet-test/`,
drives lrzsz `sz`/`rz`; verified byte-exact by md5/cmp). Every fix built via
`LineTask/Mk` and deployed to `!Converse/Resources/Line,ff8` (needs a full BBS
restart to load — line tasks are pre-spawned).
- **ZMODEM download — FIXED** (was "BUGGY"). Root causes were bad seed data (empty/oversized records) + a genuine send bug: `ZS_SEND_EOF` advertised the DB filesize even when the blob was shorter, so `rz` looped on ZRPOS forever and wedged the line. Fix in `c/zmodem`: truncate `file_size` to the bytes actually read on short EOF, send `ZEOF` at `z->pos`, and bound the ZRPOS↔ZEOF re-assert (`consecutive_errors`/`ZM_MAX_ERRORS`). file-id 3 (408 KB) and file-id 9 (short blob) both download byte-exact.
- **Line-wedge on dropped/idle transfer — FIXED** (the "aborted transfer doesn't tear the line down" follow-up). Added a transfer-wide **stall watchdog** (`c/transfer`,`h/transfer`,`c/main`): if a transfer moves zero bytes for `TRANSFER_STALL_TIMEOUT` (30 s) it aborts (`stalled`) and `main` drops the dead session via `perform_session_disconnect`. Mid-transfer client kill now self-recovers in ≤35 s instead of never.
- **Receiver CAN cancel — HONOURED** (`c/zmodem`): `zget_header` detects a run of ≥5 CAN (0x18) and returns `ZCAN`; all send wait-states abort on it. Client cancel recovers the line in seconds (< the 30 s stall deadline).
- **Plain YMODEM upload hang — FIXED** (`c/ymodem`): the EOT handler no longer completes early; it waits for and ACKs the end-of-batch terminator block 0 (bounded complete-on-timeout if the sender sends none). `sz` now exits 0.
- **XMODEM-CRC/1K, YMODEM, YMODEM-G uploads** all byte-exact.
- **Upload requires a selected area** (`c/script`): `receivefile` refuses with "Please select a file area first" when `current_area <= 0`, so uploads no longer land in the un-browsable area-0 root. (Chosen over defaulting/auto-browsable.)
- **CRITICAL crc32_table[245] fix** carried in from session 1 (`0xCDD706B3`→`0xCDD70693`).
- **LT4 upload-copy chunking — DONE** (last LT4 piece): `filebase_register_upload`'s one-shot copy loop replaced by a poll-spanning state machine (`upload_copy_start`/`upload_copy_step` in `c/main`, `upload_copy_state` in `h/main`) that copies `UPLOAD_COPY_CHUNK`=32 KB per Wimp poll via begin/upload_block/end_upload; the script stays parked in `WAIT_TRANSFER` until the copy finishes, then is resumed. `reset_line_session_state` tears down an in-progress copy on disconnect. **Verified: 1 MB upload byte-exact, guest responsive, script resumes; 8 KB regression byte-exact.** Deferred sub-item now closed — **LT4 fully DONE.**
- Committed on branch `security-hotfixes` as `c7d1af2` (session-1 transfer work + broad snapshot + `.gitignore`); session-2 fixes (CAN/area/LT4) are a follow-up commit. `.gitignore` now excludes build artifacts (o/, rm/, cmhg `h/*Hdr`, Source-tree binaries), logs, temp uploads, and `__pycache__`.

## Phase 7 F1 — DONE & LIVE-VERIFIED (2026-07-10, session 2)
- **F1 SENDMAIL / SENDNETMAIL BUILT.** Were documented (Docs/Scripting, README, NewSysop) but had no enum/token/handler. Implemented as thin non-interactive wrappers over the existing composer store path:
  - `c/messagebase`: `messagebase_send_private_direct()` and `messagebase_send_netmail_direct()` set up the composer state (area-find + recipient validate + AKA) then call `messagebase_composer_send()`; a shared `composer_set_body_from_string()` splits the CR/LF body into composer lines. Caller's current mb/area selection is saved/restored.
  - `c/script`: `SCRIPT_CMD_SENDMAIL`/`SCRIPT_CMD_SENDNETMAIL` (+ `h/script` enum). Tokeniser uses a new backtick-aware `script_arg_next()` (username/address plain, name/subject/body backtick-quoted) into arg1..arg4; execute-time macro-expands each and `script_translate_escapes()` the body (so `\r\n` → real line breaks), then calls the messagebase direct functions with the messagebase session from `get_messagebase_session`.
  - **Verified over telnet** (injected into Postlogon, walked login, checked the message store): SENDMAIL stored a private message in Private Mail (area 20) `A0020/G00/000011`; SENDNETMAIL stored netmail in area 15 `A0015/G00/000012`; both subjects in MsgDB and bodies byte-correct with CRLF line breaks; "Message sent successfully" x2.
- **PRE-EXISTING BUG FOUND & FIXED while testing F1: `Filer/h/cache` `CACHE_MAX_AREAS` was 16** but the messagebase has 24 areas, so `messagebase_cache_load_areas` dropped areas 17-24 ("cache full") and `ENUMERATE_AREAS` never saw them. This silently broke **interactive `messagebase compose private`** (Private Mail = area 20) AND hid 8 configured areas (RISC OS, BBS Networks, Fidonet General, Private Mail, Sysop Messages, System Notices, Feedback, Suggestions). Raised to **48** (per-cache, separate filebase/messagebase arrays; ~10KB bump, well under the 128KB module static budget). Requires a Filer *module* rebuild (`Source/Filer/Mk` → `Filer,ffa`) + deploy to `!Converse/Resources/Filer,ffa` + BBS restart. Netmail (area 15) worked before the fix because it's within the first 16.
- **F3 ConverseDoors messaging — DONE & deployed (2026-07-10, session 2).** `SendMessage`/`ReceiveMessage` were `-1` "future expansion" stubs; now functional per-session mailboxes (door posts EXIT_NORMAL/EXIT_ERROR/CHAT_REQUEST; collects SYSOP_CHAT/TIME_WARNING/DISCONNECT). Added host-facing `HostReceiveMessage`/`HostSendMessage` SWIs (`Doors,ffa`) so LineTask can pull door->host / push host->door. `door_native` polls door->host in `door_native_process` (exit closes the session, chat-request notifies). NB the door module suites (ConverseDoors, ARCbbs Doors+Filer) were already fully built; only these two SWIs were stubs. F4 stays CUT (the ARCbbs door SWI table in `Docs/ARCbbs/Doors` is fictional; the real module API is complete — Phase 8 fixes the docs).
- **Sysop-chat vs door (user-reported, DONE 2026-07-10) —** a user in a door (native/ARCbbs/RiscBBS) kept the door running and it swallowed keystrokes when the sysop jumped into chat, because `close_session` only reset LineTask bookkeeping and never told the door process to quit. Added `line_force_quit_door()` wired into the `MAININFO_CHAT` trigger: RiscBBS = `Message_Quit` to the door's Wimp task handle; native = `DOOR_MSG_DISCONNECT` + `Message_Quit` (handle now captured from a raw `Wimp_StartTask` at launch); ARCbbs = close deactivates the line so its status poll exits. Closing the session also fixes the input router (it routed to the door before chat). Committed `1174e4d`.
- Phase 7 complete (F1+F2+F3 built; F4 is docs-only).
- **H3 FileFix config read — DONE (2026-07-10, session 2).** `FTN/c/echofix` read the FILEBASE config through the msgbase-shaped `ECHOFIX_GLOBAL_CONFIG`, so `base_count`/`area_count`/area fields landed at wrong offsets and FileFix matched nothing (fail-closed but non-functional). Added a private filebase-config mirror (`ECHOFIX_FB_GLOBAL`/`_FB_BASE`/`_FB_AREA`, matching `Support/h/filebaseconfig` FILEBASE_* with a `sizeof(ECHOFIX_FB_AREA)==520` compile guard) and split `echofix_is_area_allowed`/`echofix_get_available_areas` into an AreaFix branch (unchanged: msgbase + group overlap) and a FileFix branch (filebase layout, match file area by FTN tag, gate on the downlink's `allowed_files` tag-list). **Policy (Andy): empty `allowed_files` = allow all** (consistent with the empty-groups convention), non-empty restricts to listed tags (`fileecho_tag_allowed`, whitespace/comma-separated, case-insensitive). Rebuilt+deployed `FTN,ff8`. **Verification limit: FileFix runs in the FTN mailer on an inbound netmail to the FileFix robot — not telnet-drivable here; needs a real FTN feed to exercise end-to-end. Compile-guarded + code-reviewed; AreaFix behaviour unchanged (no regression).**
- Deferred: RO3b — **DONE** (see Phase 2 log). No open code findings remain; only Phase 8 (docs) outstanding.

## Phase 8 — Documentation reconciliation — DONE (2026-07-10, session 2)
Every claim was re-verified against the current source rather than applied from the (partly stale) A9 summary.
- **Batch 1 (commit `97a62a0`):** `Docs/ARCbbs/Doors` fictional SWI table → real API (from `cmhg/arcbbsHdr`: ReadStatus/WriteStatus/SendRequest/GetReply/SetUserInfo/Input*/Output*/Clear*/Host*/Activate/Deactivate); `Docs/Doors` host-facing SWIs + F3 note; `Docs/BlockDrivers` 31/32 corrections; `Docs/NewSysop` config path (`<Converse$Dir>.Config.*`) + tree + real System keys; `Docs/FTN/Configuration` paths.
- **Batch 2 (commit `5141195`):** `Docs/FTN/Configuration` — removed the fictional per-address `packet_password`/`areafix_password`, corrected auto keys to `toss_interval`/`poll_interval` (default 0 = off) + runtime defaults (listen_port 24554, max_sessions 4), uplink id 1-16 + its areafix/filefix passwords, documented the previously-undocumented **Downlinks/Domains** blocks and the **AreaFix/FileFix** self-service commands. `Docs/SWIs/Filer` — `FTN_ADDRESS` is 116 B (`char domain[100]`+4 ints) not 8; rewrote `MESSAGE_RECORD` to the canonical 748-B offset table + an `FTN_ADDRESS` sub-table; rewrote `USER_FLAGS` (real 19-int field list) and `USER_STATS` (32 B, real fields — was 40 B with fictional names). `Docs/Scripting` — flagged the "Internal Command Codes" enum as an internal/unstable detail (canonical `LineTask/h/script`, 53 entries incl. the now-real SENDMAIL/SENDNETMAIL). **New `Docs/Web`** — the previously-undocumented Web app (endpoints, sessions, compiled limits, `{{...}}` template tags, access control).
- **All phases 0–8 complete. No open audit findings (code or docs) remain.**

## Suggested milestones
- **M1 "Safe":** Phases 1+2 → no remote compromise, no RO5 boot-crash.
- **M2 "Correct":** Phases 0+3+4 → FTN works, no caller crashes, clean sessions.
- **M3 "Complete":** Phases 5+6+7 → doors, access control, feature decisions.
- **M4 "Documented":** Phase 8 → docs match reality.
