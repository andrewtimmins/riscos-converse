# Make file for LineTask

COMPONENT   = Line
OBJS        = ansiterm chat crc debug door_arcbbs door_native door_riscbbs filebase main messagebase pipes script transfer xmodem
LIBS        = C:Desk.o.Desk TCPIPLibs:o.Socklib TCPIPLibs:o.Inetlib OSLib:o.OSLib32
CFLAGS      = -c -depend !Depend -I,C:,TCPIPLibs: -apcs 3/32bit -Wcdp -throwback -fan
OBJASMFLAGS = -throwback -NoCache -depend !Depend
include CApp

clean::
	${WIPE} ${INSTAPP} ${WFLAGS}

# Dynamic dependencies:
