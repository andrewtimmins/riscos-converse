#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from gen import *

g = load_font()
s = Screen()

# ---- 5x5 readable block font (only the letters we need) ----
GL = {
'T':["#####","..#..","..#..","..#..","..#.."],
'H':["#...#","#...#","#####","#...#","#...#"],
'E':["#####","#....","###..","#....","#####"],
'Y':["#...#",".#.#.","..#..","..#..","..#.."],
'L':["#....","#....","#....","#....","#####"],
'O':[".###.","#...#","#...#","#...#",".###."],
'W':["#...#","#...#","#.#.#","##.##","#...#"],
'A':[".###.","#...#","#####","#...#","#...#"],
'S':[".####","#....",".###.","....#","####."],
'R':["####.","#...#","####.","#..#.","#...#"],
' ':["     ","     ","     ","     ","     "],
}
def word(sx, sy, txt, fg, shadow=None):
    w = len(txt)*6
    x0 = sx if sx is not None else (COLS-w)//2
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

# ---- background frame ----
for x in range(COLS): s.putc(x,0, FULL, 3, 0)      # amber top rule
s.box(0,1,COLS,ROWS-2,6,0,double=True)              # cyan double frame
s.putc(0,1,D_TL,14,0); s.putc(COLS-1,1,D_TR,14,0)
_tab = chr(D_RT)+" The Yellow Toaster "+chr(D_LT)
s.put((COLS-len(_tab))//2,1, _tab, 14, 0)

# ---- wordmark ----
s.center(2,"T  H  E", 14, 0)
word(None,4,"YELLOW", 11, shadow=3)     # bright yellow + amber shadow
word(None,10,"TOASTER", 3, shadow=1)    # amber + red shadow

# ---- subtitle band ----
for x in range(6,COLS-5): s.putc(x,16, MED, 3, 0)
s.center(16, "  a retro BBS for fans of classic computing  ", 14, 0)

# ---- feature bullets ----
feats=[
 "Chat across six FidoNet-style networks",
 "Download demos, utilities & software for retro kit",
 "Play classic door games - Tetris, Snake, Breakout & more",
 "A friendly community that still remembers dial-up",
]
for i,t in enumerate(feats):
    s.putc(13,18+i, BULLET, 11, 0); s.put(15,18+i, t, 7, 0)

# ---- bottom status bar ----
s.fillrow(ROWS-1, 0x20, 15, 4)
s.put(1,ROWS-1, chr(TRI)+" 2400-115200 baud", 14, 4)
_sr = "NEW user? type NEW  "+chr(BULLET)+"  ENTER to log on"
s.put(COLS-len(_sr)-1, ROWS-1, _sr, 15, 4)

render_png(s,g,os.path.join(os.path.dirname(__file__),"login.png"))
emit_ans(s,os.path.join(os.path.dirname(__file__),"Login.ans"))
