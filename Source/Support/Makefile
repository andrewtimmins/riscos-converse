# Makefile for Support

COMPONENT   = Support
OBJS        = config linestate support
LIBS        = OSLib:o.OSLib32
CMHGDEPENDS = support
CFLAGS      = -c -depend !Depend -I,C: -apcs 3/32bit -Wcdp -throwback -fan
OBJASMFLAGS = -throwback -NoCache -depend !Depend
CUSTOMRES   = no

include CModule
