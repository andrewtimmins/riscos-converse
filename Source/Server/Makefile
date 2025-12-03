# Make file for DoorSrv

COMPONENT 	= Server
OBJS        = config debug timer main
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
o.timer:	c.timer
o.timer:	C:oslib.h.os
o.timer:	C:oslib.h.types
o.timer:	C:oslib.h.oscore32
o.timer:	C:oslib.h.osf32
o.config:	c.config
o.config:	C:h.kernel
o.config:	C:h.swis
o.config:	h.config
o.config:	h.debug
o.main:	c.main
o.main:	C:h.kernel
o.main:	C:h.swis
o.main:	C:Desk.h.Core
o.main:	C:h.kernel
o.main:	C:Desk.h.Event
o.main:	C:Desk.h.Wimp
o.main:	C:Desk.h.EventMsg
o.main:	C:Desk.h.Resource
o.main:	C:Desk.h.Sprite
o.main:	C:Desk.h.Coord
o.main:	C:Desk.h.Core
o.main:	C:Desk.h.Handler
o.main:	C:Desk.h.File
o.main:	C:Desk.h.SWI
o.main:	C:Desk.h.Error2
o.main:	C:Desk.h.Error
o.main:	C:Desk.h.JumpRaw
o.main:	C:Desk.h.Debug
o.main:	C:Desk.h.Icon
o.main:	C:Desk.h.DragASpr
o.main:	C:Desk.h.Menu
o.main:	C:Desk.h.Screen
o.main:	C:Desk.h.WimpSWIs
o.main:	C:Desk.h.Msgs
o.main:	C:Desk.h.Template
o.main:	C:Desk.h.LinkList
o.main:	C:Desk.h.Dialog
o.main:	C:Desk.h.Window
o.main:	C:Desk.h.Pointer
o.main:	C:Desk.h.Dialog2
o.main:	C:Desk.h.Sound
o.main:	TCPIPLibs:sys.h.types
o.main:	TCPIPLibs:sys.h.cdefs
o.main:	TCPIPLibs:machine.h.endian
o.main:	TCPIPLibs:machine.h.ansi
o.main:	TCPIPLibs:machine.h.types
o.main:	TCPIPLibs:sys.h.socket
o.main:	TCPIPLibs:sys.h.cdefs
o.main:	TCPIPLibs:h.socklib
o.main:	TCPIPLibs:sys.h.types
o.main:	TCPIPLibs:sys.h.socket
o.main:	TCPIPLibs:sys.h.stat
o.main:	TCPIPLibs:sys.h.time
o.main:	TCPIPLibs:sys.h.types
o.main:	TCPIPLibs:sys.h.cdefs
o.main:	TCPIPLibs:sys.h.cdefs
o.main:	TCPIPLibs:sys.h.time
o.main:	TCPIPLibs:sys.h.uio
o.main:	TCPIPLibs:sys.h.cdefs
o.main:	C:h.kernel
o.main:	TCPIPLibs:h.inetlib
o.main:	TCPIPLibs:sys.h.types
o.main:	TCPIPLibs:netinet.h.in
o.main:	TCPIPLibs:netinet.h.in
o.main:	TCPIPLibs:sys.h.ioctl
o.main:	TCPIPLibs:sys.h.ttycom
o.main:	TCPIPLibs:sys.h.ioccom
o.main:	TCPIPLibs:sys.h.ioccom
o.main:	TCPIPLibs:sys.h.filio
o.main:	TCPIPLibs:sys.h.ioccom
o.main:	TCPIPLibs:sys.h.sockio
o.main:	TCPIPLibs:sys.h.ioccom
o.main:	TCPIPLibs:sys.h.cdefs
o.main:	TCPIPLibs:sys.h.errno
o.main:	C:h.kernel
o.main:	TCPIPLibs:h.netdb
o.main:	TCPIPLibs:sys.h.cdefs
o.main:	h.main
o.main:	C:Desk.h.Core
o.main:	C:Desk.h.Menu
o.main:	C:Desk.h.Dialog
o.main:	C:Desk.h.Dialog2
o.main:	h.iconnames
o.main:	h.ansi
o.main:	h.debug
o.main:	h.config
