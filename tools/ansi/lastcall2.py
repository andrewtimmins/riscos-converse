#!/usr/bin/env python3
"""Last Callers backdrop in the house style: persistent TOASTER masthead +
'LAST CALLERS' subtitle + a recent-callers line + column headers and a rule.
The LastCallers BBS script overlays the caller table into rows 13..22 (see the
column geometry below - keep the two in sync)."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from gen import *
from menu2 import masthead

# Column geometry - MUST match the LastCallers script overlay:
#   overlay starts at 1-indexed col 6 (grid 5); uname pad 16, realname pad 26.
COL_USER = 5          # grid col of the User column
COL_NAME = COL_USER + 16   # 21
COL_WHEN = COL_NAME + 26   # 47

s = Screen()
masthead(s, "L A S T   C A L L E R S", 11)
s.center(9, "~ Recent callers to The Yellow Toaster ~", 3, 0)

# column headers (row 11) + a cyan rule under them (row 12)
s.put(COL_USER, 11, "User", 11, 0)
s.put(COL_NAME, 11, "Real Name", 11, 0)
s.put(COL_WHEN, 11, "When", 11, 0)
for x in range(5, COLS-5): s.putc(x, 12, S_H, 6, 0)
# table body = rows 13..22 (overlaid live by the script)

out = os.path.join(os.path.dirname(__file__), "lastcall2.ans")
emit_ans(s, out, rows=ROWS)
