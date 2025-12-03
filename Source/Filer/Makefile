# Makefile for Filer

COMPONENT   = Filer
OBJS        = debug filer userdb logging misc encrypt filebase messagebase stats
LIBS        = C:Desk.o.Desk_M OSLib:o.OSLib32
CMHGDEPENDS = filer
CFLAGS      = -c -depend !Depend -I,C: -apcs 3/32bit -Wcdp -throwback -fan
OBJASMFLAGS = -throwback -NoCache -depend !Depend
CUSTOMRES   = no

include CModule

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
o.filer:	c.filer
o.filer:	C:h.kernel
o.filer:	h.filerhdr
o.filer:	h.structs
o.filer:	h.filer
o.filer:	C:h.kernel
o.filer:	h.logging
o.filer:	h.structs
o.filer:	h.userdb
o.filer:	h.structs
o.filer:	h.filebase
o.filer:	C:h.kernel
o.filer:	h.structs
o.filer:	h.messagebase
o.filer:	C:h.kernel
o.filer:	h.structs
o.filer:	h.stats
h.FilerHdr:	cmhg.filerHdr
o.userdb:	c.userdb
o.userdb:	h.structs
o.userdb:	h.userdb
o.userdb:	h.structs
o.userdb:	h.logging
o.userdb:	h.structs
o.userdb:	h.misc
o.userdb:	h.encrypt
o.userdb:	h.debug
o.logging:	c.logging
o.logging:	h.logging
o.logging:	h.structs
o.logging:	h.stats
o.logging:	h.debug
o.misc:	c.misc
o.misc:	h.debug
o.misc:	h.misc
o.encrypt:	c.encrypt
o.encrypt:	h.encrypt
o.filebase:	c.filebase
o.filebase:	C:h.kernel
o.filebase:	C:h.swis
o.filebase:	h.debug
o.filebase:	h.logging
o.filebase:	h.structs
o.filebase:	h.misc
o.filebase:	h.filebase
o.filebase:	C:h.kernel
o.filebase:	h.structs
o.messagebase:	c.messagebase
o.messagebase:	C:h.kernel
o.messagebase:	C:h.swis
o.messagebase:	h.debug
o.messagebase:	h.logging
o.messagebase:	h.structs
o.messagebase:	h.misc
o.messagebase:	h.messagebase
o.messagebase:	C:h.kernel
o.messagebase:	h.structs
o.stats:	c.stats
o.stats:	h.stats
o.stats:	h.debug
o.FilerHdr:	cmhg.filerHdr
