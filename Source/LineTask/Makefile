# Make file for LineTask

COMPONENT   = Line
OBJS        = debug filebase main script
LIBS        = C:Desk.o.Desk TCPIPLibs:o.Socklib TCPIPLibs:o.Inetlib OSLib:o.OSLib32
CFLAGS      = -c -depend !Depend -I,C:,TCPIPLibs: -apcs 3/32bit -Wcdp -throwback -fan
OBJASMFLAGS = -throwback -NoCache -depend !Depend
include CApp

clean::
	${WIPE} ${INSTAPP} ${WFLAGS}

# Dynamic dependencies:
o.debug:	c.debug
o.debug:	C:oslib.h.report
o.debug:	C:oslib.h.types
o.debug:	C:oslib.h.os
o.debug:	C:oslib.h.oscore32
o.debug:	C:oslib.h.osf32
o.debug:	C:oslib.h.wimp
o.debug:	C:oslib.h.osspriteop
o.debug:	C:oslib.h.font
o.debug:	C:oslib.h.wimp32
o.debug:	h.debug
o.filebase:	c.filebase
o.filebase:	C:h.kernel
o.filebase:	C:h.swis
o.filebase:	h.filebase
o.filebase:	h.debug
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
o.main:	h.filebase
o.main:	h.debug
o.script:	c.script
o.script:	h.script
o.script:	h.filebase
