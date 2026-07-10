# Converse BBS telnet transfer test harness

Drives the running BBS (LineTask) over telnet on `127.0.0.1:2222`, logs in as a
normal user, walks the ANSI menus, and exercises X/Y/ZMODEM up- and downloads by
bridging the socket to `lrzsz` (`sz`/`rz`).

## Prereqs
- RPCEmu running with the Converse BBS **telnet server listening on 2222**
  (check: `ss -ltn | grep 2222`). Start it inside the guest first.
- Host tools: `python3`, `sz`/`rz` (`apt install lrzsz`).

## Usage
```sh
cd tools/telnet-test
./run_tests.py login                      # verify login as andy/Hello -> Main Menu
./run_tests.py download --file-id 1       # BBS sends via ZMODEM; rz saves to ./incoming/
./run_tests.py upload   --proto z         # send payloads/upload_test.bin via ZMODEM
./run_tests.py upload   --proto y         # YMODEM
./run_tests.py upload   --proto x         # XMODEM-CRC
./run_tests.py upload   --proto 1         # XMODEM-1K
./run_tests.py upload   --proto g         # YMODEM-G (streaming)
```
Creds default to `andy` / `Hello`; override with `--user/--pass`.

## Menu path (from the deployed BBS scripts)
- `Prelogon` runs `detectansi` (server sends `ESC[6n`; the client auto-answers
  `ESC[24;80R`), shows `Login`, then `logon` prompts `Username:` / `Password:`.
- `Postlogon`: Bulletins -> LastCallers -> loginscan, each an `anykey` pause
  (no prompt text) -> `MainMenu`. The client advances past these on idle.
- `MainMenu` hot-key `F` -> `Filebase`.
- Download: Filebase `D` -> `File ID to download:` -> id -> `sendfile <id> zmodem`
  (**menu path is ZMODEM only** for download).
- Upload: Filebase `U` -> `Filename:` -> `Description:` -> protocol picker
  (`Z`=ZMODEM `Y`=YMODEM `G`=YMODEM-G `X`=XMODEM-CRC `1`=XMODEM-1K).

## Telnet IAC escaping (important)
lrzsz is not telnet-aware. By default the bridge doubles outbound `0xFF`
(IAC IAC) and collapses inbound `0xFF 0xFF`, and drops IAC command sequences.
If the BBS telnet server does **not** do IAC processing on the data stream,
that escaping corrupts binary data — pass `--raw` to bridge bytes untouched.
The `payloads/upload_test.bin` fixture deliberately contains `0xFF` bytes so
this shows up. If a transfer fails with escaping on, retry with `--raw`.

## Files
- `bbsclient.py` — telnet-aware client (IAC negotiation, ESC[6n answer,
  expect/drain/advance helpers) + `transfer_bridge()` to lrzsz.
- `run_tests.py` — login + download/upload driver (this CLI).
- `payloads/` — upload fixtures. `incoming/` — downloaded files land here.
