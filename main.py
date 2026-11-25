#!/usr/bin/env python3
"""One-page broadsheet that sums up the world news of Tuesday 24 November 2026.

Standard library only. The page is drawn at 4096x4096 with a hand-made
stroke font and then reduced to 1024x1024 by 4x4 area averaging, so the
output is a deterministic PNG written to /output/entry.png.
"""

import os
import struct
import zlib

S = 4                      # supersampling factor
W = H = 1024 * S           # internal canvas
OW = OH = 1024             # output size

PAPER = (247, 243, 232)
INK = (24, 24, 34)
DARK = (46, 46, 54)
RED = (176, 28, 38)
BLUE = (26, 74, 138)
LAND = (74, 76, 92)
WHITE = (255, 255, 255)

img = bytearray(bytes(PAPER) * (W * H))

# ---------------------------------------------------------------- canvas --

def stamp(cx, cy, r, color):
    """Filled square brush stamp, coordinates in device pixels."""
    x0 = int(cx - r)
    x1 = int(cx + r)
    y0 = int(cy - r)
    y1 = int(cy + r)
    if x1 < 0 or y1 < 0 or x0 >= W or y0 >= H:
        return
    x0 = max(0, x0)
    y0 = max(0, y0)
    x1 = min(W - 1, x1)
    y1 = min(H - 1, y1)
    seg = bytes(color) * (x1 - x0 + 1)
    n = len(seg)
    for yy in range(y0, y1 + 1):
        i = (yy * W + x0) * 3
        img[i:i + n] = seg


def line(x0, y0, x1, y1, w, color):
    """Thick line, coordinates in design units (1024 grid)."""
    X0, Y0, X1, Y1 = x0 * S, y0 * S, x1 * S, y1 * S
    steps = int(max(abs(X1 - X0), abs(Y1 - Y0))) + 1
    r = max(1.0, w * S / 2.0)
    for i in range(steps + 1):
        t = i / steps if steps else 0.0
        stamp(X0 + (X1 - X0) * t, Y0 + (Y1 - Y0) * t, r, color)


def rect(x, y, w, h, color):
    X0, Y0 = int(x * S), int(y * S)
    X1, Y1 = int((x + w) * S), int((y + h) * S)
    if X1 <= X0 or Y1 <= Y0:
        return
    seg = bytes(color) * (X1 - X0)
    n = len(seg)
    for yy in range(Y0, Y1):
        i = (yy * W + X0) * 3
        img[i:i + n] = seg


def frame(x, y, w, h, t, color):
    rect(x, y, w, t, color)
    rect(x, y + h - t, w, t, color)
    rect(x, y, t, h, color)
    rect(x + w - t, y, t, h, color)


def disc(cx, cy, r, color):
    """Filled circle in design units."""
    R = r * S
    CX, CY = cx * S, cy * S
    y0 = int(CY - R)
    y1 = int(CY + R)
    for yy in range(y0, y1 + 1):
        dy = yy - CY
        dx = (max(0.0, R * R - dy * dy)) ** 0.5
        x0 = int(CX - dx)
        x1 = int(CX + dx)
        if x1 < 0 or x0 >= W or yy < 0 or yy >= H:
            continue
        x0 = max(0, x0)
        x1 = min(W - 1, x1)
        seg = bytes(color) * (x1 - x0 + 1)
        i = (yy * W + x0) * 3
        img[i:i + len(seg)] = seg

# ------------------------------------------------------------ stroke font --
# Each glyph is a list of strokes; a stroke is a list of (x, y) points in a
# 6-wide, 9-tall box where y grows upwards from the baseline.

GL = {
    "A": [[(0, 0), (3, 9), (6, 0)], [(1.3, 3.3), (4.7, 3.3)]],
    "B": [[(0, 0), (0, 9)], [(0, 9), (3.4, 9), (4.9, 7.7), (4.9, 6.2), (3.4, 4.9), (0, 4.9)],
          [(0, 4.9), (3.8, 4.9), (5.3, 3.4), (5.3, 1.5), (3.8, 0), (0, 0)]],
    "C": [[(5.4, 7.6), (3.9, 9), (1.8, 9), (0.4, 6.8), (0.4, 2.6), (1.8, 0.4), (3.9, 0.2), (5.4, 1.6)]],
    "D": [[(0, 0), (0, 9)], [(0, 9), (3.2, 9), (5.2, 6.8), (5.2, 2.2), (3.2, 0), (0, 0)]],
    "E": [[(5.2, 9), (0, 9), (0, 0), (5.2, 0)], [(0, 4.6), (4.2, 4.6)]],
    "F": [[(0, 0), (0, 9), (5.2, 9)], [(0, 4.6), (4.0, 4.6)]],
    "G": [[(5.4, 7.6), (3.9, 9), (1.8, 9), (0.4, 6.8), (0.4, 2.6), (1.8, 0.4), (4.0, 0.2),
           (5.4, 1.2), (5.4, 3.4), (3.4, 3.4)]],
    "H": [[(0, 0), (0, 9)], [(6, 0), (6, 9)], [(0, 4.6), (6, 4.6)]],
    "I": [[(3, 0), (3, 9)], [(1.2, 9), (4.8, 9)], [(1.2, 0), (4.8, 0)]],
    "J": [[(5.4, 9), (5.4, 2.2), (4.2, 0.4), (2.4, 0.2), (0.8, 1.6)]],
    "K": [[(0, 0), (0, 9)], [(5.6, 9), (0.6, 4.2)], [(1.6, 3.2), (5.8, 0)]],
    "L": [[(0, 9), (0, 0), (5.2, 0)]],
    "M": [[(0, 0), (0, 9), (3, 3.8), (6, 9), (6, 0)]],
    "N": [[(0, 0), (0, 9), (6, 0), (6, 9)]],
    "O": [[(1.8, 0.2), (0.4, 2.4), (0.4, 6.6), (1.8, 8.8), (4.2, 8.8), (5.6, 6.6),
           (5.6, 2.4), (4.2, 0.2), (1.8, 0.2)]],
    "P": [[(0, 0), (0, 9), (3.6, 9), (5.2, 7.4), (5.2, 5.8), (3.6, 4.4), (0, 4.4)]],
    "Q": [[(1.8, 0.2), (0.4, 2.4), (0.4, 6.6), (1.8, 8.8), (4.2, 8.8), (5.6, 6.6),
           (5.6, 2.4), (4.2, 0.2), (1.8, 0.2)], [(3.8, 2.2), (6.2, 0)]],
    "R": [[(0, 0), (0, 9), (3.6, 9), (5.2, 7.4), (5.2, 5.8), (3.6, 4.4), (0, 4.4)],
          [(3.4, 4.4), (5.6, 0)]],
    "S": [[(5.2, 7.8), (3.8, 9), (1.6, 8.8), (0.6, 7.2), (1.2, 5.6), (4.6, 3.8),
           (5.4, 2.4), (4.6, 0.6), (2.6, 0), (0.8, 1.2)]],
    "T": [[(0, 9), (6, 9)], [(3, 9), (3, 0)]],
    "U": [[(0, 9), (0, 2.4), (1.6, 0.3), (4.4, 0.3), (6, 2.4), (6, 9)]],
    "V": [[(0, 9), (3, 0), (6, 9)]],
    "W": [[(0, 9), (1.4, 0), (3, 5.2), (4.6, 0), (6, 9)]],
    "X": [[(0, 0), (6, 9)], [(0, 9), (6, 0)]],
    "Y": [[(0, 9), (3, 4.6), (6, 9)], [(3, 4.6), (3, 0)]],
    "Z": [[(0, 9), (6, 9), (0, 0), (6, 0)]],
    "0": [[(1.9, 0.2), (0.5, 2.2), (0.5, 6.8), (1.9, 8.8), (4.1, 8.8), (5.5, 6.8),
           (5.5, 2.2), (4.1, 0.2), (1.9, 0.2)]],
    "1": [[(1.4, 7.2), (3.2, 9), (3.2, 0)], [(1.2, 0), (5, 0)]],
    "2": [[(0.6, 7.4), (2.0, 9), (4.2, 8.8), (5.4, 7.2), (5.0, 5.2), (0.4, 0.2), (5.6, 0.2)]],
    "3": [[(0.6, 7.6), (2.2, 9), (4.4, 8.6), (4.6, 6.8), (3.2, 5.2), (1.8, 4.8)],
          [(3.2, 5.2), (4.8, 4.4), (5.0, 2.0), (3.8, 0.3), (1.8, 0.2), (0.4, 1.4)]],
    "4": [[(4.2, 0), (4.2, 9), (0.4, 3.2), (5.8, 3.2)]],
    "5": [[(5.2, 9), (1.0, 9), (0.8, 5.6), (3.4, 6.2), (5.2, 4.8), (5.2, 2.0),
           (3.6, 0.3), (1.4, 0.4), (0.4, 1.6)]],
    "6": [[(5.0, 7.8), (3.4, 9), (1.4, 7.0), (0.6, 3.6), (1.6, 1.0), (3.4, 0.2),
           (5.0, 1.4), (5.2, 3.4), (4.0, 4.8), (2.0, 4.6), (0.8, 3.4)]],
    "7": [[(0.4, 9), (5.6, 9), (2.6, 0)]],
    "8": [[(2.0, 4.8), (1.0, 6.0), (1.2, 7.8), (2.8, 9), (4.6, 8.6), (5.4, 6.8), (4.6, 5.4),
           (3.4, 4.6), (4.8, 3.6), (5.4, 1.8), (4.4, 0.3), (2.4, 0.1), (0.8, 1.2),
           (0.6, 3.2), (2.0, 4.8)]],
    "9": [[(1.0, 1.8), (2.6, 0.2), (4.6, 2.0), (5.4, 5.4), (4.4, 8.0), (2.6, 8.8),
           (1.0, 7.4), (1.0, 5.6), (2.6, 4.2), (4.4, 4.6), (5.3, 5.6)]],
    ".": [[(3, 0.1), (3, 1.0)]],
    ",": [[(3.3, 1.3), (2.7, 0.0)]],
    ":": [[(3, 6.7), (3, 7.6)], [(3, 0.6), (3, 1.5)]],
    ";": [[(3, 6.7), (3, 7.6)], [(3.3, 1.5), (2.7, 0.0)]],
    "'": [[(3, 9), (3, 7.4)]],
    '"': [[(1.7, 9), (1.7, 7.4)], [(4.3, 9), (4.3, 7.4)]],
    "!": [[(3, 9), (3, 2.6)], [(3, 0.2), (3, 1.1)]],
    "?": [[(0.8, 7.2), (2.2, 9), (4.4, 8.8), (5.2, 7.2), (4.4, 5.2), (3, 4.2), (3, 2.8)],
          [(3, 0.2), (3, 1.1)]],
    "-": [[(1, 4.5), (5, 4.5)]],
    "\u2014": [[(0.2, 4.5), (5.8, 4.5)]],
    "/": [[(0.6, 0), (5.4, 9)]],
    "(": [[(4.4, 9), (2.6, 6.6), (2.6, 2.4), (4.4, 0)]],
    ")": [[(1.6, 9), (3.4, 6.6), (3.4, 2.4), (1.6, 0)]],
    "%": [[(0.6, 0), (5.4, 9)],
          [(1.8, 6.6), (0.8, 7.6), (1.0, 8.8), (2.2, 8.6), (2.3, 7.3), (1.8, 6.6)],
          [(4.5, 0.5), (3.6, 1.7), (3.8, 3.0), (5.0, 2.8), (5.1, 1.5), (4.5, 0.5)]],
    "+": [[(3, 1.8), (3, 7.2)], [(0.8, 4.5), (5.2, 4.5)]],
    "\u00b7": [[(3, 4.1), (3, 5.0)]],
}

NARROW = set("I.,:;'!|")
WIDE = set("MW")


def char_adv(ch, size):
    if ch == " ":
        return size * 0.50
    if ch in NARROW:
        return size * 0.44
    if ch in WIDE:
        return size * 0.98
    if ch == "\u2014":
        return size * 1.00
    return size * 0.80


def text_w(s, size):
    return sum(char_adv(c, size) for c in s.upper())


def draw_text(x, y, s, size, color, bold=False, align="left"):
    """Draw one line of text; y is the top of the cap height."""
    s = s.upper()
    w = text_w(s, size)
    if align == "center":
        x -= w / 2.0
    elif align == "right":
        x -= w
    ratio = 0.235 if bold else 0.165
    if size < 11:
        ratio += 0.035          # small type gets a heavier stroke
    sw = size * ratio
    u = size / 9.0
    cx = x
    for ch in s:
        if ch != " ":
            glyph = GL.get(ch)
            if glyph:
                for stroke in glyph:
                    pts = [(cx + px * u, y + (9 - py) * u) for px, py in stroke]
                    if len(pts) == 1:
                        line(pts[0][0], pts[0][1], pts[0][0], pts[0][1], sw, color)
                    for a, b in zip(pts, pts[1:]):
                        line(a[0], a[1], b[0], b[1], sw, color)
        cx += char_adv(ch, size)
    return cx


def wrap(s, size, maxw):
    words = s.upper().split()
    lines = []
    cur = ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if text_w(trial, size) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def draw_wrapped(x, y, s, size, maxw, color, lh, bold=False, max_lines=None):
    lines = wrap(s, size, maxw)
    if max_lines:
        lines = lines[:max_lines]
    for i, ln in enumerate(lines):
        draw_text(x, y + i * lh, ln, size, color, bold)
    return y + len(lines) * lh

# ------------------------------------------------------------------ map --
# Rough continent outlines as (lon, lat) polygons, drawn as dot fields.

LAND_POLYS = [
    # North America
    [(-166, 68), (-150, 70), (-135, 69), (-125, 71), (-110, 68), (-95, 69), (-88, 66),
     (-82, 66), (-78, 62), (-68, 58), (-60, 52), (-65, 47), (-70, 44), (-72, 40),
     (-75, 35), (-76, 30), (-80, 26), (-82, 23), (-87, 21), (-90, 20), (-96, 16),
     (-102, 13), (-92, 11), (-83, 9), (-79, 9), (-86, 13), (-92, 15), (-102, 18),
     (-106, 22), (-110, 24), (-114, 29), (-117, 33), (-122, 37), (-124, 43),
     (-124, 47), (-130, 54), (-140, 60), (-155, 59), (-165, 60)],
    # South America
    [(-78, 7), (-75, 10), (-72, 12), (-64, 10), (-55, 6), (-50, 0), (-44, -2),
     (-35, -8), (-39, -13), (-40, -20), (-46, -24), (-52, -30), (-58, -35),
     (-62, -39), (-63, -42), (-65, -47), (-67, -52), (-69, -54), (-71, -54),
     (-74, -50), (-74, -42), (-73, -34), (-71, -27), (-70, -20), (-73, -16),
     (-77, -12), (-80, -6), (-81, -2), (-80, 2), (-77, 5)],
    # Africa
    [(-17, 15), (-16, 20), (-13, 27), (-9, 31), (-6, 34), (-2, 35), (10, 37),
     (11, 34), (20, 32), (30, 31), (34, 28), (36, 24), (39, 20), (43, 12),
     (48, 11), (51, 12), (48, 6), (42, 0), (41, -4), (40, -10), (38, -16),
     (36, -21), (34, -26), (31, -29), (27, -33), (20, -35), (18, -33), (16, -28),
     (14, -22), (13, -17), (12, -12), (13, -6), (9, -1), (9, 4), (4, 6), (-3, 5),
     (-8, 4), (-13, 7), (-17, 12)],
    # Europe (mainland)
    [(-9, 37), (-9, 43), (-5, 44), (-2, 46), (-1, 49), (2, 51), (5, 53), (7, 54),
     (8, 56), (10, 58), (18, 56), (21, 55), (24, 58), (26, 60), (29, 63), (30, 67),
     (25, 71), (18, 69), (14, 66), (12, 62), (6, 62), (5, 59), (-3, 53), (-5, 48),
     (-9, 44)],
    # Britain
    [(-5, 50), (-3, 53), (-2, 55), (-4, 58), (-6, 57), (-8, 55), (-6, 52), (-5, 50)],
    # Asia
    [(30, 41), (33, 45), (36, 42), (40, 44), (44, 42), (48, 40), (50, 44),
     (55, 46), (60, 50), (66, 52), (72, 54), (80, 54), (88, 50), (95, 50),
     (104, 52), (110, 54), (118, 52), (126, 50), (132, 48), (138, 46), (141, 42),
     (140, 38), (138, 35), (133, 34), (129, 36), (127, 40), (126, 41), (122, 38),
     (121, 32), (120, 28), (118, 25), (110, 20), (109, 16), (108, 11), (106, 7),
     (104, 2), (101, 6), (99, 10), (98, 14), (95, 16), (92, 16), (90, 22),
     (88, 21), (85, 19), (80, 13), (78, 8), (75, 13), (72, 20), (68, 23),
     (62, 25), (57, 26), (52, 28), (50, 29), (48, 28), (54, 26), (58, 23),
     (59, 22), (55, 17), (49, 14), (45, 12), (43, 12), (40, 15), (38, 20),
     (36, 28), (34, 31), (36, 36), (30, 36), (30, 41)],
    # Siberia strip (northern Asia)
    [(32, 66), (45, 67), (60, 69), (75, 72), (90, 73), (105, 77), (115, 73),
     (128, 72), (142, 72), (155, 70), (168, 66), (178, 65), (178, 62), (165, 60),
     (158, 53), (145, 50), (130, 48), (110, 52), (88, 50), (66, 52), (50, 44),
     (40, 44), (32, 66)],
    # Indonesia / New Guinea
    [(95, 5), (100, 1), (104, -2), (106, -6), (110, -7), (114, -3), (119, -1),
     (125, -1), (131, -3), (137, -2), (142, -3), (147, -6), (150, -9), (146, -8),
     (140, -7), (133, -4), (126, -4), (118, -4), (111, -9), (105, -9), (99, -3),
     (95, 3)],
    # Japan
    [(130, 31), (132, 33), (135, 34), (138, 35), (140, 36), (141, 40), (141, 43),
     (143, 44), (141, 45), (139, 39), (136, 35), (132, 33), (130, 32)],
    # Australia
    [(113, -22), (113, -26), (115, -32), (118, -35), (124, -33), (130, -32),
     (135, -35), (138, -36), (141, -38), (146, -39), (150, -37), (153, -31),
     (153, -26), (150, -22), (146, -19), (143, -15), (142, -11), (140, -13),
     (137, -12), (136, -15), (133, -12), (130, -12), (126, -14), (122, -17),
     (118, -20), (114, -21)],
]


def in_poly(lon, lat, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > lat) != (y2 > lat):
            xin = (x2 - x1) * (lat - y1) / (y2 - y1) + x1
            if lon < xin:
                inside = not inside
    return inside


def on_land(lon, lat):
    for poly in LAND_POLYS:
        if in_poly(lon, lat, poly):
            return True
    return False

# -------------------------------------------------------------- content --
# Every headline, summary and brief below is written for this page.

CARDS = [
    {"n": 1, "place": "BRUSSELS", "cat": "DEFENCE", "tag": "ON RECORD", "region": "EUROPE",
     "lon": 4.4, "lat": 50.9, "dx": -13, "dy": -13,
     "head": "NATO PLEDGE REACHES INTO ORBIT, RUTTE SAYS",
     "body": "Alliance chief says the defence pledge now reaches orbit, amid reports Russia readies a nuclear satellite.",
     "src": "NATO HQ BRIEFING"},
    {"n": 2, "place": "MOSCOW", "cat": "DIPLOMACY", "tag": "REPORTED", "region": "EUROPE",
     "lon": 37.6, "lat": 55.8, "dx": 12, "dy": -12,
     "head": "RUSSIA WARNS ESTONIA OVER HOSTILE ACTS",
     "body": "Moscow accused Tallinn of hostile behaviour and said such acts come close to a trigger for war.",
     "src": "STATE MEDIA, MOSCOW"},
    {"n": 3, "place": "TRIPOLI", "cat": "DIPLOMACY", "tag": "ON RECORD", "region": "AFRICA",
     "lon": 13.2, "lat": 32.9, "dx": -13, "dy": 13,
     "head": "LIBYA DEMANDS KYIV EXPLAIN SHIP ATTACK",
     "body": "The unity government asked Ukraine to explain a strike on a Russian ship off Benghazi and use of Libyan soil.",
     "src": "GOVERNMENT STATEMENT"},
    {"n": 4, "place": "SANAA", "cat": "HUMANITARIAN", "tag": "ON RECORD", "region": "MIDEAST",
     "lon": 44.2, "lat": 15.4, "dx": 13, "dy": 10,
     "head": "360,000 FLEE THEIR HOMES IN YEMEN",
     "body": "UN counts 323 civilian casualties since August, 76 of them dead, as displacement passes 360,000 people.",
     "src": "UN OCHA COUNT"},
    {"n": 5, "place": "THE HAGUE", "cat": "LAW", "tag": "ON RECORD", "region": "ASIA",
     "lon": 4.3, "lat": 52.1, "dx": 13, "dy": -13,
     "head": "14 NATIONS: GENOCIDE RULING BINDS MYANMAR",
     "body": "Foreign ministers of 14 states said the ICJ ruling on genocide against the Rohingya binds Myanmar.",
     "src": "JOINT STATEMENT"},
    {"n": 6, "place": "SEOUL", "cat": "DEFENCE", "tag": "REPORTED", "region": "ASIA",
     "lon": 127.0, "lat": 37.6, "dx": 12, "dy": -11,
     "head": "RUSSIAN JETS ENTER KOREA DEFENCE ZONE",
     "body": "Fighters scrambled as Russian aircraft entered the air defence zone over the East Sea; Seoul protested.",
     "src": "JOINT CHIEFS, SEOUL"},
    {"n": 7, "place": "VILLAVICENCIO", "cat": "SECURITY", "tag": "REPORTED", "region": "AMERICAS",
     "lon": -73.6, "lat": 4.1, "dx": 0, "dy": 14,
     "head": "CAR BOMB WRECKS GOVERNMENT HQ IN META",
     "body": "A car bomb destroyed a government building in the Meta capital; the casualty count was still unconfirmed.",
     "src": "REGIONAL AUTHORITIES"},
    {"n": 8, "place": "SALEM, OREGON", "cat": "TECH LAW", "tag": "CLAIM", "region": "AMERICAS",
     "lon": -120.6, "lat": 44.0, "dx": -12, "dy": -12,
     "head": "TWO STATES SUE SPACEX OVER GROK IMAGES",
     "body": "Oregon and Virginia allege the Grok AI produced child-abuse imagery, in a suit against SpaceX.",
     "src": "COURT FILINGS, US"},
    {"n": 9, "place": "HORMUZ", "cat": "ENERGY", "tag": "ON RECORD", "region": "MIDEAST",
     "lon": 56.3, "lat": 26.6, "dx": 13, "dy": -12,
     "head": "IRAN ATTACKS AT RECORD LEVEL AT HORMUZ",
     "body": "Britain says Iranian attacks near the strait hit record levels at the chokepoint of world oil trade.",
     "src": "UK FOREIGN OFFICE"},
    {"n": 10, "place": "GAZA", "cat": "CONFLICT", "tag": "REPORTED", "region": "MIDEAST",
     "lon": 34.3, "lat": 31.4, "dx": -13, "dy": -12,
     "head": "STRIKES KILL THREE IN GAZA, UN AIDE AMONG THEM",
     "body": "Israeli attacks killed at least three people in Gaza; one of the dead was an UNRWA staff member.",
     "src": "HEALTH MINISTRY, GAZA"},
    {"n": 11, "place": "TOKYO", "cat": "MARKETS", "tag": "ON RECORD", "region": "ASIA",
     "lon": 139.7, "lat": 35.7, "dx": 12, "dy": 12,
     "head": "NIKKEI LEAPS 3.91% AS CHIP STOCKS SURGE",
     "body": "Tokyo rose 3.91% and Seoul 6% as chip shares surged, a day after NVIDIA boss Jensen Huang visited.",
     "src": "MARKET CLOSE, TOKYO"},
    {"n": 12, "place": "KATHMANDU", "cat": "DISASTER", "tag": "REPORTED", "region": "ASIA",
     "lon": 85.3, "lat": 27.7, "dx": -12, "dy": 12,
     "head": "MAGNITUDE 5.6 QUAKE SHAKES EASTERN NEPAL",
     "body": "A magnitude 5.6 quake struck Koshi province in the east of Nepal, close to the border with China.",
     "src": "SEISMOLOGY CENTRE"},
]

BRIEFS = [
    "BERLIN \u2014 MERZ: EUROPE IS READY TO TALK TO RUSSIA",
    "LEAK \u2014 RUSSIAN DEAD IN UKRAINE PUT NEAR 500,000",
    "ANKARA \u2014 TURKEY BUILDS BLACK SEA SHIPPING SHIELD",
    "HELSINKI \u2014 FINLAND SUMMONS RUSSIA ENVOY IN PROTEST",
    "BRUSSELS \u2014 EU SANCTIONS THE BASE FOUNDER AS TERRORIST",
    "WASHINGTON \u2014 SENATE PROBES VANCE, VENEZUELA OIL DEAL",
    "WASHINGTON \u2014 US BLACKLISTS MEGASPEED IN NVIDIA CASE",
    "ROME \u2014 WFP: FOOD AID FOR 7.3M MORE PUT AT RISK BY WAR",
    "DHAKA \u2014 HASINA PLANS DEC 16 RETURN DESPITE SENTENCE",
    "JAKARTA \u2014 EX-POLICE CHIEF CHARGED WITH TREASON",
    "ORBIT \u2014 PAKISTAN'S ALI, FIRST FOREIGNER ON TIANGONG",
    "PARIS \u2014 MACRON FLOATS RARE-EARTH STRATEGIC RESERVE",
    "FRANKFURT \u2014 DE COS LEADS RACE FOR ECB PRESIDENCY",
    "US \u2014 MEASLES KILLS A NINTH; 46 COUNTIES AFFECTED",
    "UN \u2014 GUTERRES SEEKS AI-RISK PACT WITHIN A YEAR",
    "ZURICH \u2014 US CONFIRMED HOST OF 2031 WOMEN'S CUP",
]

NUMBERS = [
    ("360,000", "PEOPLE DISPLACED IN YEMEN SINCE AUGUST"),
    ("500,000", "RUSSIAN SOLDIERS KILLED \u2014 LEAKED DATA"),
    ("14", "NATIONS BACKING THE ICJ GENOCIDE RULING"),
    ("7.3M", "MORE PEOPLE RISK LOSING FOOD AID"),
    ("+3.91%", "NIKKEI 225 RISE AT THE TOKYO CLOSE"),
    ("46", "COUNTIES REPORTING MEASLES CASES"),
    ("M5.6", "QUAKE IN KOSHI PROVINCE, EASTERN NEPAL"),
]

TIMELINE = [
    (1.7, "M5.6 NEPAL"), (4.1, "GAZA STRIKES"), (6.5, "KOSPI +6%"),
    (7.3, "NIKKEI +3.91%"), (9.3, "JETS OVER EAST SEA"), (11.8, "HORMUZ WARNING"),
    (13.2, "META CAR BOMB"), (15.5, "RUTTE ON ORBIT"), (17.1, "ICJ RULING"),
    (19.7, "YEMEN COUNT"), (21.3, "SPACEX SUED"), (23.0, "LIBYA PROTEST"),
]

MX = 28.0          # page margin
RX = 996.0         # right edge

# ----------------------------------------------------------------- page --

def masthead():
    draw_text(MX, 16, "GLOBAL EDITION \u2014 ALL TIMES UTC", 12, RED, True)
    draw_text(RX, 18, "ONE DAY \u00b7 ONE PAGE \u00b7 NO. 24-11", 10.5, DARK, False, "right")
    line(MX, 36, RX, 36, 2.6, RED)
    draw_text(512, 44, "THE WORLD TODAY", 56, INK, True, "center")
    draw_text(512, 106, "THE DAY'S WORLD NEWS ON A SINGLE PAGE \u2014 FROM EVERY CONTINENT",
              11.5, DARK, False, "center")
    line(MX, 126, RX, 126, 3.0, INK)
    draw_text(MX, 136, "LATE EDITION", 10, DARK, True)
    draw_text(512, 131, "TUESDAY 24 NOVEMBER 2026", 24, INK, True, "center")
    draw_text(RX, 136, "EST. 2026", 10, DARK, True, "right")
    line(MX, 160, RX, 160, 1.2, INK)


def chips():
    y = 168
    x = MX
    draw_text(x, y + 2, "THE 12 STORIES BY REGION:", 10.5, INK, True)
    x += text_w("THE 12 STORIES BY REGION:", 10.5) + 12
    counts = {}
    for c in CARDS:
        counts[c["region"]] = counts.get(c["region"], 0) + 1
    order = ["EUROPE", "MIDEAST", "ASIA", "AMERICAS", "AFRICA"]
    names = {"MIDEAST": "MIDDLE EAST"}
    for reg in order:
        label = "%s %d" % (names.get(reg, reg), counts.get(reg, 0))
        w = text_w(label, 10.5) + 16
        frame(x, y, w, 20, 1.1, INK)
        draw_text(x + 8, y + 5, label, 10.5, INK, True)
        x += w + 8


def timeline():
    draw_text(RX, 190, "THE DAY IN UTC \u2014 HOUR BY HOUR", 10.5, INK, True, "right")
    axis_y = 230
    x0, x1 = 40.0, 984.0
    line(x0, axis_y, x1, axis_y, 1.4, INK)
    for h in range(0, 25, 2):
        tx = x0 + (x1 - x0) * h / 24.0
        line(tx, axis_y - 3, tx, axis_y + 3, 1.2, INK)
        if h % 6 == 0:
            draw_text(tx, axis_y + 18, "%02d" % h, 8, DARK, False, "center")
    for i, (hour, label) in enumerate(TIMELINE):
        tx = x0 + (x1 - x0) * hour / 24.0
        disc(tx, axis_y, 2.6, RED)
        if i % 2 == 0:
            line(tx, axis_y - 8, tx, axis_y - 3, 1.0, DARK)
            draw_text(tx, axis_y - 24, label, 8.5, INK, True, "center")
        else:
            line(tx, axis_y + 3, tx, axis_y + 5, 1.0, DARK)
            draw_text(tx, axis_y + 6, label, 8.5, INK, True, "center")


def card(c, x, y, w, h):
    frame(x, y, w, h, 1.2, INK)
    rect(x, y, 21, 21, INK)
    draw_text(x + 10.5, y + 5.5, str(c["n"]), 11, WHITE, True, "center")
    draw_text(x + 27, y + 6, "%s \u2014 %s" % (c["place"], c["cat"]), 9.5, INK, True)
    tag_color = {"ON RECORD": BLUE, "REPORTED": DARK, "CLAIM": RED}[c["tag"]]
    draw_text(x + w - 7, y + 6, c["tag"], 8.5, tag_color, True, "right")
    draw_wrapped(x + 8, y + 20, c["head"], 12.5, w - 16, INK, 14.5, True, 2)
    draw_wrapped(x + 8, y + 50, c["body"], 9.5, w - 16, INK, 10.8, False, 3)
    draw_text(x + 8, y + h - 10.5, "SOURCE: " + c["src"], 7.5, DARK, True)


def cards():
    top = 264
    gap = 5
    ch = 96
    cw = (RX - MX - 2 * 12) / 3.0
    for i, c in enumerate(CARDS):
        col = i % 3
        row = i // 3
        x = MX + col * (cw + 12)
        y = top + row * (ch + gap)
        card(c, x, y, cw, ch)


def world_map(x, y, w, h):
    frame(x, y, w, h, 1.2, INK)
    draw_text(x + 9, y + 7, "WHERE IT HAPPENED \u2014 PINS MATCH THE NUMBERED STORIES",
              10, INK, True)
    ax, ay = x + 10, y + 27
    aw, ah = w - 20, h - 35

    def proj(lon, lat):
        return (ax + (lon + 170.0) / 360.0 * aw,
                ay + (84.0 - lat) / 142.0 * ah)

    lat = -57.0
    while lat <= 82.0:
        lon = -168.0
        while lon <= 186.0:
            if on_land(lon, lat):
                px, py = proj(lon, lat)
                disc(px, py, 1.55, LAND)
            lon += 3.0
        lat += 3.0
    for c in CARDS:
        px, py = proj(c["lon"], c["lat"])
        bx, by = px + c["dx"], py + c["dy"]
        line(px, py, bx, by, 0.9, RED)
        disc(px, py, 1.8, RED)
        disc(bx, by, 9.5, RED)
        draw_text(bx, by - 4.8, str(c["n"]), 9.5, WHITE, True, "center")


def numbers_box(x, y, w, h):
    frame(x, y, w, h, 1.2, INK)
    draw_text(x + 10, y + 8, "THE DAY IN NUMBERS", 13, RED, True)
    line(x + 10, y + 27, x + w - 10, y + 27, 1.1, RED)
    yy = y + 32
    for val, label in NUMBERS:
        draw_text(x + 10, yy, val, 13, INK, True)
        draw_text(x + 108, yy + 2.5, label, 9, DARK, True)
        yy += 18.0


def middle_band():
    y = 670
    h = 158
    world_map(MX, y, 528, h)
    numbers_box(568, y, RX - 568, h)


def briefs():
    y = 838
    line(MX, y, RX, y, 2.2, RED)
    draw_text(MX, y + 6, "ALSO ON TUESDAY \u2014 16 MORE STORIES IN BRIEF", 12.5, INK, True)
    yy = y + 28
    colw = (RX - MX - 24) / 2.0
    for i, b in enumerate(BRIEFS):
        col = i // 8
        row = i % 8
        x = MX + col * (colw + 24)
        draw_text(x, yy + row * 12.0, b, 9.5, INK, False)


def footer():
    y = 968
    frame(MX, y, RX - MX, 42, 1.2, INK)
    draw_text(MX + 9, y + 5,
              "DATE CHECK: EVERY STORY HERE HAPPENED, OR WAS FIRST REPORTED, ON "
              "TUESDAY 24 NOVEMBER 2026 (UTC).", 9.5, INK, True)
    draw_text(MX + 9, y + 19,
              "ITEMS FROM EARLIER DAYS WERE LEFT OUT. LEGEND: ON RECORD = SAID IN "
              "PUBLIC \u00b7 REPORTED = AGENCY REPORT \u00b7 CLAIM = ALLEGATION, UNVERIFIED.",
              9, DARK, False)


def build():
    masthead()
    chips()
    timeline()
    cards()
    middle_band()
    briefs()
    footer()

# --------------------------------------------------------------- output --

def downscale():
    out = bytearray(OW * OH * 3)
    rows = []
    for yy in range(H):
        i = yy * W * 3
        rows.append(bytes(img[i:i + W * 3]))
    for oy in range(OH):
        r0 = rows[oy * 4]
        r1 = rows[oy * 4 + 1]
        r2 = rows[oy * 4 + 2]
        r3 = rows[oy * 4 + 3]
        base_out = oy * OW * 3
        for ox in range(OW):
            b = ox * 12
            for ch in range(3):
                s = (sum(r0[b + ch:b + ch + 10:3]) + sum(r1[b + ch:b + ch + 10:3])
                     + sum(r2[b + ch:b + ch + 10:3]) + sum(r3[b + ch:b + ch + 10:3]))
                out[base_out + ox * 3 + ch] = s >> 4
    return bytes(out)


def png_bytes(rgb):
    raw = bytearray()
    stride = OW * 3
    for yy in range(OH):
        raw.append(0)
        raw += rgb[yy * stride:(yy + 1) * stride]

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        c += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return c

    ihdr = struct.pack(">IIBBBBB", OW, OH, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 6)) + chunk(b"IEND", b""))


def main():
    build()
    data = png_bytes(downscale())
    out = os.environ.get("MAKEFUN_OUTPUT", "/output/entry.png")
    d = os.path.dirname(out)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(out, "wb") as f:
        f.write(data)


if __name__ == "__main__":
    main()
