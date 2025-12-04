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
