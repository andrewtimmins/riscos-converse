#!/usr/bin/env python3
"""Rich submenu screens (Messages / Files / Doors) in the same house style as
the main menu: persistent TOASTER masthead + live-status row + colourful hotkey
chips grouped under cyan section tabs + shaded gradient rules. The calling BBS
scripts overlay the live status strip (Header), a section context line, and the
command prompt. Palette (VGA): 3 amber, 11 bright yellow, 6 cyan, 14 bright
cyan, 15 white, 10 green, 1 red."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from gen import *
from menu2 import masthead, key, tab, ggrad

C1, C2, C3 = 5, 31, 56          # the three chip columns (match the main menu)

def footer(s):
    ggrad(s, 21, 4, COLS-4, 3)
    # row 22 = section context (overlaid) ; row 23 = command prompt (overlaid)

def build(subtitle, groups):
    """groups: list of (col, tab_title, [(key,label), ...])."""
    s=Screen()
    masthead(s, subtitle, 11)          # bright-yellow section subtitle
    for col, title, items in groups:
        tab(s, col, 11, title)
        for i,(k,label) in enumerate(items):
            key(s, col, 12+i, k, label)
    footer(s)
    return s

def emit(name, s):
    out=os.path.join(os.path.dirname(__file__), name)
    emit_ans(s, out, rows=ROWS)

# ---- Messages ----
msg = build("M E S S A G E   B A S E S", [
    (C1, "READ & BROWSE", [("R","Read messages"),
                           ("A","Change area"),
                           ("S","Scan new posts"),
                           ("I","Your inbox")]),
    (C2, "COMPOSE",       [("P","Post public"),
                           ("E","Private email"),
                           ("N","Netmail"),
                           ("F","Feedback")]),
    (C3, "SESSION",       [("Q","Back to main")]),
])
emit("msgmenu2.ans", msg)

# ---- Files ----
fil = build("F I L E   L I B R A R I E S", [
    (C1, "BROWSE",   [("L","List files"),
                      ("A","Change area"),
                      ("S","Scan new files"),
                      ("V","View file info")]),
    (C2, "TRANSFER", [("D","Download a file"),
                      ("U","Upload a file")]),
    (C3, "SESSION",  [("Q","Back to main")]),
])
emit("filemenu2.ans", fil)

# ---- Doors & Games ----
door = build("D O O R S   &   G A M E S", [
    (C1, "ARCADE",         [("1","Tetris"),
                            ("2","Snake"),
                            ("3","Breakout")]),
    (C2, "PUZZLES & QUIZ", [("4","Boxed In"),
                            ("5","Trivia"),
                            ("6","Purity Test")]),
    (C3, "MORE",           [("7","The Wall"),
                            ("Q","Back to main")]),
])
# static flavour hint on the context row for doors (no live base/area here)
door.center(22, "pick a number to play  -  [Q] returns to the main menu", 6, 0)
emit("doorsmenu2.ans", door)
