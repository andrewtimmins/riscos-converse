# Make file for LineTask

COMPONENT   = Line
OBJS        = main script
LIBS        = C:Desk.o.Desk TCPIPLibs:o.Socklib TCPIPLibs:o.Inetlib OSLib:o.OSLib32
CFLAGS      = -c -depend !Depend -I,C:,TCPIPLibs: -apcs 3/32bit -Wcdp -throwback -fan 
OBJASMFLAGS = -throwback -NoCache -depend !Depend
include CApp

clean::
	${WIPE} ${INSTAPP} ${WFLAGS}

# Dynamic dependencies:
o.main:	c.main
o.main:	C:h.kernel
o.main:	C:h.swis
o.main:	C:Desk.h.Core
o.main:	C:h.kernel
o.main:	C:Desk.h.Event
o.main:	C:Desk.h.Wimp
o.main:	C:Desk.h.EventMsg
o.main:	C:Desk.h.Handler
o.main:	C:Desk.h.Msgs
o.main:	C:Desk.h.Resource
o.main:	C:Desk.h.Sprite
o.main:	C:Desk.h.Coord
o.main:	C:Desk.h.Core
o.main:	C:Desk.h.Screen
o.main:	C:Desk.h.Template
o.main:	C:Desk.h.LinkList
o.main:	C:Desk.h.Window
o.main:	C:Desk.h.WimpSWIs
o.main:	C:Desk.h.Error2
o.main:	C:Desk.h.Error
o.main:	C:Desk.h.JumpRaw
o.main:	C:Desk.h.Debug
o.main:	C:Desk.h.Pointer
o.main:	C:Desk.h.Icon
o.main:	C:Desk.h.DragASpr
o.main:	C:Desk.h.WimpSWIs
o.main:	h.script
o.script:	c.script
o.script:	h.script
