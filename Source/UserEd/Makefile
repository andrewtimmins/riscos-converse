# Make file for UserEd

COMPONENT 	= UserEd
OBJS        = debug version main
LIBS        = C:Desk.o.Desk OSLib:o.OSLib32
CFLAGS      = -c -depend !Depend -I,C: -apcs 3/32bit -Wcdp -throwback -fan 
OBJASMFLAGS = -throwback -NoCache -depend !Depend
include CApp

clean::
	${WIPE} ${INSTAPP} ${WFLAGS}

# Dynamic dependencies:
