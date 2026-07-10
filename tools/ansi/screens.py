#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from gen import *
g = load_font()
OUT = os.path.dirname(__file__)
def save(s,name):
    render_png(s,g,os.path.join(OUT,name+".png"))
    emit_ans(s,os.path.join(OUT,name+".ans"))

STAT = chr(TRI)+" Line 1  "+chr(BULLET)+"  GUEST"

# ============================ MESSAGE BASES ============================
s=Screen()
chrome(s,"Message Bases", STAT, "[Q] Main Menu ")
s.put(4,3,"Base:",6,0); s.put(10,3,"RetroNet / General Chatter",15,0)
s.put(4,4,"Area:",6,0); s.put(10,4,"Acorn & RISC OS",15,0)
s.put(52,3,"Unread:",6,0); s.put(60,3,"12 msgs",11,0)
s.put(52,4,"Total:",6,0); s.put(60,4,"3,481",14,0)
panelhead(s,6,"Read & Browse","")
menuitem(s,6, 8,0x0E,"R","Read Messages","continuous reader, page by page")
menuitem(s,6,11,0x1D,"A","Areas & Bases","list and switch conference")
menuitem(s,6,14,0x18,"S","Scan for New","new public posts since last call")
menuitem(s,6,17,0xF0,"I","Your Inbox","private mail addressed to you")
panelhead(s,6,"","")
s.putc(41,6,D_TT,6,0)
for y in range(7,18): s.putc(41,y,D_V,6,0)  # vertical divider
panelhead(s,18,"Compose & Send","")
menuitem(s,44, 8,0x0D,"P","Post Public","write to the current area")
menuitem(s,44,11,0x03,"E","Private E-mail","message another local user")
menuitem(s,44,14,0x0A,"N","Netmail","FidoNet-style mail to a node")
menuitem(s,44,17,0x0F,"F","Feedback","a private line to the sysop")
prompt(s,21)
save(s,"msgmenu")

# ============================ FILE LIBRARIES ============================
s=Screen()
chrome(s,"File Libraries", STAT, "[Q] Main Menu ")
s.put(4,3,"Library:",6,0); s.put(13,3,"Acorn Software",15,0)
s.put(4,4,"Area:",6,0); s.put(13,4,"Games & Demos",15,0)
s.put(52,3,"Files:",6,0); s.put(60,3,"247",14,0)
s.put(52,4,"New:",6,0); s.put(60,4,"5 today",11,0)
panelhead(s,6,"Browse","")
menuitem(s,6, 8,0x1A,"L","List Files","catalogue of the current area")
menuitem(s,6,11,0x1D,"A","Areas & Libs","switch library / area")
menuitem(s,6,14,0x18,"S","Scan for New","files added since last call")
menuitem(s,6,17,0x09,"V","View / Info","description, size, uploader")
for y in range(7,18): s.putc(41,y,D_V,6,0)
panelhead(s,18,"Transfer","")
menuitem(s,44, 8,0x19,"D","Download","send a file to your terminal")
menuitem(s,44,11,0x18,"U","Upload","contribute a file to the library")
menuitem(s,44,14,0x1C,"T","Tag / Batch","queue several for one transfer")
menuitem(s,44,17,0x0F,"Z","Protocols","ZMODEM, YMODEM, XMODEM")
prompt(s,21)
save(s,"filemenu")

# ============================ DOORS & GAMES ============================
s=Screen()
chrome(s,"Doors & Games", STAT, "[Q] Main Menu ")
s.center(3,"Take a break and play a classic -- every door runs live on your line",6,0)
games=[
 ("1","Tetris","Falling blocks, the timeless classic","*****"),
 ("2","Snake","Guide the snake, don't bite your tail","****"),
 ("3","Breakout","Bat, ball and a wall of bricks","****"),
 ("4","Boxed In","Trap yourself a high score","***"),
 ("5","Trivia","Test your retro knowledge","****"),
 ("6","Purity Test","The infamous questionnaire","***"),
 ("7","The Wall","Read & scrawl on the graffiti wall","*****"),
]
y=6
for k,name,desc,stars in games:
    s.putc(8,y,0x06,14,0)
    s.put(10,y,"["+k+"]",11,0)
    s.put(14,y,name,15,0)
    s.put(30,y,desc,7,0)
    s.put(68,y,stars,3,0)      # rendered as CP437 -> shows as * rating
    y+=2
panelhead(s,19,"","")
s.put(8,20,"[Q]",12,0); s.put(12,20,"Return to Main Menu",15,0)
prompt(s,21,"Play")
save(s,"doorsmenu")

# ============================ BULLETINS / NEWS ============================
s=Screen()
chrome(s,"Bulletins & News", STAT, "[ENTER] continue ")
s.center(3,"From the desk of the Sysop",3,0)
for x in range(20,60): s.putc(x,4,S_H,6,0)
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
    s.putc(6,y,0x10,int(col),0)
    s.put(8,y,date,3,0)
    s.put(16,y,head,15,0)
    s.put(8,y+1,body,7,0)
    y+=3
s.center(21,"-- press ENTER for the main menu --",8,0)
save(s,"bulletins")

# ============================ LAST CALLERS ============================
s=Screen()
chrome(s,"Last Callers", STAT, "[ENTER] continue ")
# table header
s.put(6,3,"Handle",11,0); s.put(24,3,"From",11,0); s.put(46,3,"When",11,0); s.put(60,3,"Doing",11,0)
for x in range(5,75): s.putc(x,4,S_H,6,0)
callers=[
 ("MegaByte","Cambridge UK","23:14","Reading msgs"),
 ("AcornArthur","Leeds","22:58","Downloading"),
 ("PiWizard","Bristol","22:31","Playing Tetris"),
 ("8bitBaz","Manchester","21:47","On The Wall"),
 ("StrongARM","Dublin IE","20:12","Posting netmail"),
 ("DemoScener","Oslo NO","19:03","New user!"),
 ("Toaster","-- console --","18:00","Sysop"),
]
y=5
for i,(h,loc,when,doing) in enumerate(callers):
    c = 11 if doing=="Sysop" else (10 if doing=="New user!" else 15)
    s.putc(6-2,y,0x07,3,0)
    s.put(6,y,h,c,0); s.put(24,y,loc,7,0); s.put(46,y,when,14,0); s.put(60,y,doing,7,0)
    y+=1
s.put(6,y+2,"You are caller",6,0); s.put(21,y+2,"#48,015",11,0)
s.put(35,y+2,"since 1994",8,0)
s.center(21,"-- press ENTER for the main menu --",8,0)
save(s,"lastcallers")

# ============================ ONE-LINERS / THE WALL ============================
s=Screen()
chrome(s,"The Wall  -  One-liners", STAT, "[A]dd  [ENTER] skip ")
s.center(3,"Scrawl left by callers passing through",6,0)
lines=[
 ("MegaByte","Long live the StrongARM!"),
 ("PiWizard","26-bit or bust."),
 ("8bitBaz","My other computer is a BBC Micro."),
 ("DemoScener","Greets to everyone on RetroNet o/"),
 ("AcornArthur","Does anyone still have the PD disk 42?"),
 ("StrongARM","Toast: it's not just for breakfast."),
]
y=6
for who,txt in lines:
    s.putc(8,y,0x13,3,0)   # double-! looks like graffiti mark; 0x13 = !!
    s.put(10,y,'"'+txt+'"',15,0)
    s.put(12+len(txt)+2,y,"- "+who,6,0)
    y+=2
for x in range(6,COLS-5): s.putc(x,19,DK,3,0)   # shaded wall base
for x in range(6,COLS-5): s.putc(x,20,MED,3,0)
s.center(21,"[A] add your own one-liner   "+chr(BULLET)+"   [ENTER] to move on",8,0)
save(s,"oneliners")

# ============================ NEW USER WELCOME ============================
s=Screen()
chrome(s,"New User Registration", chr(TRI)+" Line 1", "[ENTER] begin  [ESC] cancel ")
s.center(3,"Welcome, first-time caller!",11,0)
for x in range(24,56): s.putc(x,4,S_H,6,0)
lines=[
 (7,"You've reached The Yellow Toaster - a friendly retro BBS.",7),
 (9,"Setting up an account takes about a minute. We'll ask for:",7),
 (11,"a handle (your BBS name)",7),
 (12,"a password",7),
 (13,"your real name (kept private)",7),
 (14,"an email address (optional)",7),
]
for y,t,c in lines:
    if y>=11 and y<=14:
        s.putc(12,y,BULLET,11,0); s.put(14,y,t,7,0)
    else:
        s.center(y,t,c,0)
for x in range(10,70): s.putc(x,17,S_H,6,0)
s.center(18,"House rules: be civil, no warez, keep The Wall friendly.",3,0)
s.center(20,"Answer N at the final prompt and nothing is saved.",8,0)
s.center(21,"Press ENTER to begin, or ESC to log on to an existing account.",14,0)
save(s,"newuser")

# ============================ GOODBYE / LOG OFF ============================
s=Screen()
for x in range(COLS): s.putc(x,0,FULL,3,0)
s.box(0,1,COLS,ROWS-2,6,0,True); s.putc(0,1,D_TL,14,0); s.putc(COLS-1,1,D_TR,14,0)
# big THANKS wordmark reuse via simple blocks
s.center(4,"7 3 !",3,0)   # "73!" ham/BBS sign-off
s.center(6,"Thanks for calling",15,0)
s.center(7,"THE YELLOW TOASTER",11,0)
for x in range(26,54): s.putc(x,9,MED,3,0)
# call summary panel
s.box(24,11,32,8,6,0,False)
s.put(26,11,chr(D_RT)+" This call "+chr(D_LT),14,0)
rows=[("Time on","00:17:42"),("Downloads","2 files"),("Posts made","3"),("Calls total","1,024")]
for i,(k,v) in enumerate(rows):
    s.put(27,13+i,k,7,0); s.put(45,13+i,v,11,0)
s.center(20,"Hang up when ready -- carrier will drop shortly.",8,0)
s.center(21,"See you next time o/",6,0)
s.fillrow(ROWS-1,0x20,15,4)
s.put(1,ROWS-1,chr(TRI)+" NO CARRIER",14,4)
_gr="The Yellow Toaster"
s.put(COLS-len(_gr)-1,ROWS-1,_gr,15,4)
save(s,"goodbye")

print("all screens generated")
