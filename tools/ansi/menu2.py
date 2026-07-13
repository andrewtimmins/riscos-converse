#!/usr/bin/env python3
"""Rich menu house-style: amber rule + single cyan frame + block TOASTER
wordmark masthead + colourful hotkey chips + shaded gradient rules. Live
status/thought/prompt are overlaid by the calling script (blank rows left
here). Palette (VGA): 3 amber, 11 bright yellow, 6 cyan, 14 bright cyan,
15 white, 10 green, 1 red.

Importable: masthead(), key(), tab(), ggrad(), word() are shared by the
submenu generators (see submenus.py). Running this file directly emits the
main menu (mainmenu2.ans)."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from gen import *

# ---- 5x5 block font (from login.py) for the wordmark ----
GL = {
'T':["#####","..#..","..#..","..#..","..#.."],'H':["#...#","#...#","#####","#...#","#...#"],
'E':["#####","#....","###..","#....","#####"],'O':[".###.","#...#","#...#","#...#",".###."],
'A':[".###.","#...#","#####","#...#","#...#"],'S':[".####","#....",".###.","....#","####."],
'R':["####.","#...#","####.","#..#.","#...#"],' ':["     ","     ","     ","     ","     "],
}
def word(s, sx, sy, txt, fg, shadow=None):
    w=len(txt)*6; x0=sx if sx is not None else (COLS-w)//2
    if shadow is not None:
        for i,ch in enumerate(txt):
            pat=GL.get(ch,GL[' ']); bx=x0+i*6+1
            for r in range(5):
                for c,p in enumerate(pat[r]):
                    if p=='#': s.putc(bx+c, sy+r+1, FULL, shadow, 0)
    for i,ch in enumerate(txt):
        pat=GL.get(ch,GL[' ']); bx=x0+i*6
        for r in range(5):
            for c,p in enumerate(pat[r]):
                if p=='#': s.putc(bx+c, sy+r, FULL, fg, 0)

def ggrad(s, y, x0, x1, fg):
    """symmetric shaded rule ..:::==###==:::.. using LT/MED/DK/FULL blocks."""
    seq=[LT,LT,MED,MED,DK,DK,FULL]
    n=x1-x0; mid=(x0+x1)//2
    for x in range(x0,x1):
        d=abs(x-mid); lvl=max(0, len(seq)-1-d//2)
        s.putc(x,y, seq[min(lvl,len(seq)-1)], fg, 0)

def key(s,x,y,k,label,kc=11):
    s.put(x,y,"[",6); s.put(x+1,y,k,kc); s.put(x+2,y,"]",6); s.put(x+4,y,label,15)
def tab(s,x,y,txt):
    s.put(x,y," "+txt+" ",0,6)          # black on cyan header chip

def masthead(s, subtitle, sub_col=14):
    """Shared top-of-screen branding used by every rich menu: amber top rule,
    cyan double frame with bright-cyan top corners, 'THE YELLOW' + TOASTER
    block wordmark (rows 2-7), a per-screen subtitle (row 8), a live-status row
    left blank for the caller (row 9), and a shaded amber rule (row 10)."""
    for x in range(COLS): s.putc(x,0, FULL, 3, 0)
    s.box(0,1,COLS,ROWS-1,6,0,double=True)
    s.putc(0,1,D_TL,14,0); s.putc(COLS-1,1,D_TR,14,0)
    s.center(2, "T H E   Y E L L O W", 11, 0)
    word(s, None, 3, "TOASTER", 3, shadow=1)          # amber block + red shadow
    s.fillrow(8, 0x20, 7, 0, 1, COLS-1)                # clear the wordmark's row-8 shadow remnant (default cell = trimmable)
    s.center(8, subtitle, sub_col, 0)
    ggrad(s, 10, 4, COLS-4, 3)                          # row 9 = live status (overlaid)


def build_mainmenu():
    s=Screen()
    masthead(s, "  a retro BBS for fans of classic computing  ", 14)

    # ---- menu block 1 ----
    tab(s,5,11,"MESSAGES"); tab(s,31,11,"FILES & DOORS"); tab(s,56,11,"COMMUNITY")
    key(s,5,12,"M","Message bases");  key(s,31,12,"F","File libraries"); key(s,56,12,"W","The Wall")
    key(s,5,13,"S","Scan new posts"); key(s,31,13,"D","Doors & games");  key(s,56,13,"B","Bulletins")
    key(s,5,14,"I","Your inbox");     key(s,31,14,"O","Who's online");   key(s,56,14,"L","Last callers")
    key(s,5,15,"A","QWK mail");                                          key(s,56,15,"V","Voting booth")

    # ---- menu block 2 ----
    tab(s,5,17,"YOUR ACCOUNT"); tab(s,31,17,"SYSTEM"); tab(s,56,17,"SESSION")
    key(s,5,18,"U","Settings");    key(s,31,18,"C","Chat to sysop"); key(s,56,18,"?","Help")
    key(s,5,19,"G","Feedback");    key(s,31,19,"H","Hall of fame");  key(s,56,19,"Q","Log off")
    key(s,5,20,"T","Tell a user")

    # ---- footer ----
    ggrad(s, 21, 4, COLS-4, 3)
    # row 22 = thought (overlaid) ; row 23 = command prompt (overlaid)
    return s

if __name__ == "__main__":
    s=build_mainmenu()
    out=os.path.join(os.path.dirname(__file__),"mainmenu2.ans")
    emit_ans(s,out,rows=ROWS)
