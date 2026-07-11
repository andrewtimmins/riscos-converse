#!/usr/bin/env python3
"""Generate an 8x16 CP437 bitmap font for the Converse terminal emulator.

Authentic IBM VGA 8x16 glyphs are lifted from the host's Lat15-VGA16 console
font (PSF) and re-ordered into CP437 layout via Python's cp437 codec plus the
PSF's own Unicode table. The CP437 control-code graphics (0x00-0x1F and 0x7F),
which Python's codec treats as C0 controls and which the PSF does not carry,
fall back to row-doubling the existing 8x8 Converse font so no cell is blank.

Output format (matches the extended ansiterm loader):
    4096 bytes = 256 chars x 16 rows x 1 byte   (8 px/row, MSB = leftmost pixel)

Run with no args for a dry-run coverage report; add --write to emit the file.
"""
import gzip, struct, sys, os

PSF  = "/usr/share/consolefonts/Lat15-VGA16.psf.gz"
OLD8 = "/projects/riscos-converse/!Converse/Resources/Font,ffd"   # 4bpp 8x8
OUT  = "/projects/riscos-converse/!Converse/Resources/Font,ffd"
BAK  = "/projects/riscos-converse/!Converse/Resources/Font8x8,ffd"

def load_psf(path):
    """Return (glyphs[list of bytes], height, unicode_map{cp:index})."""
    data = gzip.open(path, "rb").read()
    uni = {}
    if data[0] == 0x36 and data[1] == 0x04:            # PSF1
        mode, charsize = data[2], data[3]
        count = 512 if (mode & 0x01) else 256
        base = 4
        glyphs = [data[base + i*charsize: base + (i+1)*charsize] for i in range(count)]
        height = charsize
        rest = data[base + count*charsize:]
        if mode & 0x06:                                 # has unicode table
            i = 0; g = 0
            while g < count and i + 1 < len(rest) + 2:
                # read uint16 entries until 0xFFFF terminator
                while i + 1 < len(rest):
                    v = rest[i] | (rest[i+1] << 8); i += 2
                    if v == 0xFFFF:
                        break
                    if v != 0xFFFE and v not in uni:
                        uni[v] = g
                g += 1
    else:                                               # PSF2
        assert data[:4] == b"\x72\xb5\x4a\x86", "unrecognised font magic"
        (ver, hdr, flags, length, charsize, height, width) = struct.unpack("<IIIIIII", data[4:32])
        glyphs = [data[hdr + i*charsize: hdr + (i+1)*charsize] for i in range(length)]
        rest = data[hdr + length*charsize:]
        count = length
        if flags & 0x01:
            i = 0; g = 0
            while g < count and i < len(rest):
                start = i
                while i < len(rest) and rest[i] != 0xFF:
                    i += 1
                seq = rest[start:i]; i += 1              # skip 0xFF
                # decode utf-8, treat 0xFE as separator between multi-char seqs
                for part in seq.split(b"\xfe"):
                    if part:
                        try:
                            for chch in part.decode("utf-8"):
                                uni.setdefault(ord(chch), g)
                        except UnicodeDecodeError:
                            pass
                g += 1
    return glyphs, height, uni

def load_old8_1bpp():
    """Read the 4bpp 8x8 font and collapse to 1bpp: 256 x 8 bytes."""
    raw = open(OLD8, "rb").read()
    out = bytearray(256 * 8)
    for ch in range(256):
        for row in range(8):
            so = ch*32 + row*4
            m = 0
            if raw[so+0] & 0x0F: m |= 0x80
            if raw[so+0] & 0xF0: m |= 0x40
            if raw[so+1] & 0x0F: m |= 0x20
            if raw[so+1] & 0xF0: m |= 0x10
            if raw[so+2] & 0x0F: m |= 0x08
            if raw[so+2] & 0xF0: m |= 0x04
            if raw[so+3] & 0x0F: m |= 0x02
            if raw[so+3] & 0xF0: m |= 0x01
            out[ch*8 + row] = m
    return out

def glyph_ascii(g16):
    return "\n".join("".join("#" if (g16[r] & (0x80 >> c)) else "." for c in range(8)) for r in range(16))

def main():
    glyphs, height, uni = load_psf(PSF)
    if height != 16:
        print("WARN: PSF height is %d, expected 16" % height)
    old8 = load_old8_1bpp()

    out = bytearray(256 * 16)
    authentic = 0; fallback = 0; fb_codes = []
    for c in range(256):
        u = None
        if 0x20 <= c != 0x7F:
            try:
                u = ord(bytes([c]).decode("cp437"))
            except Exception:
                u = None
        gi = uni.get(u) if u is not None else None
        if gi is not None:
            g = glyphs[gi][:16]
            out[c*16:c*16+16] = g + bytes(16 - len(g))
            authentic += 1
        else:
            # row-double the 8x8 glyph
            for row in range(8):
                b = old8[c*8 + row]
                out[c*16 + row*2]     = b
                out[c*16 + row*2 + 1] = b
            fallback += 1
            fb_codes.append(c)

    key = {0x2500:"box-h", 0x2502:"box-v", 0x250C:"box-corner",
           0x2588:"full-block", 0x2591:"light-shade", 0x2593:"dark-shade",
           0x263A:"smiley", 0x2660:"spade"}
    print("PSF: %s  height=%d  glyphs=%d  unicode-entries=%d" % (PSF, height, len(glyphs), len(uni)))
    print("authentic VGA glyphs: %d   fallback (8x8 doubled): %d" % (authentic, fallback))
    print("critical ANSI-art glyphs:")
    for u, name in key.items():
        print("   %-12s U+%04X : %s" % (name, u, "AUTHENTIC" if u in uni else "fallback"))
    print("fallback CP437 codes:", " ".join("%02X" % c for c in fb_codes))
    print()
    for c in (0x41, 0x67, 0xB1, 0xC9, 0xDB):
        print("--- CP437 0x%02X ---" % c)
        print(glyph_ascii(out[c*16:c*16+16]))
        print()

    if "--write" in sys.argv:
        if os.path.exists(OUT) and not os.path.exists(BAK):
            os.rename(OUT, BAK)
            open(OUT, "wb").write(bytes(out))   # rename moved old; write new
        else:
            open(OUT, "wb").write(bytes(out))
        print("WROTE %d bytes -> %s   (8x8 backup: %s)" % (len(out), OUT, BAK))
    else:
        print("dry run - re-run with --write to emit the font")

if __name__ == "__main__":
    main()
