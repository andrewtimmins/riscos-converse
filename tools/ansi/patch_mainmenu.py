#!/usr/bin/env python3
# Post-process the generated MainMenu screen to inject LIVE header data that the
# ANSI cell-grid generator can't express (variable-width macros). Run AFTER
# screens2.py regenerates mainmenu.ans, then copy to !Converse/BBS/Screens/MainMenu.
# Idempotent: rebuilds header rows 3 & 5 from constants. Fields are fixed-width
# (pad(left(..,W),W)) so the box borders stay at 77 interior cols.
import re, sys

P = sys.argv[1] if len(sys.argv) > 1 else "/projects/riscos-converse/!Converse/BBS/Screens/MainMenu"
data = open(P, "rb").read()
sep = b"\r\n" if b"\r\n" in data else b"\n"
rows = data.split(sep)

PREFIX = b"\x1b[0m\x1b[0;36;40m\xba"   # left border
SUFFIX = b"\x1b[36m\xba\x1b[0m"        # right border

# live macros (fixed width via pad(left(..,W),W)); content is left-aligned to
# col 4 (3-space margin) and reaches the col-74 right edge to match the columns.
NAME  = b'%{ =pad(left(userget("realname"),16),16) }'
LVL   = b'%{ =pad(left(userget("level"),4),4) }'
CALLS = b'%{ =pad(left(userget("calls"),6),6) }'
TIME  = b'%{ =pad(left(userget("todaytime"),4),4) }'

# ---- Row 3: welcome + name ............... [?] Help chip ----
content3 = (b"\x1b[0m   "
            + b"\x1b[1;36m" + bytes([0xAF])              # bright-cyan >>
            + b"  \x1b[1;37mWelcome back, "
            + b"\x1b[1;33m" + NAME + b"\x1b[0m"            # bright-yellow name
            + b" "*28
            + b"\x1b[0;30;46m [?] Help \x1b[0m"            # black-on-cyan chip
            + b"   ")

# ---- Row 5: stat strip framed by amber shade accents, block separators ----
SEP = b"\x1b[0;33m" + bytes([0xDB])                       # amber block separator
content5 = (b"\x1b[0m   "
            + b"\x1b[0;33m" + bytes([0xB2,0xB1,0xB0]) + b" "   # left accent
            + b"\x1b[0;36mAccess " + b"\x1b[1;32m" + LVL
            + b" " + SEP + b" "
            + b"\x1b[0;36mCalls " + b"\x1b[1;33m" + CALLS
            + b" " + SEP + b" "
            + b"\x1b[0;36mTime today " + b"\x1b[1;33m" + TIME
            + b" "*20
            + b"\x1b[0;33m" + bytes([0xB0,0xB1,0xB2]) + b"\x1b[0m"   # right accent
            + b"   ")

def vis_width(content):
    s = re.sub(rb'\x1b\[[0-9;]*m', b'', content)
    s = re.sub(rb'%\{ =pad\(left\([^,]+,(\d+)\),\d+\) \}', lambda m: b' '*int(m.group(1)), s)
    return len(s)

for label, c in (("row3",content3),("row5",content5)):
    w = vis_width(c)
    print("%s visible width = %d %s" % (label, w, "OK" if w==77 else "*** NOT 77 ***"))
    if w != 77: sys.exit(1)

rows[3] = PREFIX + content3 + SUFFIX
rows[5] = PREFIX + content5 + SUFFIX

# safety: drop a bottom blue status bar if the generator ever emits one
if rows and b"\x1b[1;37;44m" in rows[-1]:
    rows = rows[:-1]
    print("removed blue status bar")

open(P, "wb").write(sep.join(rows))
print("patched", P, "->", len(rows), "rows")
