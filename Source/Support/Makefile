# Makefile for Support

COMPONENT   = Support
OBJS        = config debug filebaseconfig ftnconfig lineconfig linestate msgbaseconfig support
LIBS        = OSLib:o.OSLib32
CMHGDEPENDS = support
CFLAGS      = -c -depend !Depend -I,C: -apcs 3/32bit -Wcdp -throwback -fan
OBJASMFLAGS = -throwback -NoCache -depend !Depend
CUSTOMRES   = no

include CModule

# Dynamic dependencies:
o.config:	c.config
o.config:	h.config
o.config:	C:h.kernel
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
o.filebaseconfig:	c.filebaseconfig
o.filebaseconfig:	h.filebaseconfig
o.filebaseconfig:	C:h.kernel
o.lineconfig:	c.lineconfig
o.lineconfig:	C:h.kernel
o.lineconfig:	C:h.swis
o.lineconfig:	h.lineconfig
o.lineconfig:	C:h.kernel
o.lineconfig:	h.debug
o.linestate:	c.linestate
o.linestate:	h.linestate
o.linestate:	C:h.kernel
o.msgbaseconfig:	c.msgbaseconfig
o.msgbaseconfig:	h.msgbaseconfig
o.msgbaseconfig:	C:h.kernel
h.SupportHdr:	cmhg.SupportHdr
o.SupportHdr:	cmhg.SupportHdr
o.ftnconfig:	c.ftnconfig
o.ftnconfig:	h.ftnconfig
o.ftnconfig:	C:h.kernel
o.support:	c.support
o.support:	C:h.kernel
o.support:	h.supporthdr
o.support:	h.support
o.support:	C:h.kernel
o.support:	h.config
o.support:	C:h.kernel
o.support:	h.linestate
o.support:	C:h.kernel
o.support:	h.lineconfig
o.support:	C:h.kernel
o.support:	h.msgbaseconfig
o.support:	C:h.kernel
o.support:	h.filebaseconfig
o.support:	C:h.kernel
o.support:	h.ftnconfig
o.support:	C:h.kernel
