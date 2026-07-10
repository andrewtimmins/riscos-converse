"""
bbsclient.py -- minimal scriptable telnet client for driving the Converse BBS
(LineTask) over 127.0.0.1:2222, with an X/Y/ZMODEM bridge to lrzsz (sz/rz).

Why this exists:
  The BBS runs inside RPCEmu and speaks telnet on port 2222. To test file
  transfers we log in as a normal user, walk the ANSI menus by matching text,
  and at the moment a transfer starts we hand the raw socket to `rz` (to
  receive a download) or `sz` (to send an upload). lrzsz does the actual
  X/Y/ZMODEM protocol; we just shuttle bytes and handle telnet IAC escaping.

Design notes:
  * Single-threaded during the menu phase (simple expect()/send()).
  * During a transfer we run the lrzsz child on pipes and pump bytes with two
    threads: socket->child and child->socket, applying telnet IAC handling.
  * detectansi (server sends ESC[6n) is auto-answered with a cursor report so
    the ANSI login path is taken.
"""

import os
import re
import select
import socket
import subprocess
import sys
import threading
import time

# ---- Telnet protocol bytes -------------------------------------------------
IAC  = 255
DONT = 254
DO   = 253
WONT = 252
WILL = 251
SB   = 250
SE   = 240
OPT_BINARY = 0
OPT_ECHO   = 1
OPT_SGA    = 3


def log(msg):
    sys.stderr.write("[bbs] %s\n" % msg)
    sys.stderr.flush()


class TelnetBBS:
    def __init__(self, host="127.0.0.1", port=2222, verbose=True):
        self.host = host
        self.port = port
        self.verbose = verbose
        self.sock = None
        self.buf = b""            # decoded application bytes seen so far (menu phase)
        self._raw_tail = b""      # partial IAC sequence carried across reads
        self.transcript = bytearray()

    # -- connection ----------------------------------------------------------
    def connect(self, timeout=10):
        self.sock = socket.create_connection((self.host, self.port), timeout=timeout)
        self.sock.setblocking(False)
        log("connected to %s:%d" % (self.host, self.port))

    def close(self):
        try:
            if self.sock:
                self.sock.close()
        except OSError:
            pass

    # -- low-level telnet-aware receive --------------------------------------
    def _negotiate(self, cmd, opt):
        """Respond to a single IAC <cmd> <opt>. Agree to BINARY+SGA, refuse rest."""
        if cmd in (DO, DONT):
            if opt in (OPT_BINARY, OPT_SGA):
                resp = WILL if cmd == DO else WONT
            else:
                resp = WONT
            self.sock.sendall(bytes([IAC, resp, opt]))
        elif cmd in (WILL, WONT):
            if opt in (OPT_BINARY, OPT_SGA, OPT_ECHO):
                resp = DO if cmd == WILL else DONT
            else:
                resp = DONT
            self.sock.sendall(bytes([IAC, resp, opt]))

    def _feed(self, data):
        """Strip telnet IAC sequences from `data`, auto-negotiate, answer ESC[6n.
        Returns the application-level bytes."""
        data = self._raw_tail + data
        self._raw_tail = b""
        out = bytearray()
        i = 0
        n = len(data)
        while i < n:
            b = data[i]
            if b == IAC:
                if i + 1 >= n:
                    self._raw_tail = data[i:]
                    break
                c = data[i + 1]
                if c == IAC:            # escaped 0xFF literal
                    out.append(IAC)
                    i += 2
                    continue
                if c in (DO, DONT, WILL, WONT):
                    if i + 2 >= n:
                        self._raw_tail = data[i:]
                        break
                    self._negotiate(c, data[i + 2])
                    i += 3
                    continue
                if c == SB:             # subnegotiation: skip to IAC SE
                    j = data.find(bytes([IAC, SE]), i + 2)
                    if j == -1:
                        self._raw_tail = data[i:]
                        break
                    i = j + 2
                    continue
                i += 2                  # other 2-byte command, ignore
                continue
            out.append(b)
            i += 1
        app = bytes(out)
        # Auto-answer DSR cursor-position query (detectansi's ESC[6n)
        if b"\033[6n" in app:
            self.sock.sendall(b"\033[24;80R")
            if self.verbose:
                log("answered ESC[6n -> ESC[24;80R (ANSI on)")
        return app

    def _recv_once(self, timeout):
        r, _, _ = select.select([self.sock], [], [], timeout)
        if not r:
            return b""
        try:
            data = self.sock.recv(4096)
        except (BlockingIOError, InterruptedError):
            return b""
        if data == b"":
            raise EOFError("server closed connection")
        self.transcript.extend(data)
        return self._feed(data)

    # -- expect / send -------------------------------------------------------
    def expect(self, pattern, timeout=15.0):
        """Read until `pattern` (str, matched as regex on latin-1) appears.
        Returns the accumulated text since the last expect."""
        rx = re.compile(pattern.encode("latin-1"), re.I | re.S)
        deadline = time.time() + timeout
        start = len(self.buf)
        while True:
            m = rx.search(self.buf, start)
            if m:
                seen = self.buf[start:m.end()]
                # keep only unconsumed tail for the next expect
                self.buf = self.buf[m.end():]
                return seen.decode("latin-1", "replace")
            if time.time() >= deadline:
                tail = self.buf[start:][-400:].decode("latin-1", "replace")
                raise TimeoutError(
                    "timeout waiting for %r; last output:\n%s" % (pattern, tail))
            chunk = self._recv_once(min(0.5, deadline - time.time()))
            self.buf += chunk

    def drain(self, idle=0.6, overall=8.0):
        """Read until the stream is quiet for `idle` seconds (or `overall` cap)."""
        deadline = time.time() + overall
        last = time.time()
        while time.time() < deadline:
            chunk = self._recv_once(0.2)
            if chunk:
                self.buf += chunk
                last = time.time()
            elif time.time() - last >= idle:
                break
        got = self.buf
        self.buf = b""
        return got.decode("latin-1", "replace")

    def send(self, data):
        if isinstance(data, str):
            data = data.encode("latin-1")
        self.sock.sendall(data)

    def send_line(self, text):
        self.send(text + "\r")

    def advance_to(self, anchor, key="\r", tries=8, idle=0.7):
        """Press `key` whenever the stream goes idle until `anchor` text appears.
        Used to get past chained `anykey` pauses to a known screen. Nudge with
        ENTER (\\r), NOT space: menus treat ENTER as an invalid key and just
        redraw, whereas space is a real keypress that desyncs the prompt."""
        rx = re.compile(re.escape(anchor).encode("latin-1"), re.I)
        for _ in range(tries):
            if rx.search(self.buf):
                self.buf = b""
                return True
            text = self.drain(idle=idle, overall=idle + 1.5)
            if rx.search(text.encode("latin-1")):
                return True
            self.send(key)   # nudge past an anykey pause
        # final check
        text = self.drain(idle=idle, overall=2.0)
        return bool(rx.search(text.encode("latin-1")))


# ---- ZMODEM / X / Y MODEM bridge to lrzsz ---------------------------------

def _pump(src_read, dst_write, transform, stop, name):
    """Copy src->dst applying `transform`, until stop is set or EOF."""
    try:
        while not stop.is_set():
            data = src_read()
            if data is None:        # timeout tick
                continue
            if data == b"":         # EOF
                break
            out = transform(data)
            if out:
                dst_write(out)
    except (OSError, ValueError):
        pass
    finally:
        stop.set()


class _IacDecoder:
    """Collapse IAC IAC -> FF and drop IAC command sequences from server->client."""
    def __init__(self):
        self.tail = b""

    def __call__(self, data):
        data = self.tail + data
        self.tail = b""
        out = bytearray()
        i, n = 0, len(data)
        while i < n:
            b = data[i]
            if b == IAC:
                if i + 1 >= n:
                    self.tail = data[i:]
                    break
                c = data[i + 1]
                if c == IAC:
                    out.append(IAC); i += 2; continue
                if c in (DO, DONT, WILL, WONT):
                    if i + 2 >= n:
                        self.tail = data[i:]; break
                    i += 3; continue
                if c == SB:
                    j = data.find(bytes([IAC, SE]), i + 2)
                    if j == -1:
                        self.tail = data[i:]; break
                    i = j + 2; continue
                i += 2; continue
            out.append(b); i += 1
        return bytes(out)


def _iac_encode(data):
    """Double any 0xFF for client->server (telnet requires IAC IAC)."""
    return data.replace(b"\xff", b"\xff\xff")


def _identity(data):
    return data


def _hexdump_frame(tag, data, fh):
    """Log a compact view of a byte run: hex + printable, ZMODEM frame hints."""
    hints = []
    if b"\x2a\x2a\x18B" in data or data.startswith(b"**\x18B"):
        hints.append("ZMODEM-hexhdr")
    if b"\x18B" in data:
        # decode frame type from ZMODEM binary/hex header if present
        idx = data.find(b"\x18B")
        if idx + 4 <= len(data):
            hints.append("frame=0x" + data[idx+2:idx+4].decode("latin-1", "replace"))
    if b"\x18\x18\x18" in data:
        hints.append("CAN")
    printable = "".join(chr(c) if 32 <= c < 127 else "." for c in data[:48])
    fh.write("%s %3dB %-22s %s | %s\n" % (
        tag, len(data), " ".join(hints), data[:24].hex(), printable))
    fh.flush()


def transfer_bridge(sock, argv, cwd, telnet_escape=True, timeout=120, label="",
                    dump_path=None):
    """Run lrzsz child (`argv`) with its stdin/stdout bridged to `sock`.
    telnet_escape=True applies IAC handling; False passes bytes raw.
    dump_path: if set, log every byte run in both directions there.
    Returns the child's exit code."""
    log("%s: launching %s (telnet_escape=%s)" % (label, " ".join(argv), telnet_escape))
    dump_fh = open(dump_path, "w") if dump_path else None
    child = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    sock.setblocking(True)
    sock.settimeout(1.0)
    stop = threading.Event()

    dec = _IacDecoder() if telnet_escape else None
    enc = _iac_encode if telnet_escape else _identity

    def sock_read():
        try:
            d = sock.recv(4096)
            return d
        except socket.timeout:
            return None

    def child_read():
        return child.stdout.read1(4096) if hasattr(child.stdout, "read1") \
            else child.stdout.read(4096)

    def to_child(d):
        if dump_fh:
            _hexdump_frame("S->C", d, dump_fh)   # server -> client (into rz)
        child.stdin.write(d)
        child.stdin.flush()

    def to_sock(d):
        if dump_fh:
            _hexdump_frame("C->S", d, dump_fh)   # client -> server (out of rz/sz)
        sock.sendall(d)

    t1 = threading.Thread(target=_pump,
                          args=(sock_read, to_child,
                                (dec if telnet_escape else _identity), stop, "sock->child"))
    t2 = threading.Thread(target=_pump,
                          args=(child_read, to_sock, enc, stop, "child->sock"))
    t1.daemon = t2.daemon = True
    t1.start(); t2.start()

    try:
        rc = child.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        log("%s: TIMEOUT after %ss, killing child" % (label, timeout))
        child.kill()
        rc = -1
    stop.set()
    if rc != 0:
        # Abort cleanly so the server's sz/rz gives up and the BBS line returns
        # to the menu instead of staying wedged mid-transfer. ZMODEM cancel =
        # 8x CAN (0x18) then 8x backspace. Sent raw (no IAC escaping needed:
        # 0x18 != 0xFF).
        try:
            sock.sendall(b"\x18" * 8 + b"\x08" * 8)
            log("%s: sent ZMODEM cancel (CANx8) to unwedge server line" % label)
        except OSError:
            pass
    try:
        child.stdin.close()
    except OSError:
        pass
    time.sleep(0.2)
    err = b""
    try:
        err = child.stderr.read() or b""
    except OSError:
        pass
    if err:
        log("%s: lrzsz stderr:\n%s" % (label, err.decode("latin-1", "replace").strip()))
    log("%s: child exit code %s" % (label, rc))
    sock.setblocking(False)
    return rc
