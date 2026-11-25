#!/usr/bin/env python3
"""news-image-20261124 entry: one day's world news on a single newspaper page.

Renders a broadsheet front page at 4096x4096 with a hand-built stroke font,
then averages 4x4 blocks down to 1024x1024 and writes a PNG.
Standard library only. Deterministic: no time, no randomness, no network.
"""

import math
import os
import struct
import zlib

SS = 4                 # supersampling factor
S = 4096               # internal canvas size
OUT_SIZE = 1024        # final image size

PAPER = (250, 248, 241)
INKC = (26, 25, 28)
REDC = (176, 28, 36)

# ---------------------------------------------------------------------------
# Stroke font.  Glyph space: x in 0..6, y in 0..10 (y grows downward).
# Cap top y=1.5, x-height top y=4, baseline y=8.5, descender y=10.
# Each glyph: (advance_units, "x,y x,y;x,y ...") strokes separated by ';'.
# ---------------------------------------------------------------------------

_FONT_SRC = {
    'A': (6.0, "0.6,8.5 3,1.5 5.4,8.5;1.7,5.8 4.3,5.8"),
    'B': (6.0, "1,1.5 1,8.5;1,1.5 3.6,1.5 4.8,2.3 4.8,3.9 3.8,4.9 1,4.9;"
              "1,4.9 3.8,4.9 5.1,5.8 5.1,7.4 3.9,8.5 1,8.5"),
    'C': (6.0, "5.2,2.6 4,1.6 2.6,1.8 1.4,3 1.2,5 1.4,7 2.6,8.3 4,8.4 5.2,7.4"),
    'D': (6.0, "1,1.5 1,8.5;1,1.5 3.6,1.5 5,5 3.6,8.5 1,8.5"),
    'E': (6.0, "5.2,1.5 1,1.5 1,8.5 5.2,8.5;1,5 4.4,5"),
    'F': (6.0, "5.2,1.5 1,1.5 1,8.5;1,5 4.2,5"),
    'G': (6.0, "5.2,2.6 4,1.6 2.6,1.8 1.4,3 1.2,5 1.4,7 2.6,8.3 4.2,8.4 "
              "5.3,7.2 5.3,5.4 3.6,5.4"),
    'H': (6.0, "1,1.5 1,8.5;5,1.5 5,8.5;1,5 5,5"),
    'I': (6.0, "3,1.5 3,8.5;1.6,1.5 4.4,1.5;1.6,8.5 4.4,8.5"),
    'J': (6.0, "3.6,1.5 5,1.5 5,6.8 4.2,8.4 2.6,8.5 1.4,7.6"),
    'K': (6.0, "1,1.5 1,8.5;5.2,1.5 1.2,5.2;1.9,4.4 5.3,8.5"),
    'L': (6.0, "1,1.5 1,8.5 5.2,8.5"),
    'M': (6.8, "0.8,8.5 0.8,1.5 3.4,4.6 6,1.5 6,8.5"),
    'N': (6.0, "0.8,8.5 0.8,1.5 5.2,8.5 5.2,1.5"),
    'O': (6.0, "3,1.5 4.4,1.9 5.2,3.4 5.2,6.6 4.4,8.1 3,8.5 1.6,8.1 "
              "0.8,6.6 0.8,3.4 1.6,1.9 3,1.5"),
    'P': (6.0, "1,1.5 1,8.5;1,1.5 3.8,1.5 5,2.6 5,4 3.9,5.1 1,5.1"),
    'Q': (6.0, "3,1.5 4.4,1.9 5.2,3.4 5.2,6.6 4.4,8.1 3,8.5 1.6,8.1 "
              "0.8,6.6 0.8,3.4 1.6,1.9 3,1.5;3.6,6.8 5.4,8.8"),
    'R': (6.0, "1,1.5 1,8.5;1,1.5 3.8,1.5 5,2.6 5,4 3.9,5.1 1,5.1;3.4,5.1 5.3,8.5"),
    'S': (6.0, "5.1,2.4 3.9,1.5 2.2,1.7 1.2,2.7 1.3,4 2.2,4.8 4,5.4 5,6.2 "
              "4.9,7.6 3.8,8.4 2,8.3 0.9,7.5"),
    'T': (6.0, "0.7,1.5 5.3,1.5;3,1.5 3,8.5"),
    'U': (6.0, "0.9,1.5 0.9,6.4 1.7,8.2 3,8.5 4.3,8.2 5.1,6.4 5.1,1.5"),
    'V': (6.0, "0.7,1.5 3,8.5 5.3,1.5"),
    'W': (6.8, "0.5,1.5 1.9,8.5 3.4,4.8 4.9,8.5 6.3,1.5"),
    'X': (6.0, "0.8,1.5 5.2,8.5;5.2,1.5 0.8,8.5"),
    'Y': (6.0, "0.7,1.5 3,4.8 5.3,1.5;3,4.8 3,8.5"),
    'Z': (6.0, "0.8,1.5 5.2,1.5 0.8,8.5 5.2,8.5"),
    'a': (6.0, "4.9,4.4 3.9,4 2.4,4.2 1.4,5.2 1.3,6.8 2,8.1 3.4,8.5 4.9,7.9 "
              "4.9,4.4;4.9,4.4 4.9,8.5"),
    'b': (6.0, "1.2,1.5 1.2,8.5;1.2,5.4 2.4,4.2 3.8,4.1 4.9,5 5.1,6.4 "
              "4.6,7.9 3.4,8.5 1.9,8.3 1.2,7.4"),
    'c': (6.0, "4.9,4.9 3.9,4.1 2.5,4.2 1.5,5.2 1.4,6.6 2,8 3.4,8.5 4.9,7.8"),
    'd': (6.0, "5,1.5 5,8.5;5,5.4 3.9,4.2 2.5,4.1 1.5,5 1.3,6.4 1.8,7.9 "
              "3.2,8.5 5,7.6"),
    'e': (6.0, "1.5,6.1 4.9,6.1 4.8,5 3.9,4.1 2.5,4.2 1.5,5.3 1.4,6.7 "
              "2,8.1 3.4,8.5 4.9,7.7"),
    'f': (6.0, "4.6,2.2 3.9,1.5 2.9,1.6 2.4,2.6 2.4,8.5;1.2,4.2 4.2,4.2"),
    'g': (6.0, "5,4.4 3.9,4.1 2.5,4.2 1.5,5.1 1.3,6.5 1.9,7.9 3.3,8.4 "
              "5,7.7 5,9 4.3,9.9 2.7,10 1.6,9.3;5,4.4 5,7.7"),
    'h': (6.0, "1.2,1.5 1.2,8.5;1.2,5.2 2.3,4.2 3.7,4.1 4.8,5 4.9,6.4 4.9,8.5"),
    'i': (3.2, "1.6,4.2 1.6,8.5;1.6,2 1.6,2.5"),
    'j': (3.6, "2.4,4.2 2.4,8.6 1.8,9.8 0.6,10 0.1,9.4;2.4,2 2.4,2.5"),
    'k': (6.0, "1.2,1.5 1.2,8.5;4.8,4.2 1.4,6.4;2.2,5.6 5,8.5"),
    'l': (3.2, "1.6,1.5 1.6,8.5"),
    'm': (6.6, "0.7,4.2 0.7,8.5;0.7,5.2 1.8,4.2 2.9,4.2 3.3,5 3.3,8.5;"
              "3.3,5.2 3.9,4.2 5,4.3 5.5,5.2 5.5,8.5"),
    'n': (6.0, "0.9,4.2 0.9,8.5;0.9,5.2 2.1,4.2 3.6,4.1 4.7,5 4.8,6.4 4.8,8.5"),
    'o': (6.0, "3,4.1 4.2,4.4 5,5.4 5,7.2 4.2,8.2 3,8.5 1.8,8.2 1,7.2 "
              "1,5.4 1.8,4.4 3,4.1"),
    'p': (6.0, "1.2,4.2 1.2,10;1.2,5.2 2.4,4.2 3.8,4.1 4.9,5 5.1,6.4 "
              "4.6,7.9 3.4,8.5 1.9,8.3 1.2,7.6"),
    'q': (6.0, "5,4.2 5,10;5,5.2 3.9,4.2 2.5,4.1 1.5,5 1.3,6.4 1.8,7.9 "
              "3.2,8.5 5,7.6"),
    'r': (6.0, "1.2,4.2 1.2,8.5;1.2,5.4 2.2,4.3 3.6,4.1 4.8,4.6"),
    's': (6.0, "4.8,4.7 3.8,4.1 2.3,4.2 1.4,5 1.8,6 3.2,6.5 4.6,7 4.7,8 "
              "3.7,8.5 2,8.4 1.1,7.8"),
    't': (6.0, "2.8,2.2 2.8,7.4 3.4,8.4 4.8,8.4;1.3,4.2 4.6,4.2"),
    'u': (6.0, "1,4.2 1,6.9 1.7,8.3 3,8.5 4.9,7.4 4.9,4.2;4.9,6.2 4.9,8.5"),
    'v': (6.0, "0.9,4.2 3,8.5 5.1,4.2"),
    'w': (6.6, "0.6,4.2 1.7,8.5 3,5.6 4.3,8.5 5.6,4.2"),
    'x': (6.0, "1,4.2 5,8.5;5,4.2 1,8.5"),
    'y': (6.0, "0.9,4.2 3,7.6 5.1,4.2;3,7.6 2.6,9.2 1.8,10 0.9,9.6"),
    'z': (6.0, "1,4.2 5,4.2 1,8.5 5,8.5"),
    '0': (6.0, "3,1.5 4.3,1.9 5,3.4 5,6.6 4.3,8.1 3,8.5 1.7,8.1 1,6.6 "
              "1,3.4 1.7,1.9 3,1.5"),
    '1': (5.6, "1.8,3 3.2,1.5 3.2,8.5;1.6,8.5 4.4,8.5"),
    '2': (6.0, "1.2,2.8 2,1.7 3.6,1.6 4.8,2.5 4.7,4 3.8,5.2 1,8.5 5.2,8.5"),
    '3': (6.0, "1.2,2.4 2.2,1.6 3.8,1.6 4.8,2.5 4.6,4 3.4,4.9 2.2,4.9;"
              "3.4,4.9 4.6,5.6 4.9,7 4,8.3 2.4,8.5 1.2,7.6"),
    '4': (6.0, "3.8,8.5 3.8,1.5 1,5.9 5.4,5.9"),
    '5': (6.0, "5,1.5 1.4,1.5 1.3,4.6 2.6,4.1 4.2,4.3 5,5.6 4.6,7.5 "
              "3.2,8.5 1.4,8 1,7"),
    '6': (6.0, "4.9,2.4 3.7,1.6 2.3,2.1 1.4,3.8 1.2,6.2 1.9,8 3.2,8.5 "
              "4.6,7.9 5.1,6.6 4.6,5.3 3.3,4.9 1.8,5.4"),
    '7': (6.0, "1,1.5 5.2,1.5 3.4,8.5"),
    '8': (6.0, "3,4.9 1.9,4.2 1.7,2.8 2.4,1.7 3.6,1.6 4.4,2.3 4.3,3.8 3,4.9 "
              "4.5,5.7 4.6,7.2 3.8,8.4 2.2,8.4 1.4,7.3 1.5,5.8 3,4.9"),
    '9': (6.0, "1.1,7.6 2.3,8.4 3.7,7.9 4.6,6.2 4.8,3.8 4.1,2 2.8,1.5 "
              "1.4,2.1 0.9,3.4 1.4,4.7 2.7,5.1 4.2,4.6"),
    ' ': (3.6, ""),
    '.': (3.0, "2.8,8.1 3.2,8.1"),
    ',': (3.0, "3.1,7.4 2.6,8.8"),
    "'": (2.6, "3,1.6 2.6,3.1"),
    '"': (4.6, "1.6,1.6 1.3,3.1;3.6,1.6 3.3,3.1"),
    '-': (6.0, "1.4,5.6 4.6,5.6"),
    '–': (6.0, "1,5.6 5,5.6"),
    '—': (6.4, "0.4,5.6 6,5.6"),
    ':': (3.0, "2.9,4.4 3.1,4.4;2.9,8.1 3.1,8.1"),
    ';': (3.0, "2.9,4.4 3.1,4.4;3.1,7.4 2.6,8.8"),
    '!': (3.0, "3,1.5 3,6.4;2.9,8.1 3.1,8.1"),
    '?': (6.0, "1.3,2.7 2.1,1.7 3.7,1.6 4.7,2.4 4.5,3.8 3,4.8 3,6;2.9,8.1 3.1,8.1"),
    '%': (6.4, "1.4,1.7 2.5,1.7 2.5,3 1.4,3 1.4,1.7;5.2,1.4 0.9,8.6;"
              "3.9,6.7 5,6.7 5,7.9 3.9,7.9 3.9,6.7"),
    '+': (6.0, "3,3.2 3,6.8;1.4,5 4.6,5"),
    '/': (6.0, "5,1.2 1,8.8"),
    '(': (6.0, "4.2,1.2 2.8,2.6 2.4,5 2.8,7.4 4.2,8.8"),
    ')': (6.0, "1.8,1.2 3.2,2.6 3.6,5 3.2,7.4 1.8,8.8"),
    '·': (3.0, "2.8,5.2 3.2,5.2"),
    '•': (3.4, "2.7,5 3.3,5"),
    '°': (6.0, "3,1.3 3.9,1.7 3.9,2.8 3,3.2 2.1,2.8 2.1,1.7 3,1.3"),
    '$': (6.0, "5.1,2.4 3.9,1.5 2.2,1.7 1.2,2.7 1.3,4 2.2,4.8 4,5.4 5,6.2 "
              "4.9,7.6 3.8,8.4 2,8.3 0.9,7.5;3,0.7 3,9.3"),
    '*': (6.0, "3,2.6 3,6.4;1.5,3.4 4.5,5.6;4.5,3.4 1.5,5.6"),
    '=': (6.0, "1.2,4.2 4.8,4.2;1.2,6 4.8,6"),
    '<': (6.0, "4.6,2.6 1.6,5 4.6,7.4"),
    '>': (6.0, "1.4,2.6 4.4,5 1.4,7.4"),
    '_': (6.0, "0.8,8.9 5.2,8.9"),
    '|': (2.6, "2,1.5 2,8.5"),
    '~': (6.0, "1,5.4 2.2,4.4 3.4,5.4 4.6,4.4"),
    '#': (6.0, "2.2,1.5 1.8,8.5;4.2,1.5 3.8,8.5;1,4 5.2,4;0.8,6.2 5,6.2"),
    '&': (6.4, "4.9,8.3 3.2,6 2,4.7 1.5,3.2 1.9,2 3.1,1.6 4.1,2.2 3.9,3.5 "
              "2.9,4.4 1.7,5.4 1.2,6.8 1.9,8.3 3.5,8.5 5.4,8.3"),
    'ü': (6.0, "1,4.2 1,6.9 1.7,8.3 3,8.5 4.9,7.4 4.9,4.2;4.9,6.2 4.9,8.5;"
              "1.8,2.2 2.1,2.2;3.9,2.2 4.2,2.2"),
    'é': (6.0, "1.5,6.1 4.9,6.1 4.8,5 3.9,4.1 2.5,4.2 1.5,5.3 1.4,6.7 "
              "2,8.1 3.4,8.5 4.9,7.7;3.4,2.6 4.6,1.4"),
    'á': (6.0, "4.9,4.4 3.9,4 2.4,4.2 1.4,5.2 1.3,6.8 2,8.1 3.4,8.5 4.9,7.9 "
              "4.9,4.4;4.9,4.4 4.9,8.5;3.4,2.6 4.6,1.4"),
    'í': (3.2, "1.6,4.2 1.6,8.5;2,2.6 3.1,1.4"),
}


def _parse_glyphs():
    out = {}
    for ch, (adv, spec) in _FONT_SRC.items():
        strokes = []
        if spec:
            for part in spec.split(';'):
                pts = []
                for pair in part.split():
                    xs, ys = pair.split(',')
                    pts.append((float(xs), float(ys)))
                if pts:
                    strokes.append(pts)
        out[ch] = (adv, strokes)
    return out


GLYPHS = _parse_glyphs()

_ALIASES = {'’': "'", '‘': "'", '“': '"', '”': '"', '−': '-', 'ʼ': "'"}


def _glyph(ch):
    ch = _ALIASES.get(ch, ch)
    return GLYPHS.get(ch, GLYPHS[' '])


def text_width(text, cap, tracking=0.3):
    """Width in final pixels of text drawn at the given cap height."""
    u = cap / 7.0
    w = 0.0
    for ch in text:
        adv, _ = _glyph(ch)
        w += (adv + tracking) * u
    return w - tracking * u if text else 0.0


def wrap_text(text, cap, maxw, tracking=0.3):
    """Greedy word wrap; returns a list of lines that fit maxw."""
    words = text.split()
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_width(trial, cap, tracking) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit_cap(text, cap, maxw, tracking=0.3):
    """Shrink cap height until the text fits on one line (or give up)."""
    while cap > 6.0 and text_width(text, cap, tracking) > maxw:
        cap -= 0.5
    return cap


# ---------------------------------------------------------------------------
# Canvas: three coverage planes (ink, red, erase) at 4096x4096.
# A plane byte is coverage 0..255; final colour composites paper -> red ->
# ink -> erase(paper), so dark strokes can be punched out of a red disc to
# leave paper-coloured numerals.
# ---------------------------------------------------------------------------

class Page(object):
    def __init__(self):
        self.ink = bytearray(S * S)
        self.red = bytearray(S * S)
        self.ers = bytearray(S * S)

    def _stamp(self, arr, cx, cy, half, val):
        """Filled square stamp; cx, cy, half are internal pixels."""
        x0 = int(cx - half)
        x1 = int(cx + half)
        y0 = int(cy - half)
        y1 = int(cy + half)
        if x0 < 0:
            x0 = 0
        if y0 < 0:
            y0 = 0
        if x1 > S:
            x1 = S
        if y1 > S:
            y1 = S
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes((val,)) * (x1 - x0)
        n = len(row)
        for y in range(y0, y1):
            i = y * S + x0
            arr[i:i + n] = row

    def line(self, arr, x0, y0, x1, y1, w, val=255):
        """Thick line; coordinates and width in final pixels."""
        ax, ay = x0 * SS, y0 * SS
        bx, by = x1 * SS, y1 * SS
        wi = w * SS
        dist = math.hypot(bx - ax, by - ay)
        steps = max(1, int(dist / (wi * 0.45)))
        half = wi / 2.0
        for i in range(steps + 1):
            t = i / steps
            self._stamp(arr, ax + (bx - ax) * t, ay + (by - ay) * t, half, val)

    def polyline(self, arr, pts, w, val=255):
        for i in range(len(pts) - 1):
            self.line(arr, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                      w, val)

    def rect(self, arr, x, y, w, h, val=255):
        """Filled rectangle; final-pixel coordinates."""
        x0 = int(x * SS)
        y0 = int(y * SS)
        x1 = int((x + w) * SS)
        y1 = int((y + h) * SS)
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(S, x1)
        y1 = min(S, y1)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes((val,)) * (x1 - x0)
        n = len(row)
        for yy in range(y0, y1):
            i = yy * S + x0
            arr[i:i + n] = row

    def disc(self, arr, cx, cy, r, val=255):
        """Filled disc; final-pixel centre and radius."""
        cx_i = cx * SS
        cy_i = cy * SS
        r_i = r * SS
        y0 = max(0, int(cy_i - r_i))
        y1 = min(S, int(cy_i + r_i) + 1)
        for yy in range(y0, y1):
            dy = yy - cy_i
            rem = r_i * r_i - dy * dy
            if rem < 0:
                continue
            half = int(math.sqrt(rem))
            x0 = max(0, int(cx_i) - half)
            x1 = min(S, int(cx_i) + half)
            if x1 <= x0:
                continue
            row = bytes((val,)) * (x1 - x0)
            i = yy * S + x0
            arr[i:i + len(row)] = row

    def text(self, x, ybase, text, cap, wgt, arr, val=255, tracking=0.3,
             align='l'):
        """Draw a single line of text; ybase is the baseline (final px)."""
        w = text_width(text, cap, tracking)
        if align == 'c':
            x -= w / 2.0
        elif align == 'r':
            x -= w
        u = cap / 7.0
        cx = x
        for ch in text:
            adv, strokes = _glyph(ch)
            for pts in strokes:
                scaled = [(cx + gx * u, ybase + (gy - 8.5) * u)
                          for gx, gy in pts]
                if len(scaled) == 1:
                    px, py = scaled[0]
                    self.line(arr, px, py, px + 0.01, py, wgt, val)
                else:
                    self.polyline(arr, scaled, wgt, val)
            cx += (adv + tracking) * u
        return w


# ---------------------------------------------------------------------------
# Downsample one coverage plane by 4x4 area average.
# ---------------------------------------------------------------------------

def box_down(b):
    out = bytearray(OUT_SIZE * OUT_SIZE)
    for by in range(OUT_SIZE):
        band = b[by * SS * S:(by + 1) * SS * S]
        if not any(band):
            continue
        acc = None
        for r in range(SS):
            row = b[(by * SS + r) * S:(by * SS + r) * S + S]
            hs = [p + q + s + t for p, q, s, t in
                  zip(row[0::4], row[1::4], row[2::4], row[3::4])]
            if acc is None:
                acc = hs
            else:
                acc = [a + h for a, h in zip(acc, hs)]
        base = by * OUT_SIZE
        out[base:base + OUT_SIZE] = bytes(v >> 4 for v in acc)
    return out


def finish_png(pg):
    ink = box_down(pg.ink)
    red = box_down(pg.red)
    ers = box_down(pg.ers)
    rgb = bytearray(OUT_SIZE * OUT_SIZE * 3)
    pr, pg_, pb = PAPER
    ir, ig, ib = INKC
    rr, rg, rb = REDC
    for i in range(OUT_SIZE * OUT_SIZE):
        a = ink[i]
        b = red[i]
        e = ers[i]
        if a == 0 and b == 0 and e == 0:
            r, g, bl = pr, pg_, pb
        else:
            r, g, bl = float(pr), float(pg_), float(pb)
            if b:
                bf = b / 255.0
                r += (rr - r) * bf
                g += (rg - g) * bf
                bl += (rb - bl) * bf
            if a:
                af = a / 255.0
                r += (ir - r) * af
                g += (ig - g) * af
                bl += (ib - bl) * af
            if e:
                ef = e / 255.0
                r += (pr - r) * ef
                g += (pg_ - g) * ef
                bl += (pb - bl) * ef
            r, g, bl = int(r + 0.5), int(g + 0.5), int(bl + 0.5)
        j = i * 3
        rgb[j] = r
        rgb[j + 1] = g
        rgb[j + 2] = bl
    raw = bytearray()
    stride = OUT_SIZE * 3
    for y in range(OUT_SIZE):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        c += struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
        return c

    ihdr = struct.pack(">IIBBBBB", OUT_SIZE, OUT_SIZE, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + \
        chunk(b"IDAT", comp) + chunk(b"IEND", b"")
    return png


# ---------------------------------------------------------------------------
# Content: the day's stories, written from the wire facts of 24 Nov 2026.
# (place line, status tag, headline, summary, source line)
# ---------------------------------------------------------------------------

CARDS = [
    ("BRUSSELS, BELGIUM — DEFENCE", "ON RECORD",
     "NATO's Shield Now Reaches Into Orbit",
     "Rutte said NATO's defence pledge now stretches into orbit, amid "
     "reports Russia is readying a nuclear-armed satellite.",
     "NATO HQ BRIEFING"),
    ("MOSCOW, RUSSIA — DIPLOMACY", "CLAIM",
     "Moscow: Estonia Nears a War Trigger",
     "Russia accused its Baltic neighbour of hostile acts and said the "
     "two now stand close to an open trigger for war.",
     "RUSSIAN FOREIGN MINISTRY"),
    ("BENGHAZI, LIBYA — CONFLICT", "ON RECORD",
     "Libya Demands Answers Over Ship Strike",
     "Tripoli's unity government demanded Kyiv explain an attack on "
     "Russian vessels off Benghazi and the use of Libyan soil.",
     "LIBYAN GOVERNMENT STATEMENT"),
    ("SANA'A, YEMEN — HUMANITARIAN", "REPORTED",
     "360,000 Displaced in Yemen Since August",
     "UN counts put the displaced since August at 360,000, with 323 "
     "civilian casualties recorded — 76 of them dead.",
     "UN RELIEF FIGURES"),
    ("NAYPYIDAW, MYANMAR — LAW", "ON RECORD",
     "14 Nations: Court Ruling Binds Myanmar",
     "Foreign ministers of 14 countries said the World Court ruling "
     "recognising the Rohingya genocide binds Myanmar.",
     "JOINT MINISTERIAL STATEMENT"),
    ("SEOUL, KOREA — AIR DEFENCE", "REPORTED",
     "Russian Jets Enter Korea's Air Zone",
     "Seoul scrambled fighters as Russian aircraft entered its air "
     "defence zone over the East Sea, and lodged a protest.",
     "SOUTH KOREAN MILITARY"),
    ("VILLAVICENCIO, COLOMBIA", "REPORTED",
     "Car Bomb Wrecks Government Building",
     "A car bomb destroyed a government building in Villavicencio, "
     "capital of Meta. Casualty figures were still unconfirmed.",
     "REGIONAL AUTHORITIES, META"),
    ("OREGON, USA — TECH LAW", "CLAIM",
     "Two States Sue SpaceX Over Grok Images",
     "Oregon and Virginia have sued SpaceX, alleging its Grok AI "
     "generated child abuse imagery.",
     "COURT FILINGS, TWO STATES"),
    ("STRAIT OF HORMUZ — SEA LANES", "ON RECORD",
     "Record Attacks Roil Strait of Hormuz",
     "Britain said Iranian attacks around the strait — the world's "
     "great oil chokepoint — are running at record levels.",
     "UK GOVERNMENT STATEMENT"),
    ("GAZA CITY — CONFLICT", "REPORTED",
     "Israeli Strikes Kill Three in Gaza",
     "At least three people were killed in Israeli attacks; one of "
     "the dead was an employee of UNRWA, the UN relief agency.",
     "HEALTH OFFICIALS IN GAZA"),
    ("TOKYO, JAPAN — MARKETS", "REPORTED",
     "Nikkei Leaps 3.91% on Chip Surge",
     "Tokyo's Nikkei leapt 3.91% and Seoul's Kospi 6% as chip shares "
     "surged a day after Nvidia chief Jensen Huang's visit.",
     "MARKET DATA, TOKYO AND SEOUL"),
    ("KATHMANDU, NEPAL — QUAKE", "REPORTED",
     "Magnitude 5.6 Quake Hits Eastern Nepal",
     "A magnitude 5.6 earthquake struck Koshi province in the east "
     "of the country, close to the border with China.",
     "US GEOLOGICAL SURVEY"),
]

BRIEFS = [
    "Merz: Europe is ready to talk with Russia; advisers may meet in Abu Dhabi.",
    "Leaked data puts Russian dead in Ukraine at nearly 500,000 soldiers.",
    "Türkiye builds a scheme to keep Black Sea merchant shipping safe.",
    "Finland summons Russia's ambassador over 'unacceptable' actions.",
    "EU adds The Base's founder, a neo-Nazi, to its terror sanctions list.",
    "Senate panel probes VP Vance's links to a Venezuela oil contract.",
    "US blacklists Megaspeed over the Nvidia spy allegations.",
    "WFP chief: war puts food aid for 7.3 million more people at risk.",
    "Ousted PM Hasina plans a 16 December return, facing a death sentence.",
    "Indonesia charges a former police chief with treason.",
    "First foreign astronaut on Tiangong: Pakistan's Zeeshan Ali, on Shenzhou-24.",
    "Macron proposes a strategic stockpile of rare earths.",
    "Hernández de Cos is the frontrunner to lead the ECB.",
    "Measles claims a 9th life; the outbreak now spans 46 counties.",
    "Guterres seeks a multilateral AI-risk framework within a year.",
    "The US is confirmed as host of the 2031 Women's World Cup.",
]

NUMBERS = [
    ("360,000", "displaced in Yemen since August"),
    ("~500,000", "Russian war dead, leaked data"),
    ("14", "nations back the ICJ Myanmar ruling"),
    ("7.3M", "more facing loss of food aid"),
    ("+3.91%", "the Nikkei's one-day leap in Tokyo"),
    ("M5.6", "quake in Nepal's Koshi province"),
]

CHIPS = ["EUROPE 9", "ASIA 7", "AMERICAS 6", "MIDDLE EAST 3",
         "WORLD 2", "AFRICA 1"]

# Dotted world map: continent blobs as (lon centre, lat centre, lon radius,
# lat radius).  A grid point inside any blob earns a dot.
BLOBS = [
    (-100, 48, 38, 16), (-85, 38, 22, 10), (-95, 30, 16, 7),
    (-102, 23, 12, 6), (-152, 64, 14, 7), (-42, 72, 13, 7),
    (-79, 50, 16, 10),
    (-62, -12, 13, 17), (-70, -25, 8, 12), (-58, -2, 10, 7),
    (15, 50, 20, 8), (3, 43, 9, 4), (13, 42, 5, 4), (16, 63, 11, 7),
    (-2, 53, 4, 4),
    (20, 6, 20, 20), (18, 22, 20, 9), (25, -18, 13, 10), (47, -19, 3, 6),
    (60, 50, 45, 14), (95, 48, 30, 12), (78, 21, 10, 9),
    (104, 32, 14, 10), (112, 15, 8, 6), (138, 37, 4, 6), (128, 37, 3, 3),
    (107, -2, 10, 3), (120, -2, 8, 3), (131, -3, 6, 3),
    (45, 24, 10, 7), (32, 39, 8, 3), (150, 62, 25, 9),
    (134, -25, 13, 8), (147, -32, 6, 5), (172, -42, 4, 4),
]

# Card pin positions (lon, lat), matching CARDS order.
PINS = [
    (4.3, 50.8), (24.7, 59.4), (20.1, 32.1), (44.2, 15.4),
    (96.0, 21.9), (127.0, 37.6), (-73.6, 4.1), (-123.5, 44.0),
    (56.3, 26.5), (34.3, 31.4), (139.7, 35.7), (85.3, 27.7),
]


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

M = 30.0            # page margin
PAGE_W = 1024.0


def draw_masthead(pg):
    cx = PAGE_W / 2.0
    pg.text(cx, 42, "ONE DAY · ONE PAGE · THE WHOLE WORLD", 12.5, 2.4,
            pg.red, align='c', tracking=0.9)
    cap = fit_cap("THE DAILY WORLD", 60, PAGE_W - 2 * M, 0.4)
    pg.text(cx, 106, "THE DAILY WORLD", cap, 3.4, pg.ink, align='c',
            tracking=0.4)
    pg.text(cx, 140, "TUESDAY 24 NOVEMBER 2026", 24, 2.8, pg.red,
            align='c', tracking=0.8)
    pg.text(cx, 162, "28 STORIES · SIX REGIONS · EVERY STORY FROM THIS "
            "ONE DAY", 9.5, 1.5, pg.ink, align='c', tracking=0.6)
    pg.rect(pg.ink, M, 172, PAGE_W - 2 * M, 2.6)
    pg.rect(pg.ink, M, 178, PAGE_W - 2 * M, 0.9)


def draw_chips(pg):
    caps = 10.0
    gap = 10.0
    widths = [text_width(c, caps, 0.5) + 20 for c in CHIPS]
    total = sum(widths) + gap * (len(CHIPS) - 1)
    x = (PAGE_W - total) / 2.0
    y = 190.0
    for label, w in zip(CHIPS, widths):
        pg.rect(pg.ink, x, y, w, 1.0)
        pg.rect(pg.ink, x, y + 23, w, 1.0)
        pg.rect(pg.ink, x, y, 1.0, 24)
        pg.rect(pg.ink, x + w - 1, y, 1.0, 24)
        pg.text(x + w / 2.0, y + 16.5, label, caps, 1.6, pg.ink,
                align='c', tracking=0.5)
        x += w + gap


def draw_timeline(pg):
    ybase = 240.0
    pg.text(M, ybase, "THE DAY IN UTC", 10.5, 1.9, pg.ink, tracking=0.6)
    x0 = M + 150.0
    x1 = PAGE_W - M
    axis_y = ybase - 3.5
    pg.line(pg.ink, x0, axis_y, x1, axis_y, 1.1)
    for h in range(0, 25, 4):
        tx = x0 + (x1 - x0) * h / 24.0
        pg.line(pg.ink, tx, axis_y - 3, tx, axis_y + 3, 1.1)
        pg.text(tx, ybase + 13, "%02d" % h, 8.0, 1.3, pg.ink, align='c')
    for i in range(14):
        tx = x0 + (x1 - x0) * (i + 0.5) / 14.0
        pg.disc(pg.red, tx, axis_y, 2.4)


def draw_card(pg, idx, x, y, w):
    place, status, head, summ, src = CARDS[idx]
    pg.line(pg.ink, x, y, x + w, y, 2.2)
    # number disc with paper-coloured numeral
    dcx, dcy = x + 12, y + 16
    pg.disc(pg.red, dcx, dcy, 10.5)
    pg.text(dcx, dcy + 3.8, str(idx + 1), 10.5, 2.0, pg.ers, align='c')
    status_w = text_width(status, 7.8, 0.4)
    pcap = fit_cap(place, 8.8, w - 29 - status_w - 12, 0.4)
    pg.text(x + 29, y + 20, place, pcap, 1.6, pg.ink, tracking=0.4)
    pg.text(x + w, y + 20, status, 7.8, 1.6, pg.red, tracking=0.4,
            align='r')
    hcap = 13.0
    hlines = wrap_text(head, hcap, w, 0.15)
    while len(hlines) > 2 and hcap > 10.0:
        hcap -= 0.5
        hlines = wrap_text(head, hcap, w, 0.15)
    by = y + 40
    for ln in hlines[:2]:
        pg.text(x, by, ln, hcap, 2.2, pg.ink, tracking=0.15)
        by += 17.5
    slines = wrap_text(summ, 9.0, w, 0.25)
    sy = y + 73 if len(hlines) > 1 else y + 57
    for ln in slines[:3]:
        pg.text(x, sy, ln, 9.0, 1.35, pg.ink, tracking=0.25)
        sy += 12.2
    pg.text(x, y + 112, src, 7.8, 1.3, pg.ink, val=150, tracking=0.5)


def draw_cards(pg):
    top = 262.0
    gapx, gapy = 14.0, 10.0
    w = (PAGE_W - 2 * M - 2 * gapx) / 3.0
    h = 110.0
    for i in range(12):
        col = i % 3
        row = i // 3
        draw_card(pg, i, M + col * (w + gapx), top + row * (h + gapy), w)


def draw_briefs(pg):
    x0 = M
    y = 736.0
    pg.text(x0, y + 16, "ALSO ON TUESDAY", 13, 2.4, pg.ink, tracking=0.5)
    pg.line(pg.red, x0, y + 24, x0 + 616, y + 24, 2.0)
    colw = 300.0
    rows_top = y + 34
    pitch = 23.5
    for i, brief in enumerate(BRIEFS):
        col = 0 if i < 8 else 1
        row = i % 8
        bx = x0 + col * (colw + 16)
        by = rows_top + row * pitch
        pg.text(bx, by + 10, str(i + 13), 8.6, 1.9, pg.red, tracking=0.2)
        lines = wrap_text(brief, 8.6, colw - 26, 0.25)
        ly = by + 10
        for ln in lines[:2]:
            pg.text(bx + 26, ly, ln, 8.6, 1.3, pg.ink, tracking=0.25)
            ly += 11.0


def draw_numbers(pg):
    x = 662.0
    w = PAGE_W - M - x
    y = 736.0
    pg.text(x, y + 16, "THE DAY IN NUMBERS", 12.5, 2.4, pg.ink,
            tracking=0.4)
    pg.line(pg.red, x, y + 24, x + w, y + 24, 2.0)
    ry = y + 42
    for num, label in NUMBERS:
        pg.text(x, ry, num, 12.5, 2.1, pg.red, tracking=0.1)
        pg.text(x + 96, ry, label, 8.3, 1.3, pg.ink, tracking=0.25)
        ry += 16.5


def draw_map(pg):
    x = 662.0
    w = PAGE_W - M - x
    y = 890.0
    h = 56.0
    pg.text(x, 882, "WHERE IT HAPPENED — PINS MATCH THE CARDS", 8.6,
            1.6, pg.ink, tracking=0.4)
    lat_top, lat_bot = 78.0, -58.0

    def proj(lon, lat):
        px = x + (lon + 180.0) / 360.0 * w
        py = y + (lat_top - lat) / (lat_top - lat_bot) * h
        return px, py

    lon = -176.0
    while lon <= 178.0:
        lat = 76.0
        while lat >= -54.0:
            for clon, clat, rlon, rlat in BLOBS:
                dlon = (lon - clon) / rlon
                dlat = (lat - clat) / rlat
                if dlon * dlon + dlat * dlat <= 1.0:
                    px, py = proj(lon, lat)
                    pg.disc(pg.ink, px, py, 1.4, val=170)
                    break
            lat -= 5.0
        lon += 4.4
    for i, (lon, lat) in enumerate(PINS):
        px, py = proj(lon, lat)
        pg.disc(pg.red, px, py, 7.6)
        pg.text(px, py + 2.7, str(i + 1), 7.4, 1.7, pg.ers, align='c')


def draw_footer(pg):
    y = 958.0
    pg.rect(pg.ink, M, y, PAGE_W - 2 * M, 1.6)
    left = ("DATE CHECK — Every story on this page happened, or was first "
            "reported, on Tuesday 24 November 2026 (UTC). Earlier days "
            "are excluded.")
    lines = wrap_text(left, 8.4, 545, 0.25)
    ly = y + 16
    for ln in lines[:2]:
        pg.text(M, ly, ln, 8.4, 1.3, pg.ink, tracking=0.25)
        ly += 11.5
    legend = "ON RECORD = said by officials · REPORTED = from news reports"
    legend2 = "CLAIM = one side's allegation · Drawn in code — no photographs"
    pg.text(PAGE_W - M, y + 16, legend, 7.9, 1.3, pg.ink, align='r',
            tracking=0.25)
    pg.text(PAGE_W - M, y + 27.5, legend2, 7.9, 1.3, pg.ink, align='r',
            tracking=0.25)


def render():
    pg = Page()
    draw_masthead(pg)
    draw_chips(pg)
    draw_timeline(pg)
    draw_cards(pg)
    draw_briefs(pg)
    draw_numbers(pg)
    draw_map(pg)
    draw_footer(pg)
    return finish_png(pg)


def main():
    data = render()
    out = os.environ.get("ENTRY_OUT", "/output/entry.png")
    parent = os.path.dirname(out)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(out, "wb") as fh:
        fh.write(data)


if __name__ == "__main__":
    main()
