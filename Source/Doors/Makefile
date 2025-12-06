# Makefile for ConverseDoors

COMPONENT   = Doors
OBJS        = debug doors
LIBS        = OSLib:o.OSLib32
CMHGDEPENDS = doors
CFLAGS      = -c -depend !Depend -I,C: -apcs 3/32bit -Wcdp -throwback -fan
OBJASMFLAGS = -throwback -NoCache -depend !Depend
CUSTOMRES   = no

include CModule

# Dynamic dependencies:
o.debug:	c.debug
o.debug:	C:h.kernel
o.debug:	C:h.swis
o.debug:	h.debug
o.doors:	c.doors
o.doors:	C:h.kernel
o.doors:	C:h.swis
o.doors:	h.doorshdr
o.doors:	h.doors
o.doors:	C:h.kernel
o.doors:	h.debug
h.DoorsHdr:	cmhg.DoorsHdr
o.DoorsHdr:	cmhg.DoorsHdr
