# Makefile for Pipes

COMPONENT   = Pipes
OBJS        = debug pipes
LIBS        = OSLib:o.OSLib32
CMHGDEPENDS = pipes
CFLAGS      = -c -depend !Depend -I,C: -apcs 3/32bit -Wcdp -throwback -fan
OBJASMFLAGS = -throwback -NoCache -depend !Depend
CUSTOMRES   = no

include CModule
