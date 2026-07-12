#!/usr/bin/env python3
"""Boxed backdrops for the Converse content pages (Hall of Fame, The Wall,
Settings, Voting, Feedback, Tell, QWK). Same house style as the nav menus:
gen.py frame() (amber top rule + cyan double box + centred title tab), with the
page script `type`-ing the backdrop and pos-overlaying live values on top.

Each make_*() returns (Screen, layout). `layout` holds the overlay coordinates
(grid, 0-based) the matching BBS script pos-writes into; keeping them next to the
labels keeps the .ans and the script in sync. `pos` in the engine is 1-based, so
a grid cell (x,y) is written `pos x+1 y+1`.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from gen import Screen, frame, panelhead, emit_ans, ROWS, COLS, S_H

OUT = "/projects/riscos-converse/!Converse/BBS/Screens"

def _bullet(s, x, y, col=14):
    s.putc(x, y, 0xAF, col, 0)

# ---------------------------------------------------------------- Hall of Fame
def make_stats():
    s = Screen(); frame(s, "Hall of Fame"); L = {}
    s.put(6, 3, "The board at a glance", 6, 0)
    LX, LV = 6, 28
    RX, RV = 46, 66
    rows = [("Registered users","Online now","users","online"),
            ("Message bases","Messages","mbases","msgs"),
            ("File bases","Files online","fbases","files"),
            ("Calls to date","Free memory","calls","mem")]
    for i,(ll,rl,lk,rk) in enumerate(rows):
        y = 5+i
        _bullet(s, LX-2, y); s.put(LX, y, ll, 15, 0)
        _bullet(s, RX-2, y); s.put(RX, y, rl, 15, 0)
        L[lk]=(LV,y); L[rk]=(RV,y)
    panelhead(s, 10, "MEMBERS", "level / calls")
    L.update(mem_y0=11, mem_n=9, mem_mark=5, mem_user=7, mem_lvl=40, mem_calls=54)
    panelhead(s, 21, "")
    s.put(6, 23, "Press", 6, 0); _bullet(s, 12, 23, 11)
    s.put(14, 23, "ENTER", 15, 0); s.put(20, 23, "for the Main Menu", 6, 0)
    return s, L

# -------------------------------------------------------------------- The Wall
def make_wall():
    s = Screen(); frame(s, "The Wall"); L = {}
    s.put(6, 3, "Scrawls left by callers passing through The Yellow Toaster", 6, 0)
    panelhead(s, 5, "RECENT")
    L.update(wall_y0=6, wall_n=12, wall_x=6)
    panelhead(s, 19, "")
    s.put(6, 21, "Leave your mark", 11, 0)
    s.put(22, 21, "(ENTER alone skips)", 6, 0)
    _bullet(s, 6, 23, 11); s.put(8, 23, "", 15, 0)     # prompt bullet; input at col 8
    L["prompt"] = (8, 23)
    return s, L

# -------------------------------------------------------------------- Settings
def make_settings():
    s = Screen(); frame(s, "Your Settings"); L = {}
    _bullet(s, 4, 3, 6); s.put(6, 3, "Signed in as", 6, 0)
    L["who"] = (19, 3)
    panelhead(s, 5, "TOGGLES", "press the key to flip")
    tog = [("A","ANSI Graphics","ansi"),("M","Page Pause (More)","more"),
           ("E","Expert Mode","expert")]
    for i,(k,lbl,key) in enumerate(tog):
        y = 6+i
        _bullet(s, 5, y, 14); s.put(7, y, "["+k+"]", 11, 0); s.put(11, y, lbl, 15, 0)
        L[key] = (44, y)          # ON/OFF overlaid here
    panelhead(s, 10, "ACCOUNT")
    _bullet(s, 5, 11, 14); s.put(7, 11, "[N]", 11, 0); s.put(11, 11, "Change real name / location", 15, 0)
    _bullet(s, 5, 12, 14); s.put(7, 12, "[P]", 11, 0); s.put(11, 12, "Change password", 15, 0)
    panelhead(s, 21, "")
    s.put(6, 23, "Choice", 6, 0); _bullet(s, 13, 23, 11)
    s.put(15, 23, "(key to toggle, [Q] to return)", 6, 0)
    L["cmd"] = (26, 23)           # single-char echo sits after the bullet
    L["sub"] = (6, 15)            # sub-prompt row for name/password entry
    return s, L

# ---------------------------------------------------------------- Voting Booth
def make_voting():
    s = Screen(); frame(s, "Voting Booth"); L = {}
    s.put(6, 3, "Topic:", 11, 0); L["topic"] = (13, 3)
    panelhead(s, 5, "")           # rule under the topic
    L.update(opt_y0=7, res_y0=7, body_x=6, bar_x=28, pct_x=62)
    panelhead(s, 21, "")
    s.put(6, 23, "Choice", 6, 0); _bullet(s, 13, 23, 11)
    L["cmd"] = (16, 23)
    L["note"] = (18, 23)          # "(1-5, or Q)" / result note
    return s, L

# ---------------------------------------------------------- Feedback to Sysop
def make_feedback():
    s = Screen(); frame(s, "Feedback to the Sysop"); L = {}
    s.put(6, 3, "A private line to", 6, 0); L["sysop"] = (24, 3)
    s.put(6, 5, "Found a bug? Got an idea? Want a new area or door? Say your piece.", 7, 0)
    s.put(6, 6, "Enter your message a line at a time; a blank line sends it.", 7, 0)
    panelhead(s, 8, "MESSAGE")
    s.put(6, 9, "Subject", 11, 0); _bullet(s, 14, 9, 11); L["subject"] = (16, 9)
    L.update(body_y0=11, body_n=8, body_x=6)   # message lines collected here
    panelhead(s, 21, "")
    L["status"] = (6, 23)
    return s, L

# ------------------------------------------------------------------ Tell a User
def make_tell():
    s = Screen(); frame(s, "Tell a User"); L = {}
    s.put(6, 3, "Send a one-line message to someone who's online.", 6, 0)
    _bullet(s, 6, 5, 6); s.put(8, 5, "Users online right now:", 6, 0); L["count"] = (32, 5)
    panelhead(s, 7, "COMPOSE")
    s.put(6, 9, "Send to", 11, 0); _bullet(s, 14, 9, 11); L["to"] = (16, 9)
    s.put(6, 10, "Message", 11, 0); _bullet(s, 14, 10, 11); L["msg"] = (16, 10)
    s.put(6, 12, "Username or line number; ENTER alone cancels.", 6, 0)
    panelhead(s, 21, "")
    L["status"] = (6, 23)
    return s, L

# -------------------------------------------------------------- QWK Offline Mail
def make_qwk():
    s = Screen(); frame(s, "QWK Offline Mail"); L = {}
    s.put(6, 3, "Read and reply to your mail offline in your favourite QWK reader.", 6, 0)
    _bullet(s, 6, 4, 6); s.put(8, 4, "Packages your current message base - select one first (M).", 6, 0)
    panelhead(s, 6, "TRANSFER")
    opts = [("D","Download a mail packet","every message in the base"),
            ("N","Download new mail only","just posts since your last call"),
            ("U","Upload your reply packet",".REP file from your offline reader")]
    y = 8
    for k,lbl,desc in opts:
        _bullet(s, 5, y, 14); s.put(7, y, "["+k+"]", 11, 0); s.put(11, y, lbl, 15, 0)
        s.put(11, y+1, desc, 6, 0)
        y += 2
    panelhead(s, 21, "")
    s.put(6, 23, "Choice", 6, 0); _bullet(s, 13, 23, 11)
    s.put(15, 23, "([D] [N] [U], or [Q] to return)", 6, 0)
    L["cmd"] = (26, 23); L["status"] = (6, 19)
    return s, L

PAGES = dict(Stats=make_stats, Oneliner=make_wall, Settings=make_settings,
             Voting=make_voting, Feedback=make_feedback, Tell=make_tell, QWK=make_qwk)

def _write(name, s):
    path = os.path.join(OUT, name); emit_ans(s, path); return path

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for name, fn in PAGES.items():
        if which in ("all", name):
            s,_ = fn(); _write(name, s)
