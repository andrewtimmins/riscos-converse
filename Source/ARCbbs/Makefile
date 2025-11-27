# Makefile for ARCbbsDoors Emulator

COMPONENT   = ARCbbs
OBJS        = debug arcbbs buffer
LIBS        = OSLib:o.OSLib32
CMHGDEPENDS = arcbbs
CFLAGS      = -c -depend !Depend -I,C: -apcs 3/32bit -Wcdp -throwback -fan
OBJASMFLAGS = -throwback -NoCache -depend !Depend
CUSTOMRES   = no

include CModule
