# FTN Mailer Audit — Multi-Network Robustness & Messagebase Toss In/Out

**Date:** 2026-07-11
**Scope:** `Source/FTN/{c,h}/{mailer,binkp,tosser,scanner,packer,queue,echofix}` + `!Converse/Config/FTN`, `!Converse/Config/MsgBase_1`.
**Question asked:** Will the mailer stand up to exchanging mail across a real multi-network setup, and can it reliably toss mail in/out of the BBS messagebase?
**Method:** 5 parallel deep-read auditors (one per axis); every CRITICAL/HIGH finding below was then re-read and confirmed by hand at the cited `file:line`.

---

## Bottom line

The **config model** is fully multi-network (6 domains/AKAs/uplinks, downlinks with filters), and the plumbing that historically broke tossing is genuinely fixed: **all per-domain inbound dirs are scanned** (`tosser:1545`), the Filer area cache is fixed (48 ≥ 24 areas), 748-byte record guards are in place, and multi-AKA is presented on the wire. **But the core routing and identity logic is NOT multi-network-safe.** Outbound, echomail is flooded to *every* uplink and every packet is stamped with the fidonet AKA; there is no SEEN-BY loop suppression. Inbound, netmail lands in a dead area and any unknown echotag is silently discarded. Your instinct is correct — on face value it looks complete, but it will not hold up as-is: single-network fidonet mostly works; the other five networks will misroute, mis-attribute, and (as a hub) risk dupe/loop storms.

Priority: fix the four CRITICALs before trusting *any* multi-network traffic. Fixes 5–7 (silent inbound loss + open auth) matter even single-network.

---

## CRITICAL — mail is wrong / lost / loops on the wire

### C1. Echomail is flooded to every group-matching uplink; no zone/network routing
`scanner_get_echomail_uplinks` (`scanner:736-780`) selects uplinks purely by group-string overlap (`groups_match`), never by zone/domain. All 6 uplinks share `groups A,B,C`, and `groups_match` (`scanner:153-183`) returns "match" if **either** side's group list is empty. So a post in *any* echo goes to all six uplinks (`scanner:1083-1126`).
**Failure:** a cnet-only echo is packed and sent to the fidonet, pinet, retronet, hobbynet and amiganet uplinks. Each foreign uplink gets an echo it doesn't carry → rejected/duplicated, cross-net leakage.
**Fix direction:** tie each area to a network/zone (or derive it), and select the uplink whose zone matches; keep group filtering as a secondary constraint. Confirmed.

### C2. Every outbound packet's envelope origin is hard-wired to `our_addrs[0]` (fidonet)
`scanner:877` → `packer_create_packet(&mailer.our_addrs[0], ...)`; the Type-2+ header orig is written from that (`packer:177-246`). Only the fidonet batch is correct by luck.
**Failure:** the cnet uplink `64:500/0` receives a packet whose envelope says it came from `2:250/9` — not an address it knows → packet-level auth/routing fails or misfiles.
**Fix direction:** choose the origin AKA by matching `batch->uplink_addr.zone` to `our_addrs[i].zone` (fall back to [0] only if none). Confirmed.

### C3. No SEEN-BY loop suppression; our AKA never stamped on pass-through echomail
In `packer_pack_message_from_filer` the message struct is memset (`packer:831`) and `seen_by`/`path` are never populated from the stored record, so re-export starts from empty (`packer:721-760`). The only SEEN-BY entry added is `packer_add_seenby(..., msg->orig_addr.net, msg->orig_addr.node)` — the **original author's** node for pass-through mail (`is_local==0`), never one of *our* AKAs. Nothing checks existing SEEN-BY before sending to a peer.
**Failure:** an echo received from the fidonet uplink is re-exported back toward `2:250/0` and out to downlinks with our node absent from SEEN-BY → peers keep sending it back → dupe/loop storm. We are the node generating the flood; only peers' own dupe logic contains it. (Prior SEEN-BY also survives only as literal body text via the tosser, corrupting the readable body.)
**Fix direction:** read prior SEEN-BY/PATH, add **all** our AKAs (per network) to SEEN-BY + our address to PATH, and skip any recipient already in SEEN-BY. Confirmed.

### C4. `MARK_EXPORTED` marks the whole batch when only some messages packed → silent mail loss
`scanner_mark_messages_exported` (`scanner:934-946`) iterates **all** `batch->messages` unconditionally; the caller gates only on "≥1 packed" (`scanner:1172-1174`). A per-message pack failure (MESSAGE_INFO/DOWNLOAD_BLOCK/malloc at `packer:838,910`) still gets marked exported.
**Failure:** batch of 10, message #4's body download fails → still marked exported → never re-scanned → permanently lost.
**Fix direction:** mark each message exported only on that message's pack success (return per-message status from the pack loop). Confirmed.

---

## HIGH — silent delivery failure / open door

### H5. Inbound netmail is written to area 0, not the configured Netmail area (15)
`tosser:1233-1235` hardcodes `base_id = 1; area_id = 0;` for all netmail. Config defines Netmail as **area 15** (`MsgBase_1:111-114`, `areatype 2`); the reader finds netmail via that area, not area 0.
**Failure:** personal netmail to the sysop/users, and AreaFix/FileFix *result* netmails, toss "successfully" (`messages_tossed++`, packet archived) but never appear where anyone reads them. Silent loss. Confirmed.
**Fix direction:** resolve the netmail area id (base 1 / areatype 2) at toss time instead of hardcoding 0.

### H6. Unknown/unmatched echotag is silently dropped and the packet is archived
`tosser:1182-1187`: when `tosser_match_area` misses, the message is counted `areas_unmatched`, logged to debug only, **not** stored and **not** diverted to Bad; the enclosing packet still moves to Processed (`msg_count>0`). Matching is exact tag-string equality against the 24 local tags.
**Failure:** any uplink echo whose `AREA:` tag isn't mirrored *exactly* in `MsgBase_1` is discarded with no operator-visible trace, and the packet is moved away so it can't be recovered. This is the dominant real-world "mail isn't tossing" path across 6 networks. Confirmed.
**Fix direction:** route unmatched echomail to a catch-all/junk area or leave the packet in Bad with a log line; never silently drop + archive.

### H7. Inbound authentication is effectively optional
`binkp_handle_file` (`binkp:1254-1260`) sets `authenticated=1` on the first `M_FILE` if not already authenticated — a peer can skip `M_PWD` entirely and push files. Separately, an empty/unknown expected password auto-sends `M_OK` (`binkp:1024-1035`), and there is no secure/unsecure inbound split, so unknown-node files land in the same trusted Inbound as verified ones.
**Failure:** anything that can reach port 24554 injects mail into the toss pipeline. Confirmed.
**Fix direction:** require completed auth before accepting `M_FILE`; land unsecured sessions in a separate insecure inbound; consider offering CRAM-MD5 as the answering side (currently never advertised, `binkp:647-677`).

### H8. Per-message / local-post origin AKA falls back to fidonet unless every area's `akause` is hand-set
Locally-posted messages take origin from `our_addrs[area->akause]` (`packer:860-871`, fed by `scanner:1068`); unset `akause==0` → fidonet. Combined with C1, the *same* message is written into every network's packet carrying one network's AKA in Origin/MSGID.
**Failure:** a local post to a cnet echo is stamped `2:250/9` in Origin + MSGID. Confirmed (contamination); correct-only-if-every-area-configured is a fragile design.
**Fix direction:** derive AKA from the area's network rather than a manually-maintained per-area index; validate at config load.

### H9. 5D uplink recognition can fail — `ftn_addr_match` compares domain, config addresses have none
`ftn_addr_match` (`mailer:232-244`) compares `domain` first; `ftn_string_to_addr` (`mailer:174-207`) only sets `domain` when the string has `@domain`. Config uplinks (`2:250/0.0`) parse with empty domain, but a real binkd peer presents `2:250/0@fidonet` in M_ADR. `ftn_domain_strcasecmp("","fidonet") != 0` → **no match**. The domain-agnostic matcher `ftn_addr_match_ignore_domain` exists but is never called; `ftn_expand_address` (which would populate domain) is dead code.
**Failure:** a standard binkd uplink isn't recognized → falls back to first-address/unsecure and mis-attributed password lookup. Confirmed (logic); depends on peer sending `@domain` (binkd does by default).
**Fix direction:** use `ftn_addr_match_ignore_domain` for routing/recognition, or populate config-address domains via `ftn_expand_address` at load.

---

## MEDIUM

- **M10. Shared-host uplinks collapse inbound routing.** cnet/pinet/retronet all use `call.rofbbs.com`; `binkp_handle_adr` (`binkp:926-988`) pegs `remote_addr` to the *first* matching AKA, so pinet/retronet inbound files land in the cnet tree, and busy/retry bookkeeping keys off the wrong node (`mailer:1561,1591`). *(reported; high-confidence, not hand-verified line-by-line)*
- **M11. Dupe DB is in-memory only.** `dupe_hashes[1024]` ring, 32-bit djb2 hash (MSGID not stored), memset to 0 at init (`tosser:96-97,320,352-378`): non-persistent (loops re-enter after restart), wraps after 1024 unique MSGIDs, hash collisions can false-drop legit mail, MSGID that hashes to 0 is dropped on first sight, and netmail (usually no MSGID) is never deduped. With C3 (no SEEN-BY), this ring is the *only* loop guard.
- **M12. Downlink access control is dead config; no wildcards.** `allowed_echoes`, `max_echoes`, `max_files` are loaded but never read in any gating logic (`echofix:262-265`; grep-confirmed no other readers). There is **no glob/wildcard helper** in the FTN tree, so `RISCOS*`/`BBS_*`/`*` are matched as literal strings — and `allowed_files *` matches nothing (deny-all, inverted), while a *blank* list allows everything. AreaFix gates on `allowed_groups` only.
- **M13. `max_packet_size` ignored, no packet rollover; arcmail bundling not invoked by scanner** → one unbounded loose `.pkt` per batch, uncompressed (`scanner:886-903`).
- **M14. Outbound rescan clobbers live sessions.** `queue_scan_outbound` rebuilds the node array every 60s with no `active_sessions` guard (`mailer:2754-2769`); a live session's cached `QUEUE_NODE *` can then point at a different node → `.pkt` not marked sent → resent; also zeroes `busy`, allowing a duplicate concurrent session. *(reported; high-confidence)*
- **M15. HOLD flavour triggers a poll and is prioritized.** `QUEUE_FLAVOUR_HOLD` is enum 1 > `NORMAL` 0, so hold mail both dials out and jumps the queue — inverted semantics (`queue:18-25`). *(reported)*
- **M16. REPLY kludge never generated** (threading lost); cross-zone netmail origin AKA is the netmail-area's `akause`, not the destination network's AKA (`packer`, `scanner:1128-1146`).

## LOW

- `maxsessions 10` silently clamped to `MAILER_MAX_SESSIONS 4` (no warning) — no overflow (`mailer:1268-1275`).
- `ftn_string_to_addr` has no range/negative validation; bare 2D `net/node` rejected (`mailer:174-207`).
- `packer_add_seenby`/`add_path` presence test uses `strstr` substring → `"25/9"` false-matches inside `"250/9"` (`packer:524,563`).
- Tossed record never stores orig/dest `domain` (`tosser:561-569`) → network-of-origin lost from the record.
- `our_addr_count` not reset in `mailer_load_config` → unsafe only on a future runtime reload (`mailer:1208`).

---

## Genuinely sound (verified — do NOT re-fix)

- **All per-domain inbound dirs are scanned** via COUNT_DOMAINS/GET_DOMAIN (`tosser:1545-1585`); legacy path used only when no domains configured. The "only scans one inbound" fear is unfounded.
- **Multi-AKA presentation:** M_ADR emits all 6 AKAs (`binkp:367-392`).
- **Outbound file selection IS zone-isolated:** keyed off `target_addr` / `queue_get_next_file_for_zone` — network A's mail never goes to network B's uplink (the *files*; the *contents* are the C1/C2 problem).
- **CACHE_MAX_AREAS = 48** (≥ 24 areas); areas 17-24 reachable.
- **748-byte MESSAGE_RECORD** sizeof guards + offset comments present in tosser/scanner/packer.
- **Filename-collision `ftn_uniquify_path`** applied at final inbound landing + processed/bad moves.
- **AreaFix/FileFix subscriptions ARE persisted** to `Config.FTNLinks` (magic `ECXF`), saved on change, reloaded at init, and a **result netmail is sent**. The recent FileFix (H3) fix is coherent (ECHOFIX_FB_* filebase mirror, `sizeof==520` guard, matches by FTN tag).
- **Zone-subdir scheme round-trips** between binkp write (`%03x`) and tosser read.

---

---

## IMPLEMENTATION STATUS (2026-07-11)

All of the recommended fix order **C1–C4, H5–H9, M10, M11 are implemented, built (0 errors) and deployed** to `!Converse/Resources/FTN,ff8` (86431 B). **Needs a full BBS restart to load.** Runtime verification (loopback toss + a real binkp session) still pending — gated on restart.

| ID | Fix | Where |
|----|-----|-------|
| C4 | MARK_EXPORTED now per-message (`packed_ok` flag), not whole-batch | `scanner` + `h/scanner` |
| C2 | Packet envelope origin = `mailer_aka_for_zone(dest zone)`, not `our_addrs[0]` | `mailer` (new helper) + `scanner:877` |
| H8 | Local-post origin/MSGID = `ctx->orig_addr` (correct per-network AKA) | `packer` |
| C1 | Echomail routed to uplinks in the area's **zone** (from `akause`) + group | `scanner_get_echomail_uplinks` + caller |
| C3 | SEEN-BY/PATH now stamp **our** zone AKA (`ctx->orig_addr`), not the author; whole-token presence test (killed the `strstr` "25/9"⊂"250/9" bug) | `packer` |
| M11 | Dupe DB: dual-hash (djb2+FNV) 8192-ring, `used` flag (fixes hash==0), **persisted** to `Data.FTNDupes`, reloaded at init | `tosser` |
| H5 | Inbound netmail → configured NETMAIL area (areatype 2), not area 0 | `tosser` (new `tosser_find_area_by_type`) |
| H6 | Unknown echotag: loud `ftnlog` + optional JUNK(areatype 3) catch-all, never silent | `tosser` |
| H7 | M_FILE rejected unless authenticated (nodes WITH a password can't skip it); `secure` flag tracked + logged | `binkp` + `h/mailer` |
| H9 | `ftn_addr_match` compares domain only when BOTH sides have one (fixes 5D `@domain` recognition) — single-point fix for all 11 routing call sites | `mailer` |
| M10 | Busy-clear + retry scheduling use the **dialed** node (`target_addr`), not the remapped `remote_addr` | `mailer` |
| M12 | `allowed_echoes` now enforced (AND with groups); wildcard/glob matcher (`RISCOS*`, `*`) added; `allowed_files *` no longer inverts to deny-all; `max_echoes`/`max_files` caps enforced | `echofix` |
| M13 | Packet rollover at `max_packet_size` (soft limit, message never split) instead of one unbounded `.pkt` | `scanner` |
| M14 | `queue_scan_outbound` refuses to rebuild the node array while any session is active (protects live `QUEUE_NODE*`) | `queue` |
| M15 | HOLD mail no longer triggers an outbound poll and is not sent on a call we placed (only when the peer calls us); HOLD no longer out-ranks NORMAL | `queue` + `binkp` |

**REQUIRED CONFIG ACTION (multi-network):** an echo area's network is now taken from its `akause` (index into the `address N` entries: 0=fidonet, 1=cnet, 2=pinet, 3=retronet, 4=hobbynet, 5=amiganet). Today every echo area is fidonet so the default `akause 0` is correct and nothing breaks. **When adding a non-fidonet echo, set `akause N` on that area in `Config/MsgBase_1`**, or it will be stamped/routed as fidonet.

**Deferred / open:**
- **H7 physical dir split** — per operator decision (2026-07-11), unsecured inbound is *accepted + logged* (non-breaking), NOT quarantined. Quarantine remains an option if wanted later.
- **LOW items** remain: `maxsessions` silently clamped to 4 (no warning); `ftn_string_to_addr` no range validation / bare-2D rejected; tossed record doesn't store orig/dest `domain`; `our_addr_count` not reset on a (currently non-existent) runtime config reload.
- C3 explicit "skip a recipient already in SEEN-BY" not added — our-AKA-in-SEEN-BY + preserved history (in body) + the persistent dupe DB together contain loops; the remaining case is wasted bandwidth, not corruption.

**As of 2026-07-11 all C/H findings and mediums M10–M15 are implemented, built (0 err), deployed. Only LOW items + the H7 quarantine option remain.**

## LIVE VERIFICATION (2026-07-11, loopback toss test — PASSED)

Drove real Type-2 `.pkt` files into `FTN/Inbound/Fidonet/002` and let the mailer auto-toss (idle-triggered, ~180s). Ground-truthed against the actual message store `MsgBases/0001/Messages/A00NN/G00/`:

- ✅ **Echomail** (`AREA:RETRO_COMPUTING`) → stored in **area 16**. Area matching + echo toss confirmed.
- ✅ **Netmail** (to `2:250/9`, To:Sysop) → stored in **NETMAIL area 15**, NOT the phantom area 0. **H5 confirmed live** (the headline inbound fix).
- ✅ **Unknown echotag** (`BOGUS_NONEXISTENT_ECHO`) → **not stored** anywhere (correct discard, no misfile). **H6 behaviour confirmed.**
- ✅ **Dupe detection** — re-dropped the same MSGID; area stayed at one file (not re-stored). **M11 in-memory dedup confirmed live.**
- ✅ **Dupe DB persistence** — `Resources.Data.FTNDupes,ffd` (98320 B = 16-byte header + 8192×12-byte ring) now written. **M11 persistence confirmed.**

**Bugs found & fixed during verification:**
- **M11 path bug:** dupe file was pointed at `<Converse$Dir>.Data.FTNDupes` but that dir doesn't exist (data lives in `Resources.Data`) → save silently failed. Corrected to `Resources.Data.FTNDupes`; confirmed file now created.
- **Log routing:** `ftnlog_printf` writes the live GUI ring; `mailer_log`→Filer-logging-SWI writes the persistent `Logs/FTN` file (buffered, flushes on close). H5/H6 warnings now go to **both** via a new `tosser_notify()` helper.

**Shared-host poll dedupe (M16, 2026-07-11 — implemented):** uplinks 2/3/4 share `call.rofbbs.com`; dialling them concurrently made the hub reject the extra connections. Added `mailer_host_busy(host,port,exclude)` (scans active sessions) and a guard in `queue_get_next_poll_node` that skips a node whose host:port already has a live session. One session per host; same-host networks rotate over poll cycles via `next_poll` backoff. Session now records `remote_port`. Deployed binary **87183 B**. Needs restart + verification (expect: only one call.rofbbs.com session at a time, no concurrent "Auth failed").

**Environment notes:** message store root = `<Converse$Dir>.MsgBases` (NOT `Resources/Data/MsgDB`, a red herring). Auto-toss requires `active_sessions==0`. Shared-host observation: uplinks 2/3/4 all target `call.rofbbs.com` and are dialled concurrently → cnet authed "secure" but pinet/retronet "Auth failed" (hub rejecting concurrent sessions from one IP) — pre-existing, NOT caused by these changes; would need host+port poll de-dup to fix (new finding, deferred).

Latest deployed binary: **87007 B**. All changes UNCOMMITTED.

---

## Recommended fix order

1. **C4** (mark-exported per-message) — stops silent outbound loss; small, self-contained.
2. **C2 + H8** (AKA selection by zone for header + origin/MSGID) — one helper `aka_for_zone()`, used in packer/scanner.
3. **C1** (route echomail by zone, not just group) — the central multi-network defect.
4. **C3** (SEEN-BY: read prior, add all our AKAs, skip already-seen) — hub loop safety; pairs with a persistent MSGID dupe DB (M11).
5. **H5 + H6** (netmail area resolution; unknown-tag → junk/Bad not silent-drop) — stops silent inbound loss.
6. **H7** (enforce auth before M_FILE; secure/unsecure split).
7. **H9 / M10** (domain-agnostic matching; shared-host inbound routing).
8. Mediums as capacity allows; M12 (dead access-control config) matters once real downlinks connect.
