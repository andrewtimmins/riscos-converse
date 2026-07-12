#!/usr/bin/env python3
# Framed 80x25 menu/content screens in the shared house style (see gen.frame()).
# Nav menus (msgmenu/filemenu/doorsmenu) are shown via the `menu` primitive;
# bulletins/newuser/goodbye via `type`. All fill the terminal, box bottom on the
# last row, >> item markers, no blue status bar.
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from gen import *
try:
    g = load_font()
except Exception as e:
    g = None
    print("(font unavailable, skipping PNG previews: %s)" % e)
OUT = os.path.dirname(__file__)
def save(s,name):
    if g is not None:
        render_png(s,g,os.path.join(OUT,name+".png"))
    emit_ans(s,os.path.join(OUT,name+".ans"))

LEFT=4; RIGHT=74

def grouphead(s,x,y,txt,w=20):
    s.put(x,y,txt,3,0)
    for i in range(len(txt),w): s.putc(x+i,y,S_H,6,0)
def itemd(s,x,y,key,label,desc="",kc=11):
    s.putc(x,y,0xAF,14,0); s.put(x+2,y,"["+key+"]",kc,0); s.put(x+6,y,label,15,0)
    if desc: s.put(x+6,y+1,desc,6,0)
def rule(s,y,x0=LEFT,x1=RIGHT):
    for x in range(x0,x1+1): s.putc(x,y,S_H,6,0)
def promptbar(s,y=23,label="Command"):
    s.put(LEFT,y,label,6,0); s.putc(LEFT+len(label)+1,y,ARR,11,0); s.putc(LEFT+len(label)+3,y,FULL,15,0)

def infohead(s,l1,l2,r1,r2):
    # two-line info header; the VALUES are overlaid live by the script via pos.
    # left labels at col 6 (value col 13), right labels right-aligned to col 58
    # (value col 60). Positions are documented for the script overlays.
    s.put(6,3,l1,6,0); s.put(58-len(r1),3,r1,6,0)
    s.put(6,4,l2,6,0); s.put(58-len(r2),4,r2,6,0)

# ============================ MESSAGE BASES ============================
s=Screen()
frame(s,"Message Bases")
infohead(s,"Base:","Area:","Total:","Areas:")   # values overlaid: base/area @col13 r3/4; total/areas @col60 r3/4
rule(s,6)
grouphead(s,6,8,"READ & BROWSE",26)
itemd(s,6, 9,"R","Read Messages","the continuous reader")
itemd(s,6,12,"A","Areas & Bases","list and switch conference")
itemd(s,6,15,"S","Scan for New","new posts since last call")
itemd(s,6,18,"I","Your Inbox","private mail addressed to you")
for y in range(8,20): s.putc(40,y,D_V,6,0)
grouphead(s,44,8,"COMPOSE & SEND",26)
itemd(s,44, 9,"P","Post Public","write to the current area")
itemd(s,44,12,"E","Private E-mail","message a local user")
itemd(s,44,15,"N","Netmail","FidoNet mail to a node")
itemd(s,44,18,"F","Feedback","a private line to the sysop")
rule(s,21); promptbar(s)
save(s,"msgmenu")

# ============================ FILE LIBRARIES ============================
s=Screen()
frame(s,"File Libraries")
infohead(s,"Library:","Area:","Files:","Areas:")  # values overlaid live by the script
rule(s,6)
grouphead(s,6,8,"BROWSE",26)
itemd(s,6, 9,"L","List Files","catalogue of this area")
itemd(s,6,12,"A","Areas & Libs","list and switch library")
itemd(s,6,15,"S","Scan for New","files added since last call")
itemd(s,6,18,"V","View / Info","description, size, uploader")
for y in range(8,20): s.putc(40,y,D_V,6,0)
grouphead(s,44,8,"TRANSFER",26)
itemd(s,44, 9,"D","Download","send a file to your terminal")
itemd(s,44,12,"U","Upload","contribute a file")
itemd(s,44,15,"T","Tag / Batch","queue several files")
itemd(s,44,18,"Z","Protocols","ZMODEM, YMODEM, XMODEM")
rule(s,21); promptbar(s)
save(s,"filemenu")

# ============================ DOORS & GAMES ============================
s=Screen()
frame(s,"Doors & Games")
s.put(6,3,"Games online:",6,0); s.put(20,3,"7",11,0)
s.put(58,3,"Time left:",6,0)   # value overlaid live by the script @col 69
rule(s,5)
# name, desc, stars, [door type shown to the caller]
games=[
 ("1","Tetris","Falling blocks, the timeless classic","*****"),
 ("2","Snake","Guide the snake, don't bite your tail","****"),
 ("3","Breakout","Bat, ball and a wall of bricks","****"),
 ("4","Boxed In","Trap yourself a high score","***"),
 ("5","Trivia","Test your retro knowledge","****"),
 ("6","Purity Test","The infamous questionnaire","***"),
 ("7","The Wall","Read & scrawl on the graffiti wall","*****"),
]
y=7
for k,name,desc,stars in games:
    s.putc(6,y,0xAF,14,0)
    s.put(8,y,"["+k+"]",11,0)
    s.put(12,y,name,15,0)
    s.put(28,y,desc,7,0)
    s.put(68,y,stars,3,0)
    y+=2
rule(s,21)
s.put(LEFT,23,"Play a game (1-7), or [Q] to return",6,0)
s.putc(LEFT+36,23,ARR,11,0); s.putc(LEFT+38,23,FULL,15,0)
save(s,"doorsmenu")

# ============================ BULLETINS / NEWS ============================
s=Screen()
frame(s,"Bulletins & News")
s.center(3,"From the desk of the Sysop",3,0)
news=[
 ("10 Jul","New Acorn file library online","6",
  "247 fresh uploads - demos, PD games and RISC OS utilities."),
 ("08 Jul","RetroNet now carrying 6 echoes","2",
  "Chat, Coding, Hardware, Games, Emulation and Off-Topic."),
 ("02 Jul","Door tournament this weekend","11",
  "Top Tetris & Snake scores win extra download credit."),
 ("28 Jun","Be kind on The Wall","1",
  "One-liners are public and logged. Keep it friendly, folks."),
]
y=6
for date,head,col,body in news:
    s.putc(6,y,0xAF,int(col),0)
    s.put(8,y,date,3,0)
    s.put(16,y,head,15,0)
    s.put(8,y+1,body,7,0)
    y+=3
rule(s,21)
s.center(23,"-- press ENTER for the main menu --",6,0)
save(s,"bulletins")

# ============================ NEW USER WELCOME ============================
s=Screen()
frame(s,"New User Registration")
s.center(3,"Welcome, first-time caller!",11,0)
s.center(6,"You've reached The Yellow Toaster - a friendly retro BBS.",7,0)
s.center(8,"Setting up an account takes about a minute. We'll ask for:",7,0)
bul=[("a handle (your BBS name)"),("a password"),
     ("your real name (kept private)"),("an email address (optional)")]
for i,t in enumerate(bul):
    s.putc(24,11+i,0xAF,11,0); s.put(27,11+i,t,7,0)
rule(s,17)
s.center(18,"House rules: be civil, no warez, keep The Wall friendly.",3,0)
s.center(20,"Answer N at the final prompt and nothing is saved.",6,0)
s.center(23,"Press ENTER to begin, or ESC to log on to an existing account.",14,0)
save(s,"newuser")

# ============================ GOODBYE / LOG OFF ============================
s=Screen()
frame(s,"Log Off")
s.center(3,"7 3 !",3,0)
s.center(5,"Thanks for calling",15,0)
s.center(6,"THE YELLOW TOASTER",11,0)
s.box(24,9,32,8,6,0,False)
s.put(26,9,chr(D_RT)+" This call "+chr(D_LT),14,0)
rows=[("Time on","00:17:42"),("Downloads","2 files"),("Posts made","3"),("Calls total","1,024")]
for i,(k,v) in enumerate(rows):
    s.put(27,11+i,k,7,0); s.put(45,11+i,v,11,0)
rule(s,19)
s.center(21,"Hang up when ready - carrier will drop shortly.",6,0)
s.center(23,"See you next time o/",6,0)
save(s,"goodbye")

# ============================ LAST CALLERS (backdrop) ============================
# Full box + column headers; the caller rows + caller-number are overlaid live by
# the LastCallers script (KV ring data).
s=Screen()
frame(s,"Last Callers")
s.center(3,"Recent callers to The Yellow Toaster",6,0)
s.put(8,5,"User",11,0); s.put(24,5,"Real Name",11,0); s.put(50,5,"When",11,0)
rule(s,6)
rule(s,20)
save(s,"lastcall")

print("framed screens generated")
