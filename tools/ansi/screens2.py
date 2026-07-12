#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gen
gen.ROWS = 25            # the local ansiterm terminal is 80x25 - fill it
from gen import *
try:
    g = load_font()
except Exception as e:
    g = None            # PNG preview needs the font; .ans emit does not
    print("(font unavailable, skipping PNG previews: %s)" % e)
OUT = os.path.dirname(__file__)
def save(s,name,rows=None):
    if rows is None: rows = gen.ROWS
    if g is not None:
        render_png(s,g,os.path.join(OUT,name+".png"))
    emit_ans(s,os.path.join(OUT,name+".ans"),rows=rows)
STAT = chr(TRI)+" Line 1  "+chr(BULLET)+"  GUEST"

def citem(s,x,y,ic,key,label,kc=11):
    # every item uses the same >> marker (0xAF) for consistency
    s.putc(x,y,0xAF,14,0); s.put(x+2,y,"["+key+"]",kc,0); s.put(x+6,y,label,15,0)
def grouphead(s,x,y,txt,w=20):
    s.put(x,y,txt,3,0)
    for i in range(len(txt),w): s.putc(x+i,y,S_H,6,0)

# ===================== MAIN MENU (fills 80x25, full-width, left-aligned) =====================
# 25 rows: the box bottom border + Command prompt sit on the last rows so there's
# no dead black space. Manual frame (chrome leaves a row for a status bar we don't
# want). Header rows 3 (welcome + [?] Help) and 5 (stats) are filled with live data
# by tools/ansi/patch_mainmenu.py; rows 2/4/6 stay blank for breathing room.
LEFT=4; C1=4; C2=29; C3=54; GW=21; RIGHT=74
s=Screen()
for x in range(COLS): s.putc(x,0,FULL,3,0)                 # amber top rule
s.box(0,1,COLS,gen.ROWS-1,6,0,double=True)                 # box rows 1..24 (bottom = last row)
s.putc(0,1,D_TL,14,0); s.putc(COLS-1,1,D_TR,14,0)
_tab=" The Yellow Toaster  -  Main Menu "
_tx=(COLS-len(_tab)-2)//2
s.putc(_tx,1,D_RT,14,0); s.put(_tx+1,1,_tab,15,0); s.putc(_tx+1+len(_tab),1,D_LT,14,0)

for x in range(LEFT,RIGHT+1): s.putc(x,7,S_H,6,0)          # divider under header

grouphead(s,C1,9,"MESSAGES",GW)
citem(s,C1,10,0,"M","Message Bases"); citem(s,C1,11,0,"S","Scan for New"); citem(s,C1,12,0,"I","Your Inbox")
grouphead(s,C2,9,"FILES & FUN",GW)
citem(s,C2,10,0,"F","File Libraries"); citem(s,C2,11,0,"D","Doors & Games"); citem(s,C2,12,0,"O","Who's Online")
grouphead(s,C3,9,"COMMUNITY",GW)
citem(s,C3,10,0,"W","The Wall"); citem(s,C3,11,0,"B","Bulletins"); citem(s,C3,12,0,"L","Last Callers")

for x in range(LEFT,RIGHT+1): s.putc(x,14,S_H,6,0)         # divider between blocks
grouphead(s,C1,16,"YOUR ACCOUNT",GW)
citem(s,C1,17,0,"U","Settings"); citem(s,C1,18,0,"G","Feedback"); citem(s,C1,19,0,"C","Chat to Sysop")
grouphead(s,C2,16,"THE SYSTEM",GW)
citem(s,C2,17,0,"H","Hall of Fame"); citem(s,C2,18,0,"V","Voting Booth"); citem(s,C2,19,0,"?","Help & Commands")
grouphead(s,C3,16,"EXIT",GW)
citem(s,C3,17,0,"Q","Log Off",12)

for x in range(LEFT,RIGHT+1): s.putc(x,21,S_H,6,0)         # divider above the prompt
# prompt on the last interior row (row 23); box bottom border is row 24
s.put(LEFT,23,"Command",6,0); s.putc(LEFT+8,23,ARR,11,0); s.putc(LEFT+10,23,FULL,15,0)
save(s,"mainmenu",rows=gen.ROWS)

# ============================ USER SETTINGS ============================
s=Screen()
chrome(s,"User Settings", STAT, "[Q] save & return ")
s.center(3,"Tune the board to your terminal & taste",6,0)
for x in range(20,60): s.putc(x,4,S_H,6,0)
def setting(s,y,key,label,val,on=True):
    s.putc(10,y,0x10,14,0); s.put(12,y,"["+key+"]",11,0)
    s.put(16,y,label,15,0)
    vc = 10 if on else 8
    s.put(52,y,val,vc,0)
setting(s,7,"A","ANSI Graphics","ON")
setting(s,8,"C","Colour","ON")
setting(s,9,"W","Screen Width","79 columns",True)
setting(s,10,"P","Page Pause (More)","ON")
setting(s,11,"E","Message Editor","Full-screen",True)
setting(s,12,"H","Hot-keyed Menus","ON")
setting(s,13,"R","Show Real Name","OFF",False)
for x in range(10,70): s.putc(x,15,S_H,6,0)
s.putc(10,17,0x10,14,0); s.put(12,17,"[X]",11,0); s.put(16,17,"Change Password",15,0)
s.putc(10,18,0x10,14,0); s.put(12,18,"[N]",11,0); s.put(16,18,"Change Real Name / Location",15,0)
s.put(10,20,"Toggle a setting with its key; changes save on [Q].",8,0)
prompt(s,21)
save(s,"settings")

# ============================ HALL OF FAME / STATS ============================
s=Screen()
chrome(s,"Hall of Fame", STAT, "[ENTER] continue ")
# three panels across the top
def panel(s,x,y,w,h,title):
    s.box(x,y,w,h,6,0,False); s.put(x+2,y,chr(D_RT)+" "+title+" "+chr(D_LT),14,0)
panel(s,4,3,36,9,"Top Posters")
posters=[("MegaByte","1,204"),("AcornArthur","987"),("PiWizard","842"),("8bitBaz","713"),("StrongARM","655")]
for i,(n,c) in enumerate(posters):
    s.put(6,5+i,chr(0x07),3,0); s.put(8,5+i,("%d."%(i+1)),8,0); s.put(11,5+i,n,15,0); s.put(31,5+i,c,11,0)
panel(s,40,3,36,9,"Top Uploaders")
ups=[("DemoScener","318 MB"),("PiWizard","204 MB"),("MegaByte","155 MB"),("RetroRod","98 MB"),("8bitBaz","61 MB")]
for i,(n,c) in enumerate(ups):
    s.put(42,5+i,chr(0x1E),3,0); s.put(44,5+i,("%d."%(i+1)),8,0); s.put(47,5+i,n,15,0); s.put(67,5+i,c,11,0)
# door high scores
panel(s,4,12,72,7,"Door High Scores")
scores=[("Tetris","MegaByte","148,220"),("Snake","PiWizard","9,940"),
        ("Breakout","8bitBaz","41,700"),("Trivia","AcornArthur","98/100")]
for i,(gm,n,sc) in enumerate(scores):
    x=6 if i%2==0 else 40; y=14+(i//2)
    s.putc(x,y,0x06,14,0); s.put(x+2,y,gm,3,0); s.put(x+14,y,n,15,0); s.put(x+28,y,sc,11,0)
# system totals footer
for x in range(4,76): s.putc(x,20,S_H,6,0)
s.put(5,21,"System:",6,0)
s.put(13,21,"48,015 calls",7,0); s.put(30,21,chr(BULLET),3,0)
s.put(33,21,"1,140 users",7,0); s.put(48,21,chr(BULLET),3,0)
s.put(51,21,"up since Mar 1994",7,0)
save(s,"stats")

# ============================ VOTING BOOTH ============================
s=Screen()
chrome(s,"Voting Booth", STAT, "[1-5] vote  [Q] return ")
s.center(3,"Topic 7 of 12",8,0)
s.center(4,"What's the greatest 8-bit micro of all time?",15,0)
for x in range(14,66): s.putc(x,5,S_H,6,0)
opts=[("1","BBC Micro",42,11),("2","Commodore 64",28,14),("3","ZX Spectrum",19,10),
      ("4","Amstrad CPC",8,6),("5","Acorn Electron",3,3)]
y=8
for k,name,pct,col in opts:
    s.put(6,y,"["+k+"]",11,0); s.put(10,y,name,15,0)
    barw=int(pct/100*40)
    for i in range(40):
        s.putc(28+i,y, FULL if i<barw else LT, col if i<barw else 8, 0)
    s.put(70,y,"%d%%"%pct,14,0)
    y+=2
for x in range(14,66): s.putc(x,19,S_H,6,0)
s.center(20,"1,204 votes cast   "+chr(BULLET)+"   one vote per caller",8,0)
s.center(21,"Press 1-5 to cast your vote, or Q to return.",6,0)
save(s,"voting")

# ============================ FEEDBACK TO SYSOP ============================
s=Screen()
chrome(s,"Feedback to the Sysop", STAT, "[ENTER] write  [ESC] cancel ")
s.center(3,"A private line to the operator",6,0)
for x in range(24,56): s.putc(x,4,S_H,6,0)
s.center(7,"Found a bug? Got an idea? Want a new message area or door?",7,0)
s.center(8,"Drop the sysop a note - it's delivered as private mail",7,0)
s.center(9,"and nobody else will see it.",7,0)
# a little framed 'compose' hint
s.box(16,12,48,7,6,0,True); s.put(18,12,chr(D_RT)+" Your message "+chr(D_LT),14,0)
s.put(19,14,"Type your message when the editor opens.",8,0)
s.put(19,15,"A blank line on its own sends it.",8,0)
s.put(19,16,chr(0x07)+" Be as detailed as you like.",8,0)
s.center(21,"Press ENTER to start writing, or ESC to go back.",14,0)
save(s,"feedback")

# ============================ HELP / COMMANDS ============================
s=Screen()
chrome(s,"Help  -  Command Reference", STAT, "[ENTER] continue ")
s.center(3,"Hot-keys work from almost anywhere on the board",6,0)
grouphead(s,6,5,"GLOBAL",16)
gl=[("M","Message bases"),("F","File libraries"),("D","Doors & games"),
    ("W","The Wall"),("C","Chat to sysop"),("Q","Log off")]
for i,(k,d) in enumerate(gl):
    x=6 if i<3 else 40; y=7+(i%3)
    s.put(x,y,"["+k+"]",11,0); s.put(x+4,y,d,7,0)
grouphead(s,6,11,"READING",16)
rd=[("R","Read messages"),("N","Next message"),("P","Previous / Post"),
    ("A","Area / base list"),("S","Scan for new"),("I","Your inbox")]
for i,(k,d) in enumerate(rd):
    x=6 if i<3 else 40; y=13+(i%3)
    s.put(x,y,"["+k+"]",11,0); s.put(x+4,y,d,7,0)
grouphead(s,6,17,"ANYTIME",16)
s.put(6,19,"[?]",11,0); s.put(10,19,"this help",7,0)
s.put(40,19,"[Ctrl-]",11,0); s.put(48,19,"release mouse / abort",7,0)
s.center(21,"-- press ENTER to return --",8,0)
save(s,"help")

print("phase-2 screens generated")
