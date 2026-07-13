#!/usr/bin/env python3
"""Bulletins / News screen in the house style: persistent TOASTER masthead +
'BULLETINS & NEWS' subtitle + a sysop line + dated news items + a shaded rule.
Shown at login (Postlogon) and from the main menu; advanced with any key, so a
subtle 'Press any key to continue' sits at the foot (NO 'press ENTER for the
main menu' - it isn't the main menu next in the login flow)."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from gen import *
from menu2 import masthead, ggrad

MARK = 0xAF   # >>

NEWS = [
 ("10 Jul", "New Acorn file library online",   "247 fresh uploads - demos, PD games and RISC OS utilities."),
 ("08 Jul", "RetroNet now carrying 6 echoes",  "Chat, Coding, Hardware, Games, Emulation and Off-Topic."),
 ("02 Jul", "Door tournament this weekend",    "Top Tetris & Snake scores win extra download credit."),
 ("28 Jun", "Be kind on The Wall",             "One-liners are public and logged. Keep it friendly, folks."),
]

s = Screen()
masthead(s, "B U L L E T I N S   &   N E W S", 11)
s.center(9, "~ From the desk of the Sysop ~", 3, 0)     # fills the status row

y = 11
for date, title, desc in NEWS:
    s.putc(5, y, MARK, 14, 0)
    s.put(7, y, date, 11, 0)
    s.put(15, y, title, 15, 0)
    s.put(9, y+1, desc, 7, 0)
    y += 3

# No in-frame prompt: the `anykey` command shows the system blue "Press any
# key..." bar on the bottom row (Resources/System/Anykey), so a baked one would
# just double up.

out = os.path.join(os.path.dirname(__file__), "bulletins2.ans")
emit_ans(s, out, rows=ROWS)
