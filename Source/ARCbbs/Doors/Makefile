# Makefile for ARCbbsDoors Emulator

COMPONENT   = ARCbbs
OBJS        = debug arcbbs buffer
LIBS        = OSLib:o.OSLib32
CMHGDEPENDS = arcbbs
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
o.arcbbs:	c.arcbbs
o.arcbbs:	C:h.kernel
o.arcbbs:	h.arcbbshdr
o.arcbbs:	h.arcbbs
o.arcbbs:	C:h.kernel
o.arcbbs:	h.buffer
o.arcbbs:	C:h.kernel
o.arcbbs:	h.arcbbs
o.arcbbs:	h.debug
h.ARCbbsHdr:	cmhg.ARCbbsHdr
o.buffer:	c.buffer
o.buffer:	h.buffer
o.buffer:	C:h.kernel
o.buffer:	h.arcbbs
o.buffer:	C:h.kernel
o.buffer:	h.debug
o.ARCbbsHdr:	cmhg.ARCbbsHdr
