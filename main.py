#!/usr/bin/env python3
"""Sum up 24 November's world news in one image.

Draws a dense broadsheet newspaper front page for Tuesday 24 November 2026
entirely in code: a hand-designed stroke font, flat pictogram panels, a
dotted world map and the day's stories as numbered cards and briefs.
Standard library only. Writes /output/entry.png (1024x1024, deterministic).
"""

import math
import os
import struct
import zlib

SS = 2                      # supersampling factor (internal render scale)
FW, FH = 1024, 1024         # final image size
W, H = FW * SS, FH * SS     # internal canvas size

# ---------------------------------------------------------------- palette
PAPER = (247, 243, 233)
PAPER_D = (238, 231, 216)
INK = (18, 30, 60)
NAVY = (24, 44, 92)
NAVY_D = (13, 24, 54)
RED = (178, 32, 44)
RED_D = (140, 22, 34)
GOLD = (190, 138, 52)
BLUE = (70, 102, 158)
BLUE_L = (168, 188, 222)
PALE = (219, 227, 240)
PALE_S = (238, 229, 203)
PALE_G = (224, 226, 220)
GRAY = (104, 106, 112)
GRAY_L = (172, 170, 162)
GREEN = (22, 122, 80)
TEAL = (28, 110, 120)
SKIN = (222, 184, 148)

# ---------------------------------------------------------------- canvas
BUF = bytearray(bytes(PAPER) * (W * H))


def _put(x, y, c):
    i = (y * W + x) * 3
    BUF[i] = c[0]
    BUF[i + 1] = c[1]
    BUF[i + 2] = c[2]


def fill_rect(x, y, w, h, c):
    """Filled rectangle in final-image coordinates (floats ok)."""
    x0 = max(0, int(round(x * SS)))
    y0 = max(0, int(round(y * SS)))
    x1 = min(W, int(round((x + w) * SS)))
    y1 = min(H, int(round((y + h) * SS)))
    if x1 <= x0 or y1 <= y0:
        return
    row = bytes(c) * (x1 - x0)
    n = len(row)
    for yy in range(y0, y1):
        s = (yy * W + x0) * 3
        BUF[s:s + n] = row


def fill_circle(cx, cy, r, c):
    cx, cy, r = cx * SS, cy * SS, r * SS
    y0 = max(0, int(cy - r - 1))
    y1 = min(H, int(cy + r + 2))
    cb = bytes(c)
    for yy in range(y0, y1):
        dy = yy - cy
        dx = math.sqrt(max(0.0, r * r - dy * dy))
        x0 = max(0, int(cx - dx))
        x1 = min(W, int(cx + dx) + 1)
        if x1 <= x0:
            continue
        s = (yy * W + x0) * 3
        BUF[s:s + (x1 - x0) * 3] = cb * (x1 - x0)


def fill_poly(points, c):
    """Scanline polygon fill; points in final-image coordinates."""
    pts = [(x * SS, y * SS) for x, y in points]
    ys = [p[1] for p in pts]
    y0 = max(0, int(min(ys)))
    y1 = min(H, int(max(ys)) + 1)
    cb = bytes(c)
    n = len(pts)
    for yy in range(y0, y1):
        yc = yy + 0.5
        xs = []
        for i in range(n):
            x1, yy1 = pts[i]
            x2, yy2 = pts[(i + 1) % n]
            if (yy1 <= yc < yy2) or (yy2 <= yc < yy1):
                xs.append(x1 + (yc - yy1) * (x2 - x1) / (yy2 - yy1))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            xa = max(0, int(xs[i]))
            xb = min(W, int(xs[i + 1]) + 1)
            if xb <= xa:
                continue
            s = (yy * W + xa) * 3
            BUF[s:s + (xb - xa) * 3] = cb * (xb - xa)


def _stamp(cx, cy, r, c):
    """Disc stamp in internal coordinates."""
    y0 = max(0, int(cy - r - 1))
    y1 = min(H, int(cy + r + 2))
    cb = bytes(c)
    for yy in range(y0, y1):
        dy = yy - cy
        dx = math.sqrt(max(0.0, r * r - dy * dy))
        x0 = max(0, int(cx - dx))
        x1 = min(W, int(cx + dx) + 1)
        if x1 <= x0:
            continue
        s = (yy * W + x0) * 3
        BUF[s:s + (x1 - x0) * 3] = cb * (x1 - x0)


def stroke_line(x1, y1, x2, y2, w, c):
    """Thick line in final-image coordinates."""
    ax, ay, bx, by = x1 * SS, y1 * SS, x2 * SS, y2 * SS
    r = max(0.55, w * SS * 0.5)
    dist = math.hypot(bx - ax, by - ay)
    steps = max(1, int(dist / max(0.6, r * 0.6)))
    for i in range(steps + 1):
        t = i / steps
        _stamp(ax + (bx - ax) * t, ay + (by - ay) * t, r, c)


def stroke_poly(points, w, c, close=False):
    pts = list(points)
    if close and pts:
        pts.append(pts[0])
    for i in range(len(pts) - 1):
        stroke_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], w, c)


def rect_outline(x, y, w, h, lw, c):
    fill_rect(x, y, w, lw, c)
    fill_rect(x, y + h - lw, w, lw, c)
    fill_rect(x, y, lw, h, c)
    fill_rect(x + w - lw, y, lw, h, c)


# ---------------------------------------------------------------- png out
def save_png(path):
    out = bytearray(FW * FH * 3)
    for oy in range(FH):
        for ox in range(FW):
            acc0 = acc1 = acc2 = 0
            base = ((oy * SS) * W + ox * SS) * 3
            for dy in range(SS):
                row = base + dy * W * 3
                for dx in range(SS):
                    i = row + dx * 3
                    acc0 += BUF[i]
                    acc1 += BUF[i + 1]
                    acc2 += BUF[i + 2]
            n = SS * SS
            o = (oy * FW + ox) * 3
            out[o] = acc0 // n
            out[o + 1] = acc1 // n
            out[o + 2] = acc2 // n
    raw = bytearray()
    stride = FW * 3
    for yy in range(FH):
        raw.append(0)
        raw += out[yy * stride:(yy + 1) * stride]

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))

    png = (b"\x89PNG\r\n\x1a\n" +
           chunk(b"IHDR", struct.pack(">IIBBBBB", FW, FH, 8, 2, 0, 0, 0)) +
           chunk(b"IDAT", zlib.compress(bytes(raw), 9)) +
           chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(png)
    return len(png)


# ---------------------------------------------------------------- font
# Hand-designed stroke font. Grid: baseline y=4, x-height y=11, cap y=14,
# descender y=0. Each glyph: (advance, strokes); a stroke is a string of
# coordinate pairs, each coordinate one char: 0-9 then a=10 .. i=18.
_C2V = {c: i for i, c in enumerate("0123456789abcdefghi")}

FONT = {
    "A": (10, "145e94 3878"),
    "B": (10, "242e 2e6e8c6a2a 2a7a977424"),
    "C": (10, "9c6e3d19356496"),
    "D": (10, "242e 2e6e9a6424"),
    "E": (9, "8e2e2484 2969"),
    "F": (9, "8e2e24 2969"),
    "G": (10, "9c6e3d193584 68689894"),
    "H": (10, "242e 848e 2a8a"),
    "I": (5, "242e 0e4e 0404"),
    "J": (8, "7e76652416"),
    "K": (10, "242e 8e28 3984"),
    "L": (9, "2e2484"),
    "M": (12, "141e67beb4"),
    "N": (10, "242e848e"),
    "O": (10, "5e8d99855425192d5e"),
    "P": (9, "242e 2e6e8c6929"),
    "Q": (10, "5e8d99855425192d5e 66a2"),
    "R": (10, "242e 2e6e8c6929 5994"),
    "S": (9, "8c5e2c3977855426"),
    "T": (10, "1e9e 5e54"),
    "U": (10, "2e264664868e"),
    "V": (10, "1e549e"),
    "W": (13, "1e346a94ce"),
    "X": (9, "2e84 248e"),
    "Y": (10, "1e599e 5954"),
    "Z": (9, "2e8e2484"),
    "a": (8, "795b2b18255475 7b74"),
    "b": (8, "242e 274b6a776424"),
    "c": (7, "795b2a17255475"),
    "d": (8, "785b2a17255475 7e74"),
    "e": (8, "1878 785b2b17255475"),
    "f": (5, "5e3e2c24 0a4a"),
    "g": (8, "785b2a17255475 7b725021"),
    "h": (8, "242e 284b6b7974"),
    "i": (4, "2b24 2e2e"),
    "j": (5, "4b422011 4e4e"),
    "k": (7, "242e 6b26 3774"),
    "l": (4, "242e"),
    "m": (12, "2b24 284b5b6964 688babb9b4"),
    "n": (8, "2b24 284b6b7974"),
    "o": (8, "4b6a77645425172a4b"),
    "p": (8, "274b6a776424 2b20"),
    "q": (8, "775b2a17255475 7b70"),
    "r": (6, "2b24 284b6b"),
    "s": (7, "694b293756654425"),
    "t": (6, "3e355445 1a5a"),
    "u": (8, "2b264664767b 7b74"),
    "v": (8, "1b447b"),
    "w": (11, "1b345974ab"),
    "x": (7, "1b64 146b"),
    "y": (8, "1b46 7b462210"),
    "z": (7, "2b6b2464"),
    "ü": (8, "2b264664767b 7b74 2e2e 6e6e"),
    "á": (8, "795b2b18255475 7b74 5d7f"),
    "0": (9, "4e7d89755425192d4e"),
    "1": (6, "3b5e54 2464"),
    "2": (9, "2c4e7d8a2484"),
    "3": (9, "2d5e7c5939 5978754425"),
    "4": (9, "646e1888"),
    "5": (9, "7e3e295a78754425"),
    "6": (9, "7c5e2b17255476795b2a"),
    "7": (9, "2e8e44"),
    "8": (9, "4e6d6b492b2d4e 49787544151849"),
    "9": (9, "896d3e1b285688 8d84"),
    " ": (4, ""),
    ".": (3, "1414"),
    ",": (4, "252411"),
    ":": (3, "1414 1a1a"),
    ";": (4, "2a2a 252411"),
    "'": (3, "2e1a"),
    '"': (5, "1e1a 4e4a"),
    "-": (6, "1858"),
    "–": (6, "1858"),
    "—": (10, "1898"),
    "·": (3, "1818"),
    "•": (4, "2828"),
    "/": (6, "135f"),
    "\\": (6, "1f53"),
    "(": (5, "4e2a2844"),
    ")": (5, "1e3a3814"),
    "%": (11, "3e4c3a2c3e 239f 8896847688"),
    "+": (8, "1878 4b45"),
    "=": (8, "1a7a 1676"),
    "$": (9, "8c5e2c3977855426 5f53"),
    "€": (10, "9c6e3d19356496 1a6a 1767"),
    "£": (9, "7d5e3c362474 1858"),
    "¥": (10, "1e599e 5954 1a9a 1797"),
    "&": (10, "7d5e3c4976 492624548794"),
    "!": (3, "1e17 1414"),
    "?": (8, "2c4e6d7a4846 4444"),
    "*": (7, "3c36 1a58 185a"),
    "#": (9, "333f 636f 1a8a 1787"),
    "°": (5, "2e3f4e3d2e"),
    "<": (7, "6b1865"),
    ">": (7, "1b6815"),
    "[": (5, "4e2e2444"),
    "]": (5, "1e3e3414"),
    "_": (7, "0363"),
    "|": (3, "1f13"),
    "~": (7, "183b5879"),
}


def _decode():
    out = {}
    for ch, (adv, strokes) in FONT.items():
        dec = []
        for st in strokes.split():
            pts = [(_C2V[st[i]], _C2V[st[i + 1]]) for i in range(0, len(st), 2)]
            dec.append(pts)
        out[ch] = (adv, dec)
    return out


GLYPHS = _decode()

_ALIASES = {"’": "'", "‘": "'", "“": '"', "”": '"', "−": "-", "×": "x"}


def _glyph(ch):
    ch = _ALIASES.get(ch, ch)
    return GLYPHS.get(ch)


def text_width(text, size, tracking=0.0):
    sc = size / 18.0
    total = 0.0
    for ch in text:
        g = _glyph(ch)
        total += (g[0] if g else 4) * sc + tracking
    return total - (tracking if text else 0.0)


def draw_text(x, y, text, size, color, bold=False, tracking=0.0,
              align="left", serif=False):
    """Draw text with baseline at y (final-image coordinates)."""
    w = text_width(text, size, tracking)
    if align == "center":
        x -= w / 2.0
    elif align == "right":
        x -= w
    sc = size / 18.0
    sw = size * (0.118 if bold else 0.082)
    sw = max(0.85, sw)
    cx = x
    for ch in text:
        g = _glyph(ch)
        if g is None:
            cx += 4 * sc + tracking
            continue
        adv, strokes = g
        for pts in strokes:
            mapped = [(cx + gx * sc, y - (gy - 4) * sc) for gx, gy in pts]
            if len(mapped) == 1:
                fill_circle(mapped[0][0], mapped[0][1], sw * 0.62, color)
            else:
                stroke_poly(mapped, sw, color)
            if serif and size >= 30 and len(mapped) >= 2:
                for k in (0, -1):
                    gx, gy = pts[k]
                    if gy not in (4, 14):
                        continue
                    x1, y1 = mapped[k]
                    x2, y2 = mapped[1] if k == 0 else mapped[-2]
                    if abs(x2 - x1) < abs(y2 - y1) * 0.45:
                        t = size * 0.085
                        stroke_line(x1 - t, y1, x1 + t, y1, sw * 0.7, color)
        cx += adv * sc + tracking
    return cx


def wrap_text(text, size, maxw, tracking=0.0):
    lines = []
    for para in text.split("\n"):
        words = para.split()
        cur = ""
        for wd in words:
            trial = wd if not cur else cur + " " + wd
            if text_width(trial, size, tracking) <= maxw or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = wd
        lines.append(cur)
    return lines


def fit_lines(text, size, maxw, max_lines, tracking=0.0, min_size=7.0):
    """Shrink size until the wrapped text fits max_lines; return (size, lines)."""
    s = size
    while s > min_size:
        lines = wrap_text(text, s, maxw, tracking)
        if len(lines) <= max_lines:
            return s, lines
        s -= 0.5
    return s, wrap_text(text, s, maxw, tracking)


# ---------------------------------------------------------------- world map
# Dotted world map on an 80x40 equirectangular grid; runs of land cells.
MAP_RUNS = {
    0: [(11, 16), (27, 33), (43, 43), (50, 53), (58, 70), (75, 77)],
    1: [(10, 20), (27, 34), (44, 46), (49, 60), (62, 74)],
    2: [(7, 25), (27, 34), (38, 38), (44, 46), (48, 78)],
    3: [(6, 26), (28, 34), (38, 38), (43, 48), (49, 79)],
    4: [(5, 26), (28, 33), (38, 38), (43, 48), (48, 79)],
    5: [(3, 20), (8, 27), (29, 32), (41, 41), (43, 79)],
    6: [(0, 6), (7, 27), (30, 31), (41, 41), (43, 79)],
    7: [(6, 28), (41, 42), (42, 60), (60, 79), (73, 76)],
    8: [(8, 28), (41, 42), (42, 52), (53, 79), (74, 76)],
    9: [(9, 27), (41, 50), (52, 66), (66, 76), (75, 76)],
    10: [(9, 27), (41, 50), (55, 58), (58, 75), (75, 76)],
    11: [(10, 26), (40, 51), (54, 59), (60, 66), (67, 75)],
    12: [(10, 26), (40, 52), (54, 59), (61, 66), (67, 75), (75, 76)],
    13: [(10, 24), (39, 53), (54, 59), (61, 66), (67, 74)],
    14: [(11, 20), (38, 54), (55, 59), (62, 66), (68, 74), (75, 75)],
    15: [(12, 17), (38, 53), (55, 59), (60, 66), (68, 73)],
    16: [(12, 16), (38, 53), (56, 58), (62, 65), (68, 71), (74, 75)],
    17: [(13, 15), (24, 26), (38, 53), (61, 64), (68, 71), (74, 74)],
    18: [(13, 15), (22, 25), (38, 54), (63, 64), (68, 71), (74, 74)],
    19: [(15, 17), (21, 25), (39, 55), (64, 65), (67, 70), (73, 75)],
    20: [(21, 24), (26, 28), (41, 46), (50, 56), (66, 68), (69, 72), (76, 79)],
    21: [(21, 27), (42, 46), (50, 55), (66, 70), (71, 74), (76, 79)],
    22: [(22, 30), (43, 46), (51, 54), (66, 74), (77, 79)],
    23: [(22, 31), (43, 47), (50, 54), (66, 72), (77, 79)],
    24: [(23, 31), (43, 47), (50, 54), (67, 71), (77, 79)],
    25: [(23, 32), (43, 47), (49, 53), (68, 72), (74, 78)],
    26: [(24, 25), (25, 32), (44, 46), (47, 51), (53, 53), (71, 77)],
    27: [(24, 26), (26, 32), (44, 47), (47, 51), (53, 53), (70, 78)],
    28: [(24, 26), (26, 31), (44, 47), (47, 50), (53, 53), (70, 78)],
    29: [(24, 27), (44, 46), (46, 50), (70, 78)],
    30: [(24, 27), (46, 49), (69, 77)],
    31: [(24, 27), (46, 49), (70, 77)],
    32: [(24, 26), (46, 48), (72, 77), (78, 79)],
    33: [(24, 26), (46, 48), (74, 77), (78, 79)],
    34: [(23, 25), (78, 79)],
    35: [(23, 25), (78, 79)],
    36: [(23, 24), (77, 78)],
    37: [(23, 24), (77, 78)],
    38: [(23, 23)],
    39: [(23, 23)],
}
# pin positions (col, row) for cards 1..12
MAP_PINS = [(43, 8), (48, 7), (44, 14), (50, 18), (63, 17), (68, 12),
            (24, 22), (18, 12), (54, 15), (48, 14), (71, 13), (61, 15)]


def draw_map(x, y, w, h):
    cols, rows = 80, 40
    cw, chh = w / cols, h / rows
    for r, runs in MAP_RUNS.items():
        for a, b in runs:
            for cidx in range(a, b + 1):
                fill_circle(x + (cidx + 0.5) * cw, y + (r + 0.5) * chh,
                            min(cw, chh) * 0.30, BLUE_L)
    for i, (cidx, r) in enumerate(MAP_PINS):
        cx, cy = x + (cidx + 0.5) * cw, y + (r + 0.5) * chh
        fill_circle(cx, cy, 7.6, PAPER)
        fill_circle(cx, cy, 6.4, RED if i % 3 == 0 else NAVY)
        label = str(i + 1)
        tw = text_width(label, 8.6)
        draw_text(cx - tw / 2, cy + 2.6, label, 8.6, PAPER, bold=True)


# ---------------------------------------------------------------- pictograms
def _star(cx, cy, r, c):
    pts = []
    for i in range(8):
        ang = math.pi / 2 + i * math.pi / 4
        rr = r if i % 2 == 0 else r * 0.34
        pts.append((cx + rr * math.cos(ang), cy - rr * math.sin(ang)))
    fill_poly(pts, c)


def illu_nato(x, y, w, h):
    fill_rect(x, y, w, h, NAVY_D)
    cx, cy = x + w * 0.5, y + h * 0.58
    # orbit ellipse
    orb = [(cx + w * 0.44 * math.cos(t), cy + h * 0.30 * math.sin(t))
           for t in [i * 0.35 for i in range(19)]]
    stroke_poly(orb, 1.1, BLUE_L)
    fill_circle(cx, cy + h * 0.16, w * 0.17, BLUE)          # earth
    fill_poly([(cx - w * 0.17, cy + h * 0.10), (cx + w * 0.17, cy + h * 0.10),
               (cx + w * 0.05, cy - h * 0.02), (cx - w * 0.05, cy - h * 0.02)], BLUE_L)
    _star(cx, cy - h * 0.30, w * 0.13, GOLD)                  # alliance star
    # satellite
    sx, sy = cx + w * 0.26, cy - h * 0.34
    fill_rect(sx - 4, sy - 3, 8, 6, PAPER)
    fill_rect(sx - 13, sy - 2, 7, 4, GOLD)
    fill_rect(sx + 6, sy - 2, 7, 4, GOLD)
    stroke_line(sx, sy + 3, cx + 4, cy - 6, 0.9, RED)


def illu_estonia(x, y, w, h):
    fill_rect(x, y, w, h, PALE)
    gy = y + h * 0.82
    stroke_line(x + 4, gy, x + w - 4, gy, 1.4, INK)
    # left pole: Estonian flag
    px1 = x + w * 0.26
    stroke_line(px1, y + 8, px1, gy, 1.8, INK)
    fill_rect(px1, y + 9, 20, 5, BLUE)
    fill_rect(px1, y + 14, 20, 5, INK)
    fill_rect(px1, y + 19, 20, 5, PAPER)
    rect_outline(px1, y + 9, 20, 15, 0.7, GRAY)
    # right pole: plain red flag
    px2 = x + w * 0.68
    stroke_line(px2, y + 8, px2, gy, 1.8, INK)
    fill_poly([(px2, y + 9), (px2 + 19, y + 12), (px2, y + 16)], RED)
    # dashed border between
    for i in range(5):
        yy = y + 12 + i * (h - 24) / 5
        stroke_line(x + w * 0.5, yy, x + w * 0.5, yy + 5, 1.1, RED)
    # warning triangle
    tx, ty = x + w * 0.5, y + h * 0.60
    fill_poly([(tx, ty - 9), (tx - 9, ty + 7), (tx + 9, ty + 7)], GOLD)
    draw_text(tx, ty + 5.5, "!", 13, INK, bold=True, align="center")


def illu_libya(x, y, w, h):
    fill_rect(x, y, w, h, PALE)
    wy = y + h * 0.62
    fill_rect(x, wy, w, h - (wy - y), BLUE)
    for i in range(3):  # waves
        for k in range(4):
            sx = x + 8 + k * 20 + (i * 7) % 9
            stroke_poly([(sx, wy + 8 + i * 9), (sx + 4, wy + 5 + i * 9),
                         (sx + 8, wy + 8 + i * 9)], 1.0, BLUE_L)
    # warship
    hx, hy = x + w * 0.16, wy - 2
    fill_poly([(hx, hy), (hx + 46, hy), (hx + 39, hy + 7), (hx + 5, hy + 7)], NAVY_D)
    fill_rect(hx + 14, hy - 7, 15, 7, NAVY)
    fill_rect(hx + 20, hy - 12, 4, 5, NAVY)
    stroke_line(hx + 34, hy - 2, hx + 45, hy - 8, 1.6, NAVY_D)
    # small drone overhead
    dx, dy = x + w * 0.76, y + h * 0.22
    fill_rect(dx - 3.5, dy - 1.5, 7, 3, INK)
    for ox, oy in ((-6, -3.5), (6, -3.5), (-6, 3.5), (6, 3.5)):
        stroke_line(dx, dy, dx + ox, dy + oy, 0.8, INK)
        fill_circle(dx + ox, dy + oy, 1.5, INK)
    for i in range(3):
        yy = dy + 6 + i * 5
        stroke_line(dx - 2, yy, dx + 2, yy + 2.5, 0.8, RED)


def illu_yemen(x, y, w, h):
    fill_rect(x, y, w, h, PALE_S)
    fill_circle(x + w * 0.82, y + h * 0.2, 8, GOLD)
    gy = y + h * 0.8
    stroke_line(x + 3, gy, x + w - 3, gy, 1.3, INK)
    # tent
    tx, ty = x + w * 0.16, gy
    fill_poly([(tx, ty), (tx + 17, ty - 22), (tx + 34, ty)], PAPER)
    stroke_poly([(tx, ty), (tx + 17, ty - 22), (tx + 34, ty)], 1.2, INK)
    fill_poly([(tx + 12, ty), (tx + 17, ty - 12), (tx + 22, ty)], NAVY)
    # aid crate with cross
    bx, by = x + w * 0.62, gy - 15
    fill_rect(bx, by, 22, 15, PAPER)
    rect_outline(bx, by, 22, 15, 1.0, INK)
    fill_rect(bx + 9, by + 3, 4, 9, RED)
    fill_rect(bx + 6, by + 6, 10, 3, RED)
    # two small figures
    for fx in (x + w * 0.44, x + w * 0.52):
        fill_circle(fx, gy - 14, 3, INK)
        stroke_line(fx, gy - 11, fx, gy - 2, 1.6, INK)


def illu_myanmar(x, y, w, h):
    fill_rect(x, y, w, h, PALE_G)
    cx = x + w * 0.5
    top = y + h * 0.16
    fill_poly([(cx - 30, top + 10), (cx, top - 4), (cx + 30, top + 10)], NAVY)
    fill_rect(cx - 32, top + 12, 64, 4, NAVY)
    for i in range(4):
        cxx = cx - 24 + i * 16
        fill_rect(cxx, top + 20, 5, 26, NAVY)
    fill_rect(cx - 32, top + 48, 64, 4, NAVY)
    fill_rect(cx - 36, top + 54, 72, 4, NAVY_D)
    # scales
    sx, sy = cx, top + 30
    stroke_line(sx, sy - 12, sx, sy + 6, 1.4, RED_D)
    stroke_line(sx - 10, sy - 10, sx + 10, sy - 10, 1.4, RED_D)
    for ex in (sx - 10, sx + 10):
        stroke_poly([(ex - 4, sy - 3), (ex, sy - 10), (ex + 4, sy - 3)], 1.0, RED_D)
        stroke_poly([(ex - 4, sy - 3), (ex + 4, sy - 3)], 1.2, RED_D)


def illu_korea(x, y, w, h):
    fill_rect(x, y, w, h, PALE)
    # ADIZ dashed boundary
    for t in [i * 0.16 for i in range(20)]:
        px = x + w * 0.52 + w * 0.42 * math.cos(t)
        py = y + h * 0.46 + h * 0.36 * math.sin(t)
        if -0.4 < math.sin(t):
            fill_circle(px, py, 1.1, RED)
    # jet silhouette
    jx, jy = x + w * 0.42, y + h * 0.38
    fill_poly([(jx - 25, jy + 5), (jx + 7, jy - 3), (jx + 25, jy - 10),
               (jx + 15, jy + 1), (jx + 20, jy + 9), (jx + 2, jy + 6),
               (jx - 10, jy + 13), (jx - 15, jy + 5)], NAVY_D)
    for i in range(3):
        stroke_line(jx - 24 - i * 5, jy + 6 + i * 2, jx - 16 - i * 5,
                    jy + 5 + i * 2, 1.1, BLUE)
    # radar dish
    dx, dy = x + w * 0.2, y + h * 0.82
    stroke_poly([(dx - 8, dy - 8), (dx, dy), (dx + 8, dy - 8)], 1.6, INK)
    stroke_line(dx, dy, dx, dy + 5, 1.6, INK)
    for r in (7, 12):
        arc = [(dx + r * math.cos(t), dy - 4 - r * math.sin(t))
               for t in [0.5 + i * 0.18 for i in range(6)]]
        stroke_poly(arc, 1.0, TEAL)


def illu_colombia(x, y, w, h):
    fill_rect(x, y, w, h, PALE_S)
    bx, by, bw, bh = x + w * 0.28, y + h * 0.3, w * 0.44, h * 0.52
    fill_rect(bx, by, bw, bh, GRAY_L)
    rect_outline(bx, by, bw, bh, 1.0, INK)
    for r in range(2):
        for cidx in range(3):
            fill_rect(bx + 5 + cidx * 11, by + 6 + r * 13, 7, 8,
                      NAVY if (r + cidx) % 2 else GOLD)
    # crack
    stroke_poly([(bx + 8, by + 2), (bx + 13, by + 14), (bx + 9, by + 24),
                 (bx + 15, by + 36)], 1.2, INK)
    # burst at base corner
    cx, cy = bx + bw - 2, by + bh
    for ang in (200, 235, 270, 305, 335):
        a = math.radians(ang)
        stroke_line(cx, cy, cx + 13 * math.cos(a), cy + 13 * math.sin(a), 1.6, RED)
    fill_circle(cx, cy, 3.4, GOLD)
    # smoke
    for i, (ox, oy, r) in enumerate(((6, -6, 4), (12, -13, 5.4), (19, -21, 7))):
        fill_circle(bx + 10 + ox, by + oy, r, GRAY)


def illu_spacex(x, y, w, h):
    fill_rect(x, y, w, h, PALE)
    # rocket
    rx, ry = x + w * 0.3, y + h * 0.46
    fill_poly([(rx - 7, ry + 16), (rx - 7, ry - 6), (rx, ry - 20),
               (rx + 7, ry - 6), (rx + 7, ry + 16)], NAVY)
    fill_circle(rx, ry - 4, 3.4, BLUE_L)
    fill_poly([(rx - 7, ry + 10), (rx - 13, ry + 18), (rx - 7, ry + 18)], RED)
    fill_poly([(rx + 7, ry + 10), (rx + 13, ry + 18), (rx + 7, ry + 18)], RED)
    fill_poly([(rx - 3, ry + 18), (rx, ry + 26), (rx + 3, ry + 18)], GOLD)
    # court document
    dx, dy = x + w * 0.58, y + h * 0.2
    fill_rect(dx, dy, 24, 32, PAPER)
    rect_outline(dx, dy, 24, 32, 1.0, INK)
    for i in range(4):
        stroke_line(dx + 4, dy + 7 + i * 6, dx + 20, dy + 7 + i * 6, 1.1, GRAY)
    draw_text(dx + 12, dy + 6.5, "VS", 10, RED, bold=True, align="center")
    # gavel
    gx, gy = x + w * 0.66, y + h * 0.72
    stroke_line(gx - 8, gy + 6, gx + 8, gy - 6, 2.2, RED_D)
    fill_rect(gx + 4, gy - 12, 10, 6, RED_D)
    stroke_line(x + w * 0.55, y + h * 0.88, x + w * 0.85, y + h * 0.88, 1.6, INK)


def illu_hormuz(x, y, w, h):
    fill_rect(x, y, w, h, BLUE)
    # land masses: NW and SE corners leave a strait channel
    fill_poly([(x, y), (x + w * 0.62, y), (x + w * 0.4, y + h * 0.4),
               (x, y + h * 0.52)], PALE_S)
    fill_poly([(x + w, y + h), (x + w * 0.42, y + h), (x + w * 0.62, y + h * 0.58),
               (x + w, y + h * 0.44)], PALE_S)
    # tanker in the channel
    tx, ty = x + w * 0.47, y + h * 0.5
    fill_poly([(tx - 20, ty), (tx + 20, ty), (tx + 15, ty + 6), (tx - 15, ty + 6)], RED_D)
    for i, cc in enumerate((NAVY, GOLD, TEAL, NAVY)):
        fill_rect(tx - 14 + i * 8, ty - 5, 7, 5, cc)
    fill_rect(tx + 12, ty - 9, 5, 5, PAPER)
    # dashed route
    for i in range(6):
        t = i / 6
        stroke_line(x + w * (0.08 + 0.2 * t), y + h * (0.86 - 0.14 * t),
                    x + w * (0.13 + 0.2 * t), y + h * (0.83 - 0.14 * t), 1.1, PAPER)


def illu_gaza(x, y, w, h):
    fill_rect(x, y, w, h, PALE_G)
    fill_circle(x + w * 0.8, y + h * 0.18, 7, GOLD)
    gy = y + h * 0.86
    heights = (0.42, 0.58, 0.36, 0.5, 0.3)
    bx = x + w * 0.08
    for i, hf in enumerate(heights):
        bw = w * 0.15
        bh = h * hf
        fill_rect(bx, gy - bh, bw, bh, GRAY if i % 2 else (128, 130, 136))
        for r in range(int(hf * 5)):
            fill_rect(bx + 3, gy - bh + 4 + r * 8, 3.4, 4,
                      GOLD if (r + i) % 3 else BLUE_L)
        bx += bw + w * 0.02
    stroke_line(x + 3, gy, x + w - 3, gy, 1.3, INK)
    # smoke plume from second building
    sx = x + w * 0.30
    for i, (oy, r) in enumerate(((-4, 3.6), (-11, 5), (-19, 6.4))):
        fill_circle(sx + i * 3, gy - h * 0.58 + oy, r, (150, 150, 152))


def illu_markets(x, y, w, h):
    fill_rect(x, y, w, h, PALE)
    ax, ay = x + w * 0.14, y + h * 0.8
    stroke_line(ax, y + h * 0.14, ax, ay, 1.1, GRAY)
    stroke_line(ax, ay, x + w * 0.9, ay, 1.1, GRAY)
    for i in range(3):
        stroke_line(ax, ay - 12 - i * 12, x + w * 0.9, ay - 12 - i * 12, 0.6, GRAY_L)
    pts = [(ax + 4, ay - 6), (ax + 16, ay - 12), (ax + 26, ay - 10),
           (ax + 36, ay - 22), (ax + 46, ay - 20), (ax + 58, ay - 34)]
    stroke_poly(pts, 2.2, GREEN)
    ex, ey = pts[-1]
    fill_poly([(ex, ey), (ex - 7, ey + 1), (ex - 2, ey + 7)], GREEN)
    # candles
    for i, (cyy, up) in enumerate(((ay - 16, True), (ay - 26, False), (ay - 34, True))):
        cxx = ax + 12 + i * 18
        fill_rect(cxx, cyy, 6, 9, GREEN if up else RED)
        stroke_line(cxx + 3, cyy - 3, cxx + 3, cyy + 12, 0.9, INK)


def illu_nepal(x, y, w, h):
    fill_rect(x, y, w, h, PALE)
    gy = y + h * 0.82
    fill_poly([(x + 4, gy), (x + w * 0.34, y + h * 0.2), (x + w * 0.58, gy)], BLUE)
    fill_poly([(x + w * 0.4, gy), (x + w * 0.68, y + h * 0.3), (x + w * 0.94, gy)], NAVY)
    fill_poly([(x + w * 0.28, y + h * 0.3), (x + w * 0.34, y + h * 0.2),
               (x + w * 0.4, y + h * 0.3), (x + w * 0.34, y + h * 0.36)], PAPER)
    fill_poly([(x + w * 0.62, y + h * 0.39), (x + w * 0.68, y + h * 0.3),
               (x + w * 0.74, y + h * 0.39), (x + w * 0.68, y + h * 0.44)], PAPER)
    # fault crack
    stroke_poly([(x + w * 0.5, gy - 16), (x + w * 0.46, gy - 8),
                 (x + w * 0.53, gy - 2), (x + w * 0.49, gy + 4)], 1.8, RED)
    stroke_line(x + 3, gy + 5, x + w - 3, gy + 5, 1.2, INK)
    # seismograph trace
    pts = []
    base = y + h * 0.93
    for i in range(25):
        px = x + 6 + i * (w - 12) / 24
        amp = (0.6, 1.2, 4.5, 7.0, 3.4, 1.0, 0.6)[min(6, abs(i - 11))] if 5 < i < 18 else 0.6
        pts.append((px, base - amp if i % 2 else base + amp * 0.4))
    stroke_poly(pts, 1.0, RED_D)


ILLUS = [illu_nato, illu_estonia, illu_libya, illu_yemen, illu_myanmar,
         illu_korea, illu_colombia, illu_spacex, illu_hormuz, illu_gaza,
         illu_markets, illu_nepal]


# ---------------------------------------------------------------- content
# tag: ON RECORD (officials said it) / REPORTED (news reports) / CLAIM (allegation)
CARDS = [
    dict(place="BERLIN, GERMANY — NATO", tag="ON RECORD",
         head="NATO's Shield Now Reaches Into Space",
         body="Rutte said NATO's defence pledge extends to orbit, after "
              "reports Russia is readying a nuclear-armed satellite.",
         src="WIRE REPORTS", banner=("SHIELD IN", "ORBIT")),
    dict(place="MOSCOW, RUSSIA — ESTONIA", tag="CLAIM",
         head="Moscow: Estonia Nears an Open Trigger for War",
         body="Russia accused Estonia of hostile acts that bring the two "
              "countries close to an open trigger for war.",
         src="JAPAN TIMES", banner=("BORDER", "WARNING")),
    dict(place="BENGHAZI, LIBYA — WAR AT SEA", tag="ON RECORD",
         head="Libya Demands Kyiv Explain Ship Strike",
         body="Libya's unity government asked Kyiv to explain the strike "
              "on Russian ships off Benghazi and any use of its soil.",
         src="WIRE REPORTS", banner=("SEA DISPUTE", "WIDENS")),
    dict(place="YEMEN — HUMANITARIAN", tag="ON RECORD",
         head="360,000 Displaced in Yemen Since August",
         body="UN figures confirm 323 civilian casualties, 76 of them "
              "dead, as fighting drives a vast displacement crisis.",
         src="UNITED NATIONS", banner=("AID AT", "THE LIMIT")),
    dict(place="NAYPYIDAW, MYANMAR — LAW", tag="ON RECORD",
         head="14 Nations: ICJ Ruling Binds Myanmar",
         body="14 foreign ministers said the ICJ ruling recognising the "
              "genocide of the Rohingya is binding on Myanmar.",
         src="JOINT STATEMENT", banner=("THE COURT", "HAS SPOKEN")),
    dict(place="SEOUL, SOUTH KOREA — AIR DEFENCE", tag="ON RECORD",
         head="Russian Jets Enter Korea's Air Zone",
         body="Fighters scrambled as Russian aircraft entered the air "
              "defence zone over the East Sea; a formal protest follows.",
         src="KOREAN MILITARY", banner=("JETS", "SCRAMBLE")),
    dict(place="VILLAVICENCIO, COLOMBIA — ATTACK", tag="REPORTED",
         head="Car Bomb Wrecks Government Building in Meta",
         body="A car bomb destroyed a government building in Meta's "
              "capital. Casualties were still unconfirmed.",
         src="LOCAL REPORTS", banner=("CAR BOMB", "IN META")),
    dict(place="OREGON + VIRGINIA, US — TECH LAW", tag="REPORTED",
         head="Two States Sue SpaceX Over Grok Images",
         body="Oregon and Virginia allege Grok generated child abuse "
              "imagery — 2 states take an AI maker to court.",
         src="PRESS REPORTS", banner=("AI IMAGES,", "REAL COURT")),
    dict(place="STRAIT OF HORMUZ — SEA LANES", tag="ON RECORD",
         head="Iran Attacks in Hormuz at Record Levels",
         body="Britain says Iranian attacks in the strait — the world's "
              "key oil chokepoint — are at record levels.",
         src="PRESS REPORTS", banner=("CHOKEPOINT", "TIGHTENS")),
    dict(place="GAZA — WAR", tag="REPORTED",
         head="Israeli Strikes Kill at Least 3 in Gaza",
         body="At least 3 people were killed in Israeli attacks, among "
              "them an employee of the UN agency UNRWA.",
         src="AL JAZEERA", banner=("WAR'S", "DAILY TOLL")),
    dict(place="TOKYO + SEOUL — MARKETS", tag="REPORTED",
         head="Nikkei Leaps 3.91%, Kospi 6% on Chip Surge",
         body="Semiconductor shares surged a day after Nvidia chief "
              "Jensen Huang's return, lifting Tokyo and Seoul.",
         src="MARKET REPORTS", banner=("CHIPS LEAD", "THE RALLY")),
    dict(place="KATHMANDU, NEPAL — QUAKE", tag="REPORTED",
         head="Magnitude 5.6 Quake Strikes Eastern Nepal",
         body="A magnitude 5.6 earthquake struck Koshi province in the "
              "east, close to the border with China.",
         src="PRESS REPORTS", banner=("HIMALAYAS", "TREMBLE")),
]

BRIEFS = [
    ("BERLIN", "Merz: Europe is ready to talk with Russia; advisers may meet in Abu Dhabi.", "WIRE"),
    ("KYIV", "Leaked data puts Russian soldiers killed in Ukraine at nearly 500,000.", "JAPAN TIMES"),
    ("ANKARA", "Türkiye is building a scheme to keep Black Sea merchant shipping safe.", "UN AMBASSADOR"),
    ("HELSINKI", "Finland summons Russia's ambassador over 'unacceptable' actions.", "WIRE"),
    ("BRUSSELS", "EU adds The Base's founder, a neo-Nazi, to its terror sanctions list.", "WIRE"),
    ("WASHINGTON", "Senate panel probes VP Vance's links to a Venezuela oil contract.", "JAPAN TIMES"),
    ("WASHINGTON", "US blacklists Megaspeed over the Nvidia spy allegations.", "JAPAN TIMES"),
    ("NEW YORK", "WFP chief: war puts food aid for 7.3 million more people at risk.", "JAPAN TIMES"),
    ("DHAKA", "Ousted PM Hasina plans a 16 December return, facing a death sentence.", "WIRE"),
    ("JAKARTA", "Indonesia charges a former police chief with treason.", "OFFICIALS"),
    ("BEIJING", "First foreign astronaut on Tiangong: Pakistan's Zeeshan Ali, on Shenzhou-24.", "STRAITS TIMES"),
    ("PARIS", "Macron proposes a strategic stockpile of rare earths.", "PRESS"),
    ("MADRID", "Hernández de Cos is the frontrunner to lead the ECB.", "PRESS"),
    ("PENNSYLVANIA", "Measles claims a 9th life; the outbreak now spans 46 counties.", "PRESS"),
    ("NEW YORK", "Guterres seeks a multilateral AI-risk framework within a year.", "PRESS"),
    ("NEW YORK", "The US is confirmed as host of the 2031 Women's World Cup.", "JAPAN TIMES"),
]

NUMBERS = [
    ("360,000+", "people displaced in Yemen since August", NAVY),
    ("~500,000", "Russian soldiers killed in Ukraine — leaked data", RED_D),
    ("14", "nations back the ICJ ruling on Myanmar", NAVY),
    ("7.3M", "more people whose food aid is at risk", NAVY),
    ("+3.91%", "the Nikkei's one-day leap in Tokyo", GREEN),
    ("46", "Pennsylvania counties in the measles outbreak", RED),
    ("M5.6", "earthquake in Nepal's Koshi province", NAVY),
]

CHIPS = [("EUROPE", 8), ("ASIA", 7), ("NORTH AMERICA", 7),
         ("MIDDLE EAST", 4), ("SOUTH AMERICA", 1), ("AFRICA", 1)]

TAG_COLORS = {"ON RECORD": NAVY, "REPORTED": BLUE, "CLAIM": RED_D}


# ---------------------------------------------------------------- helpers
def fit_single(text, size, maxw, bold=False, tracking=0.0, min_size=6.5):
    s = size
    while s > min_size and text_width(text, s, tracking) > maxw:
        s -= 0.5
    return s


def rich_wrap(segments, size, maxw):
    """Wrap styled segments [(text, color, bold)] into lines of word tokens."""
    space_w = GLYPHS[" "][0] * size / 18.0
    tokens = []
    for text, color, bold in segments:
        for wd in text.split(" "):
            if wd:
                tokens.append((wd, color, bold, text_width(wd, size)))
    lines, cur, curw = [], [], 0.0
    for tok in tokens:
        add = tok[3] if not cur else tok[3] + space_w
        if cur and curw + add > maxw:
            lines.append(cur)
            cur, curw = [tok], tok[3]
        else:
            cur.append(tok)
            curw += add
    if cur:
        lines.append(cur)
    return lines, space_w


def rich_draw(lines, space_w, x, y, size):
    for line in lines:
        cx = x
        for wd, color, bold, wdt in line:
            draw_text(cx, y, wd, size, color, bold=bold)
            cx += wdt + space_w
        y += size * 1.22
    return y


# ---------------------------------------------------------------- layout
MX = 26.0           # left margin
MW = 972.0          # content width


def hairline(y, w=0.7, c=GRAY_L, x=MX, wid=MW):
    fill_rect(x, y, wid, w, c)


def draw_card(i, card, x, y):
    w, h = 316.0, 100.0
    ILLUS[i](x, y, 78, 79)
    fill_rect(x, y + 79, 78, 21, NAVY_D)
    for li, line in enumerate(card["banner"]):
        draw_text(x + 39, y + 88.3 + li * 10, line, 8.4, PAPER,
                  bold=True, align="center")
    rect_outline(x, y, 78, 100, 0.8, INK)
    fill_circle(x + 10.5, y + 10.5, 7.4, PAPER)
    fill_circle(x + 10.5, y + 10.5, 6.3, RED)
    draw_text(x + 10.5, y + 13.4, str(i + 1), 9.2, PAPER, bold=True,
              align="center")
    fill_rect(x + 83, y + 3, 0.7, 94, GRAY_L)
    tx = x + 89
    tw = w - 89 - 2
    tag = card["tag"]
    tagw = text_width(tag, 8.2, 0.4) + 9
    tagx = x + w - 2 - tagw
    fill_rect(tagx, y + 1, tagw, 11.5, TAG_COLORS[tag])
    draw_text(tagx + tagw / 2, y + 9.3, tag, 8.2, PAPER, bold=True,
              tracking=0.4, align="center")
    msize = fit_single(card["place"], 10, tagx - 5 - tx, bold=True,
                       tracking=0.3)
    draw_text(tx, y + 11.5, card["place"], msize, NAVY, bold=True,
              tracking=0.3)
    hsize, hlines = fit_lines(card["head"], 16.5, tw, 2)
    for li, line in enumerate(hlines):
        draw_text(tx, y + 30 + li * 19.5, line, hsize, INK, bold=True)
    maxl = 3 if len(hlines) == 1 else 2
    ssize, slines = fit_lines(card["body"], 11.5, tw, maxl, min_size=9.5)
    sy = y + 30 + 19.5 * (len(hlines) - 1) + 15.5
    for li, line in enumerate(slines):
        draw_text(tx, sy + li * 14.2, line, ssize, INK)
    draw_text(tx, y + 96.5, "— " + card["src"], 8.3, GRAY, tracking=0.6)


def draw_page():
    # frame
    rect_outline(8, 8, 1008, 1008, 1.3, INK)
    rect_outline(12.5, 12.5, 999, 999, 0.6, INK)
    # top bar
    draw_text(MX, 33, "THE WORLD IN ONE DAY", 13, INK, bold=True,
              tracking=1.4)
    draw_text(998, 33, "28 STORIES · 6 REGIONS · ALL FROM THIS ONE DAY",
              11, INK, bold=True, tracking=0.7, align="right")
    fill_rect(MX, 40, MW, 2.0, INK)
    fill_rect(MX, 44.5, MW, 0.7, INK)
    # masthead
    msize = fit_single("Tuesday 24 November 2026", 66, MW, bold=True,
                       tracking=0.5)
    draw_text(512, 96, "Tuesday 24 November 2026", msize, INK, bold=True,
              tracking=0.5, align="center", serif=True)
    hairline(104)
    # kicker
    draw_text(512, 122,
              "NATO'S SHIELD REACHES SPACE · 360,000 FLEE IN YEMEN · "
              "NIKKEI LEAPS 3.91% IN TOKYO",
              13.5, RED, bold=True, tracking=0.4, align="center")
    # region chips
    hairline(130, 0.6)
    chip_specs = []
    total = 0.0
    for name, cnt in CHIPS:
        lab_w = text_width(name, 11, 0.5)
        cnt_w = text_width(" " + str(cnt), 11, 0.5)
        cw_ = lab_w + cnt_w + 15
        chip_specs.append((name, cnt, lab_w, cw_))
        total += cw_ + 8
    total -= 8
    cx = (1024 - total) / 2
    for name, cnt, lab_w, cw_ in chip_specs:
        rect_outline(cx, 134, cw_, 20, 0.9, NAVY)
        draw_text(cx + 7.5, 148, name, 11, INK, bold=True, tracking=0.5)
        draw_text(cx + 7.5 + lab_w, 148, " " + str(cnt), 11, RED,
                  bold=True, tracking=0.5)
        cx += cw_ + 8
    hairline(158, 0.6)
    # UTC timeline
    draw_text(MX, 176, "THE DAY IN UTC", 10.5, INK, bold=True, tracking=0.6)
    draw_text(MX, 187, "AS REPORTED", 8.3, GRAY, tracking=0.6)
    seg_x, seg_w = 170.0, 138.0
    labels = ["EARLY", "MORNING", "MIDDAY", "AFTERNOON", "EVENING", "NIGHT"]
    for si, lab in enumerate(labels):
        draw_text(seg_x + si * seg_w + seg_w / 2, 170, lab, 10, NAVY,
                  bold=True, tracking=0.8, align="center")
        if si:
            fill_rect(seg_x + si * seg_w, 174, 0.7, 7, GRAY)
    fill_rect(seg_x, 180, seg_w * 6, 0.8, INK)
    dots = [(0, .3), (0, .72), (1, .18), (1, .52), (1, .86), (2, .38),
            (2, .74), (3, .14), (3, .5), (3, .9), (4, .34), (4, .66),
            (5, .24), (5, .58)]
    for si, fr in dots:
        fill_circle(seg_x + (si + fr) * seg_w, 180, 2.0,
                    RED if si in (0, 5) else NAVY)
    hairline(190, 0.7)
    # cards
    for i, card in enumerate(CARDS):
        cx = MX + (i % 3) * 328
        cy = 196 + (i // 3) * 106
        draw_card(i, card, cx, cy)
    # numbers band
    hairline(624, 1.3, INK)
    draw_text(MX, 641, "THE DAY IN NUMBERS", 12.5, RED, bold=True,
              tracking=1.2)
    draw_text(998, 641, "EVERY FIGURE FROM THE DAY'S OWN REPORTING", 9,
              GRAY, tracking=0.6, align="right")
    iw = MW / 7
    for i, (val, lab, col) in enumerate(NUMBERS):
        cx = MX + i * iw + iw / 2
        vsize = fit_single(val, 26, iw - 8, bold=True)
        draw_text(cx, 669, val, vsize, col, bold=True, align="center")
        _, lab_lines = fit_lines(lab, 8.8, iw - 10, 2)
        for li, line in enumerate(lab_lines):
            draw_text(cx, 681 + li * 11, line, 8.8, GRAY, align="center")
    hairline(700, 0.7)
    # bottom section header
    draw_text(MX, 718, "ALSO ON TUESDAY", 13.5, INK, bold=True,
              tracking=0.8)
    hw = text_width("ALSO ON TUESDAY", 13.5, 0.8)
    draw_text(MX + hw + 9, 718, "— 16 MORE STORIES FROM THE SAME DAY",
              9.5, GRAY, tracking=0.4)
    draw_text(712, 718, "THE WORLD ON TUESDAY", 11.5, INK, bold=True,
              tracking=0.6)
    fill_rect(700, 726, 0.7, 238, GRAY_L)
    # briefs in three columns (6 / 5 / 5)
    cols = [(0, 6, MX), (6, 11, 238.0), (11, 16, 450.0)]
    for a, b, bx in cols:
        size = 10.6
        per = []
        while size > 8.6:
            total_h = 0.0
            per = []
            for j in range(a, b):
                city, text, src = BRIEFS[j]
                segs = [(str(j + 13) + " ", RED, True),
                        (city + " — ", NAVY, True),
                        (text + " ", INK, False),
                        ("· " + src, GRAY, False)]
                lines, sw_ = rich_wrap(segs, size, 200)
                per.append((lines, sw_))
                total_h += len(lines) * size * 1.22 + 4
            if total_h <= 242:
                break
            size -= 0.2
        by = 724.0
        for lines, sw_ in per:
            by = rich_draw(lines, sw_, bx, by + size * 0.92, size) + 4
    # map
    draw_map(712, 730, 286, 176)
    draw_text(712, 922, "WHERE IT HAPPENED — PINS MATCH THE 12 CARDS",
              8.8, NAVY, bold=True, tracking=0.3)
    draw_text(712, 935, "Berlin to Kathmandu: one day, six regions.",
              8.8, GRAY)
    # footer
    hairline(976, 1.3, INK)
    draw_text(MX, 993,
              "DATE CHECK — Every story on this page happened, or was "
              "first reported, on Tuesday 24 November 2026 (UTC). "
              "Nothing older, nothing carried over.",
              9.8, INK)
    draw_text(998, 993, "ONE IMAGE · ONE DAY", 9.8, NAVY, bold=True,
              tracking=0.6, align="right")
    draw_text(MX, 1007,
              "ON RECORD = said by officials · REPORTED = from news "
              "reports · CLAIM = one side's allegation",
              9, GRAY)
    draw_text(998, 1007, "Pictures and map drawn in code — no photographs.",
              9, INK, align="right")


def main():
    draw_page()
    os.makedirs("/output", exist_ok=True)
    n = save_png("/output/entry.png")
    print("wrote /output/entry.png:", n, "bytes")


if __name__ == "__main__":
    main()
