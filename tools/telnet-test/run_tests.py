#!/usr/bin/env python3
"""
run_tests.py -- drive the Converse BBS over telnet and exercise file transfers.

Usage:
  ./run_tests.py login
  ./run_tests.py download --file-id 1                 # BBS sends via ZMODEM -> rz
  ./run_tests.py upload   --proto z|y|g|x|1 [--file PAYLOAD]

Global options:
  --host 127.0.0.1  --port 2222  --user andy  --pass Hello
  --raw             don't telnet-escape the transfer stream (IAC handling off)
  --verbose

The menu path (from the deployed BBS scripts):
  login -> Postlogon (Bulletins/LastCall/loginscan, each an `anykey`) -> MainMenu
  MainMenu 'F' -> Filebase
  Filebase 'D' -> "File ID to download:" -> id -> `sendfile <id> zmodem`  (download)
  Filebase 'U' -> receivefile: "Filename:" -> "Description:" -> protocol picker (upload)
"""

import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from bbsclient import TelnetBBS, transfer_bridge, log  # noqa: E402


def do_login(bbs, user, password):
    # Connection gate: server asks to "press * (SHIFT+8) twice" to enter.
    pre = bbs.drain(idle=0.8, overall=6.0)
    if "*" in pre and "twice" in pre.lower():
        log("sending ** to enter the system")
        bbs.send("**")
    # Pre-logon detectansi (ESC[6n) is auto-answered inside the client.
    bbs.expect(r"Username:", timeout=20)
    bbs.send_line(user)
    bbs.expect(r"Password:", timeout=10)
    bbs.send_line(password)
    out = bbs.expect(r"Login successful|Username not found|Incorrect password|Login failed",
                     timeout=15)
    if "successful" not in out.lower():
        raise SystemExit("LOGIN FAILED: %s" % out.strip())
    log("login OK as %s" % user)
    # Walk past Bulletins / LastCallers / loginscan anykey pauses to the Main
    # Menu. Nudge with ENTER (advance_to default) -- space desyncs menu prompts.
    if not bbs.advance_to("Hall of Fame", tries=12):
        raise SystemExit("never reached Main Menu after login")
    log("at Main Menu")


def goto_filemenu(bbs):
    time.sleep(0.4)               # let the Main Menu char-prompt arm
    bbs.send("F")
    if not bbs.advance_to("Areas & Libs", tries=6):
        raise SystemExit("never reached File Libraries menu")
    log("at File Libraries")
    time.sleep(0.3)               # let the File menu char-prompt arm


def do_download(bbs, file_id, incoming, telnet_escape, timeout, dump_path=None):
    goto_filemenu(bbs)
    bbs.send("D")
    bbs.expect(r"File ID to download:", timeout=10)
    bbs.send_line(str(file_id))
    # Server prints "Sending file..." then begins ZMODEM (ZRQINIT: "rz\r" + "**\x18B00").
    # Hand the socket to `rz` which receives into `incoming`.
    time.sleep(0.3)
    before = set(os.listdir(incoming))
    rc = transfer_bridge(bbs.sock, ["rz", "-vv", "-E"], cwd=incoming,
                         telnet_escape=telnet_escape, timeout=timeout,
                         label="download/rz", dump_path=dump_path)
    after = set(os.listdir(incoming))
    new = sorted(after - before)
    if rc == 0 and new:
        for f in new:
            path = os.path.join(incoming, f)
            log("RECEIVED %s (%d bytes)" % (f, os.path.getsize(path)))
        print("DOWNLOAD OK:", ", ".join(new))
        return True
    print("DOWNLOAD FAILED (rc=%s, new files=%s)" % (rc, new))
    return False


PROTO_KEY = {"z": "z", "y": "y", "g": "g", "x": "x", "1": "1"}
PROTO_SZ = {
    "z": ["sz", "-vv"],                 # ZMODEM (default)
    "y": ["sz", "-vv", "--ymodem"],
    "g": ["sz", "-vv", "--ymodem"],    # YMODEM-G: sz has no -g; server drives streaming
    "x": ["sz", "-vv", "--xmodem"],
    "1": ["sz", "-vv", "--xmodem", "--1k"],
}


def select_area(bbs, area, filebase=1):
    """From the File menu, select a file area. 'A' first prompts for a filebase
    ("Enter filebase number to access:") then for an area ("Enter area number
    to access:"), then confirms with "Selected: <name>"."""
    bbs.send("A")
    r1 = bbs.expect(r"Enter filebase number|Enter area number", timeout=10)
    if "filebase number" in r1.lower():
        bbs.send_line(str(filebase))
        bbs.expect(r"Enter area number", timeout=10)
    bbs.send_line(str(area))
    out = bbs.expect(r"Selected|not found|Access denied|Invalid", timeout=10)
    if "selected" not in out.lower():
        raise SystemExit("area %s not selected: %s" % (area, out.strip()))
    log("selected area %s" % area)
    if not bbs.advance_to("Areas & Libs", tries=6):
        raise SystemExit("didn't return to File menu after area select")
    time.sleep(0.3)


def do_upload(bbs, proto, payload, telnet_escape, timeout, area=None):
    if proto not in PROTO_KEY:
        raise SystemExit("bad --proto %r (use z|y|g|x|1)" % proto)
    if not os.path.isfile(payload):
        raise SystemExit("payload not found: %s" % payload)
    fname = os.path.basename(payload)
    goto_filemenu(bbs)
    if area is not None:
        select_area(bbs, area)
    bbs.send("U")
    # After 'U' the server either prompts for a filename or (if no area is
    # selected) refuses with a "select a file area" message.
    resp = bbs.expect(r"Filename:|select a file area", timeout=10)
    if "select a file area" in resp.lower():
        print("UPLOAD REFUSED (no area selected) -- guard working as intended")
        return "refused"
    bbs.send_line(fname)
    bbs.expect(r"Description:", timeout=10)
    bbs.send_line("telnet-test upload %s" % proto)
    # Protocol picker screen, then a single hot-key.
    bbs.drain(idle=0.5, overall=4.0)
    bbs.send(PROTO_KEY[proto])
    time.sleep(0.4)
    argv = PROTO_SZ[proto] + [payload]
    rc = transfer_bridge(bbs.sock, argv, cwd=os.path.dirname(payload),
                         telnet_escape=telnet_escape, timeout=timeout,
                         label="upload/sz-%s" % proto)
    # After a receive the server prints "Upload complete!" with a file id.
    bbs.sock.setblocking(False)
    try:
        tail = bbs.drain(idle=0.8, overall=6.0)
    except Exception:
        tail = ""
    ok = rc == 0 or "upload complete" in tail.lower()
    print("UPLOAD %s (rc=%s)" % ("OK" if ok else "FAILED", rc))
    if tail.strip():
        log("post-upload server text:\n%s" % tail.strip()[-500:])
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["login", "download", "upload"])
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=2222)
    ap.add_argument("--user", default="andy")
    ap.add_argument("--pass", dest="password", default="Hello")
    ap.add_argument("--file-id", type=int, default=1)
    ap.add_argument("--proto", default="z", help="upload protocol: z|y|g|x|1")
    ap.add_argument("--area", type=int, default=None, help="select this file area before uploading")
    ap.add_argument("--file", default=os.path.join(HERE, "payloads", "upload_test.bin"))
    ap.add_argument("--incoming", default=os.path.join(HERE, "incoming"))
    ap.add_argument("--raw", action="store_true", help="disable telnet IAC escaping on transfer")
    ap.add_argument("--dump", default=None, help="log raw transfer bytes both directions to this file")
    ap.add_argument("--timeout", type=int, default=120, help="transfer timeout seconds")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    telnet_escape = not args.raw
    os.makedirs(args.incoming, exist_ok=True)

    bbs = TelnetBBS(args.host, args.port, verbose=True)
    try:
        bbs.connect()
    except OSError as e:
        raise SystemExit("CONNECT FAILED to %s:%d -- is the BBS telnet server up? (%s)"
                         % (args.host, args.port, e))

    ok = True
    try:
        do_login(bbs, args.user, args.password)
        if args.action == "login":
            print("LOGIN OK")
        elif args.action == "download":
            ok = do_download(bbs, args.file_id, args.incoming, telnet_escape,
                             args.timeout, dump_path=args.dump)
        elif args.action == "upload":
            ok = do_upload(bbs, args.proto, args.file, telnet_escape, args.timeout,
                           area=args.area)
    finally:
        bbs.close()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
