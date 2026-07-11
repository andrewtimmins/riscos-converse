# LineTask Scripting Engine — Deep-Dive Audit

**Date:** 2026-07-11
**Scope:** `Source/LineTask/c/script` (8963 lines), `Source/LineTask/h/script`, `Source/LineTask/c/main`, `Docs/Scripting` (1245 lines).
**Method:** 5 parallel deep-read auditors (memory, control-flow, doc-vs-code, crash-surface, completeness); every load-bearing finding re-read and confirmed by hand at the cited `file:line`.

---

## Bottom line

The instinct that the engine might be fragile and over-claimed is **half right**. On the axes you worried about — crashes, memory leaks, instability — the engine is **markedly more solid than expected**: it is memory-safe, crash-defensive, and structurally sound against taking down the board. The real story is elsewhere:

1. **One genuine robustness hole** — a runaway loop can livelock a single line forever (the board survives).
2. **The docs lie in the details** — command *coverage* is honest, but ~6 specifics are wrong and ~26 useful features are undocumented.
3. **It's a capable *macro* language, not yet a *scripting* language** — no expressions, almost no string ops, no arrays, no real functions, no data-returning BBS API. This is the "make it top-notch" gap.

Concurrency model (verified, `c/main:123 static line_task_state task_state`): **one LineTask process per line**, each with its own `script_state`. So there is no cross-session shared state — the scariest hypothesis (global loop state clobbered between callers) is **refuted**.

---

## A. Safety & robustness — mostly good (verified)

- **Memory:** no confirmed leak / double-free / use-after-free / overflow. Per-session variable values and instruction/label/call-frame arrays are freed on disconnect and dispose; `SET` on an existing var frees the old value first; every growable array reallocs via a temp pointer with a NULL-check (no lost-pointer realloc); fixed buffers uniformly use `sizeof-1`+NUL; **0 `sprintf`, only 3 `strcpy`** (all safe). Macro expansion runs through a self-growing buffer, clamped into fixed caller buffers.
- **Crashes:** `DIV`/`MOD`/`RANDOM` explicitly zero-guard the divisor (`script:4656/4679`); `FOR` step forces 1 when 0; every `host.get_*()` callback is NULL-checked *and* its return re-checked before deref; the 49 `atoi` sites that face untrusted input range-validate; the ANSI parser is bounded. **No confirmed remote crash.**
- **Control flow:** `program_counter` is always bounded (`script:775`); call stack depth-8 is enforced on push and underflow-safe on pop; parked states (`WAIT_*`) resume correctly (PC incremented *before* dispatch, so no double-execute); a **1000-instruction/poll budget** (`script:782`) keeps the guest and other lines responsive even under a runaway.

### Real gaps (verified)

| # | Sev | Finding | file:line | Fix |
|---|-----|---------|-----------|-----|
| R1 | **Med** (per-line) | **Runaway loops livelock a session.** No loop-iteration/total-instruction cap or watchdog. `WHILE 1`, `:x GOTO x`, or a `FOR` whose body resets the counter keeps `status==RUNNING`, burns 1000 instr *every poll* forever, and ignores the caller's keystrokes (input only handled while `WAITING`). The board stays alive; that one line is a CPU-burning zombie until carrier drops. | `script:775-788` | Add a per-session instruction/iteration budget → force `SCRIPT_STATUS_ERROR` with a diagnostic. |
| R2 | Low | **Init-OOM NULL deref.** `input_capacity` is set before the `input_buffer` malloc and *not* zeroed on failure (unlike labels/vars at 168-176), so a later input byte writes through NULL. Init-time OOM only. | `script:178-183` | `if (input_buffer==NULL) input_capacity=0;` |
| R3 | Low | **`messagebase info <id>` unvalidated.** `atoi(arg)` with no `<=0` guard passed to the external messagebase module (the sibling `read` handler *does* guard). Reachable from caller input via a macro. | `script:5205` (cf. `5056`) | Add the `msg_id<=0` reject. |
| R4 | Low | **Reset-contract dependency.** Variable values and `more_pending_text` are reclaimed only by `script_reset_session`, not `script_stop`. Any disconnect path that reaches only `script_stop` bleeds one caller's variables + pending More? buffer into the next user on that line. | `script:292-371` | Assert/ensure `reset_session` on every disconnect route. |

---

## B. The docs lie (in the details)

Command **coverage** is honest — every command the doc lists is really implemented (it even under-claims: ~53 commands, ~55 macros). But the **specifics** are wrong in several places, and a large, useful feature set is hidden.

**Documented but not real:**
- `%{_input}` and `%{_key}` (doc's "Special Variables") are documented as auto-populated after `PROMPT`/`ANYKEY` — **never written by any code** (`script:996-1014`); always expand to empty. *(Biggest single lie.)*
- `%{date}` documented `YYYY-MM-DD`, actually emits **`DD/MM/YYYY`** (`script:6598`).
- Variable names "64 chars" / "hash table" — actually **32 chars, linear array** (`h/script:264`).
- Backtick `` \` `` escape documented, but the parser terminates at the first raw backtick so a backtick string can never contain one (`script:7581`).
- Block-`IF` "skip mode / labels in skipped blocks not registered" is **fictional** — `IF` compiles to a runtime `GOTO`; all lines parse, all labels always register.
- A **worked `SYSOPCHAT` example** in the doc can't parse (`PROMPT` takes `<var> <mode> <echo>`, not a prompt string).

**Implemented but undocumented (worth surfacing):** ~26 macros — `%{bbsname}`, `%{sysopname}`, `%{hostname}`, `%{contact}`, `%{version}`, `%{lastlogon}`, `%{lastscan}`, and the full user-stats/flags set (`%{usercalls}`, `%{todaytime}`, `%{uploadskb}`, `%{userdownloads}`, `%{usermaxtime}`, …); plus `SLEEP` (alias for PAUSE), `messagebase search`, `filebase browse`, `BOLD 0`, and the `26bit` door modifier.

→ **Action:** a documentation reconciliation pass — fix the ~6 wrong specifics, document the ~26 hidden macros/subcommands, and correct the non-parsing example.

---

## C. Completeness — a macro language, not (yet) a scripting language

**Honest ceiling today:** labelled flow + nested block `IF` + `FOR`/`WHILE`/`BREAK`/`CONTINUE`; **one-operation-per-statement** integer math (`ADD/SUB/MUL/DIV/MOD` — no expression grammar); conditions are a flat left-to-right clause list (no precedence, parens, or `NOT`); a flat, case-insensitive, session-scoped **string variable** namespace; subscripts (`SCRIPT file`) that **share the entire variable table and pass nothing** (no params/returns/locals); and rich but **opaque** BBS integration — scripts can *drive* the built-in message/file browsers, transfers, mail, logon, doors, and read ~50 `%{}` macros, but cannot pull records *into* variables or write anything *back*.

**Missing (the top-notch gap):**
- **Expressions** — the single biggest gap: no `set x = b*2 + (c-1)`; no compound conditions with precedence/parens/NOT.
- **Strings** — only `STRLEN` + the `contains` operator. No substr/concat/upper/lower/trim/find/replace/split/format. (BBS scripting is ~80% string work.)
- **Data structures** — no arrays or maps.
- **Functions** — subscripts only; no parameters, return values, or locals.
- **Error handling** — no `on-error`/`try`, no script-readable error state; a bad command aborts.
- **Data-returning BBS API** — cannot enumerate/read/write user or base records into variables; no persistent KV store; no event hooks (login/logout/newmsg/idle/timer); no node-to-node messaging / one-liners from script.

### Roadmap (prioritised)

**Tier 1 — table stakes**
1. **Real expression evaluator** shared by `SET`/`IF`/`WHILE` (precedence, parens, unary `NOT`/`-`, string vs numeric ops). *Effort L.* Collapses the 5 arithmetic commands + the flat clause parser into one coherent language — the defining step from macro to scripting language.
2. **String function library** (substr/left/right, concat, upper/lower, trim, find, replace, split, format). *Effort M.*
3. **Loop/instruction watchdog** + clearer missing-label diagnostics (fixes R1). *Effort S.*

**Tier 2 — makes it pleasant**
4. Real subroutines: named functions with params, returns, local scope. *Effort L.*
5. Arrays / associative maps (`arr[key]=val`, `foreach`). *Effort M.*
6. `include`/library files. *Effort S–M.*
7. Structured error handling (`on error goto`, readable `%{error}`). *Effort M.*

**Tier 3 — top-notch differentiators**
8. **Data-returning BBS API** — non-interactive variants that populate variables/arrays (enumerate bases/areas, fetch a record's fields, list/iterate users, **read and write user fields**, node messaging, one-liners). *Effort L.* This is what turns "reskin the built-in UIs" into "build your own," the bar set by Synchronet/Mystic/WWIV.
9. Persistent KV store (per-user + board-global). *Effort M.*
10. Event/hook registration + ergonomic menu dispatch (`switch`/keyed table). *Effort M.*
11. Dev tooling: `TRACE`/step mode, hot-reload, docs generator off the command table. *Effort S–M.*

**Three highest-leverage:** (1) expression evaluator, (2) string library, (3) data-returning API + real subroutines.

---

## Verdict in one line

Solid, defensive engine that will not leak or crash the board — but it over-documents a few specifics, hides many useful macros, has one runaway-loop hole per line, and plateaus as a *macro* language; the path to "top-notch" is expressions → strings → a data-returning API with real functions.
