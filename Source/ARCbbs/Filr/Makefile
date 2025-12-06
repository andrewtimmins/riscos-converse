# ARCbbsFiler Emulator Module Makefile
#
# Provides compatibility with legacy ARCbbs doors

CC = cc
CMHG = cmhg
LD = link
RM = remove
WIPE = wipe

CFLAGS = -c -depend !Depend -I,C: -throwback -fah -apcs 3/32bit
CMHGFLAGS = -depend !Depend -throwback -p
LDFLAGS = -rmf -o

LIBS = C:o.stubs

OBJS = o.filer o.debug o.filerHdr

TARGET = rm.ARCbbsFlr

all: $(TARGET)
	@echo ARCbbsFiler module built

$(TARGET): $(OBJS)
	$(LD) $(LDFLAGS) $@ $(OBJS) $(LIBS)

o.filer: c.filer h.filer h.debug
	$(CC) $(CFLAGS) -o $@ c.filer

o.debug: c.debug h.debug
	$(CC) $(CFLAGS) -o $@ c.debug

o.filerHdr: cmhg.filerHdr
	$(CMHG) $(CMHGFLAGS) -o $@ cmhg.filerHdr

clean:
	$(WIPE) o.* ~CF~V
	$(WIPE) rm.* ~CF~V
	@echo Cleaned

# Dynamic dependencies:
o.debug:	c.debug
o.debug:	C:h.kernel
o.debug:	C:h.swis
o.debug:	h.debug
o.filerHdr:	cmhg.filerHdr
o.filer:	c.filer
o.filer:	C:h.kernel
o.filer:	C:h.swis
o.filer:	h.filer
o.filer:	C:h.kernel
o.filer:	h.debug
