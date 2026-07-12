#!/usr/bin/env python3
"""ANSI/CP437 screen generator for the Converse demo BBS.

- Parses the terminal's real VGA font (Font,ffd: 256 glyphs, 16x16, 2 bytes/row).
- Screen model: 80x25 grid of (char, fg, bg); fg 0-15 (bright via bold), bg 0-7.
- render_png(): pixel-accurate preview using the real font + VGA palette.
- emit_ans(): .ANS-style output (raw CP437 bytes + ANSI SGR) for the `type` cmd.
"""
import os
from PIL import Image

FONT = "/projects/riscos-converse/!Converse/Resources/Font,ffd"
CW, CH = 16, 16          # cell pixel size (font is 16x16)
# 79 wide (never touch the wrap column -> no phantom lines on any client) and
# 24 tall (fits an 80x24 terminal with no scroll). Layout derives from these.
COLS, ROWS = 79, 25

# Standard VGA/ANSI 16-colour palette (index 0-15)
PAL = [
    (0,0,0),(170,0,0),(0,170,0),(170,85,0),
    (0,0,170),(170,0,170),(0,170,170),(170,170,170),
    (85,85,85),(255,85,85),(85,255,85),(255,255,85),
    (85,85,255),(255,85,255),(85,255,255),(255,255,255),
]

def load_font(path=FONT):
    data = open(path,"rb").read()
    glyphs=[]
    for ch in range(256):
        base=ch*32
        rows=[]
        for r in range(16):
            hi=data[base+r*2]; lo=data[base+r*2+1]
            rows.append((hi<<8)|lo)   # 16-bit row, MSB = leftmost pixel
        glyphs.append(rows)
    return glyphs

# ---- CP437 code points for the art (by name, for readability) ----
FULL=0xDB; LT=0xB0; MED=0xB1; DK=0xB2          # blocks / shades
UH=0xDF; LH=0xDC; LEFTH=0xDD; RIGHTH=0xDE       # half blocks
# double box
D_H=0xCD; D_V=0xBA; D_TL=0xC9; D_TR=0xBB; D_BL=0xC8; D_BR=0xBC
D_LT=0xCC; D_RT=0xB9; D_TT=0xCB; D_BT=0xCA; D_X=0xCE
# single box
S_H=0xC4; S_V=0xB3; S_TL=0xDA; S_TR=0xBF; S_BL=0xC0; S_BR=0xD9
S_LT=0xC3; S_RT=0xB4; S_TT=0xC2; S_BT=0xC1; S_X=0xC5
BULLET=0x07; DIAM=0x04; STAR=0x0F; ARR=0x10; TRI=0x1F

# --- Telnet-safe glyph substitution -----------------------------------------
# CP437's decorative glyphs at 0x00-0x1F (bullets, arrows, hearts) live in the
# C0 control range. RPCEmu's built-in terminal renders them as glyphs, but a
# real telnet client interprets them as control codes -- 0x0A=LF, 0x0D=CR,
# 0x09=TAB, 0x07=bell, 0x1B=ESC -- which injects newlines/tabs and destroys the
# layout. Map every C0 byte (and 0x7F) to the closest printable HIGH-range
# CP437 glyph, which a CP437 terminal renders identically. Applied in BOTH
# render_png and emit_ans so the PNG preview matches what the wire sends.
_ARROW_GLYPHS = {0x10, 0x18, 0x1A, 0x1D, 0x1E, 0x1F}   # arrows/triangles -> »
def safe_glyph(ch):
    if 0x20 <= ch <= 0x7e or ch >= 0xa0:
        return ch                 # already printable / high-range CP437
    if ch in _ARROW_GLYPHS:
        return 0xAF               # »
    if ch == 0x09:
        return 0xF8               # ° (small ring, was ○)
    return 0xF9                   # ∙ generic bullet / marker

class Screen:
    def __init__(self):
        self.cells=[[(0x20,7,0) for _ in range(COLS)] for _ in range(ROWS)]
    def put(self,x,y,text,fg=7,bg=0):
        for i,c in enumerate(text):
            if 0<=x+i<COLS and 0<=y<ROWS:
                b = c if isinstance(c,int) else ord(c)
                self.cells[y][x+i]=(b,fg,bg)
    def putc(self,x,y,ch,fg=7,bg=0):
        if 0<=x<COLS and 0<=y<ROWS: self.cells[y][x]=(ch,fg,bg)
    def fillrow(self,y,ch=0x20,fg=7,bg=0,x0=0,x1=COLS):
        for x in range(x0,x1): self.putc(x,y,ch,fg,bg)
    def hline(self,x,y,w,ch,fg,bg=0):
        for i in range(w): self.putc(x+i,y,ch,fg,bg)
    def box(self,x,y,w,h,fg,bg=0,double=True):
        H,V,TL,TR,BL,BR = ((D_H,D_V,D_TL,D_TR,D_BL,D_BR) if double
                           else (S_H,S_V,S_TL,S_TR,S_BL,S_BR))
        self.putc(x,y,TL,fg,bg); self.putc(x+w-1,y,TR,fg,bg)
        self.putc(x,y+h-1,BL,fg,bg); self.putc(x+w-1,y+h-1,BR,fg,bg)
        for i in range(1,w-1):
            self.putc(x+i,y,H,fg,bg); self.putc(x+i,y+h-1,H,fg,bg)
        for j in range(1,h-1):
            self.putc(x,y+j,V,fg,bg); self.putc(x+w-1,y+j,V,fg,bg)
    def center(self,y,text,fg=7,bg=0):
        x=(COLS-len(text))//2; self.put(x,y,text,fg,bg)

def render_png(scr,glyphs,path,scale=1):
    img=Image.new("RGB",(COLS*CW,ROWS*CH),(0,0,0))
    px=img.load()
    for y in range(ROWS):
        for x in range(COLS):
            ch,fg,bg=scr.cells[y][x]
            fc=PAL[fg]; bc=PAL[bg]; g=glyphs[safe_glyph(ch)]
            ox,oy=x*CW,y*CH
            for r in range(16):
                bits=g[r]
                for c in range(16):
                    on=(bits>>(15-c))&1
                    px[ox+c,oy+r]=fc if on else bc
    if scale!=1:
        img=img.resize((img.width*scale,img.height*scale),Image.NEAREST)
    img.save(path)
    print("wrote",path,img.size)

def emit_ans(scr,path,rows=ROWS,home=True):
    out=bytearray()
    if home: out+=b"\x1b[2J\x1b[H"
    cfg=cbg=cbold=None
    def setcol(fg,bg):
        nonlocal cfg,cbg,cbold
        bold=1 if fg>=8 else 0
        base=fg&7
        codes=[]
        if bold!=cbold:
            # toggling bold off needs a reset (SGR 0) then reapply
            if bold==0:
                out.extend(b"\x1b[0m"); cfg=cbg=None
            codes.append("1" if bold else "0"); cbold=bold
        if (base)!=cfg: codes.append(str(30+base)); cfg=base
        if bg!=cbg: codes.append(str(40+bg)); cbg=bg
        if codes: out.extend(("\x1b["+";".join(codes)+"m").encode("latin1"))
    for y in range(rows):
        # trim trailing spaces on default bg to keep files tidy
        last=COLS-1
        while last>=0 and scr.cells[y][last]==(0x20,7,0): last-=1
        for x in range(last+1):
            ch,fg,bg=scr.cells[y][x]
            setcol(fg,bg)
            out.append(safe_glyph(ch))
        out.extend(b"\x1b[0m"); cfg=cbg=cbold=None
        if y<rows-1: out.extend(b"\r\n")
    open(path,"wb").write(out)
    print("wrote",path,len(out),"bytes")

def chrome(s, title, statL="", statR=""):
    """Shared screen chrome: amber top rule (row 0), cyan double frame with a
    title tab (rows 1..ROWS-2), and a blue reverse-video status bar on the
    last row. All coordinates derive from COLS/ROWS."""
    for x in range(COLS): s.putc(x,0, FULL, 3, 0)
    s.box(0,1,COLS,ROWS-2,6,0,double=True)
    s.putc(0,1,D_TL,14,0); s.putc(COLS-1,1,D_TR,14,0)
    tab=" "+title+" "
    tx=(COLS-len(tab)-2)//2
    s.putc(tx,1,D_RT,14,0); s.put(tx+1,1,tab,15,0); s.putc(tx+1+len(tab),1,D_LT,14,0)
    s.fillrow(ROWS-1, 0x20, 15, 4)
    if statL: s.put(1,ROWS-1," "+statL, 14, 4)
    if statR: s.put(COLS-len(statR)-2, ROWS-1, statR+" ", 15, 4)

def frame(s, title, boxcol=6):
    """House-style page frame that FILLS the 80x25 terminal: amber top rule
    (row 0), cyan double box whose bottom border sits on the LAST row (row
    ROWS-1, no status-bar gap), and a centred title tab. Used by every menu and
    content page so the board reads as one system."""
    for x in range(COLS): s.putc(x,0, FULL, 3, 0)              # amber top rule
    s.box(0,1,COLS,ROWS-1,boxcol,0,double=True)                # box rows 1..ROWS-1 (bottom = last row)
    s.putc(0,1,D_TL,14,0); s.putc(COLS-1,1,D_TR,14,0)
    tab=" "+title+" "
    tx=(COLS-len(tab)-2)//2
    s.putc(tx,1,D_RT,14,0); s.put(tx+1,1,tab,15,0); s.putc(tx+1+len(tab),1,D_LT,14,0)

# consistent >> item marker used across all framed menus
def item(s,x,y,key,label,keycol=11):
    s.putc(x,y,0xAF,14,0); s.put(x+2,y,"["+key+"]",keycol,0); s.put(x+6,y,label,15,0)

def menuitem(s,x,y,ic,key,label,desc,keycol=11,iccol=14):
    s.putc(x,y, ic, iccol, 0)
    s.put(x+2,y, "["+key+"]", keycol, 0)
    s.put(x+6,y, label, 15, 0)
    if desc: s.put(x+6,y+1, desc, 6, 0)

def panelhead(s,y,left,right="",fg=6):
    for x in range(3,COLS-3): s.putc(x,y, S_H, fg, 0)
    if left: s.put(5,y," "+left+" ", 11, 0)
    if right: s.put(COLS-3-len(right)-2,y," "+right+" ", 6, 0)

def prompt(s,y,label="Command"):
    s.put(6,y, label, 6, 0); s.putc(6+len(label)+1,y, ARR, 11, 0)
    s.putc(6+len(label)+3,y, FULL, 15, 0)
