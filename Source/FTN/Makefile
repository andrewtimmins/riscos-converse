# Make file for FTN Mailer

COMPONENT 	= FTN
OBJS        = debug timer mailer binkp queue
LIBS        = C:Desk.o.Desk TCPIPLibs:o.Socklib TCPIPLibs:o.Inetlib OSLib:o.OSLib32
CFLAGS      = -c -depend !Depend -I,C:,TCPIPLibs: -apcs 3/32bit -Wcdp -throwback -fan 
OBJASMFLAGS = -throwback -NoCache -depend !Depend
include CApp
