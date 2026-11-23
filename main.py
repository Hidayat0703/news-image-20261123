#!/usr/bin/env python3
"""news-image-20261123: draws one 1024x1024 PNG summing up the world's news
of Monday 23 November 2026. Python 3 stdlib only, no network, deterministic:
two runs write byte-identical output.

Layout (1024x1024): masthead / region strip / 3 hero cards with drawn
illustrations / world map with numbered pins + day-in-numbers panel /
2 rows x 5 small cards with illustrations / 37 numbered one-line briefs /
sources footer. 50 stories total, all verified from reporting dated
23 November 2026 (events that happened or were first reported that day).
"""
import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
PAPER   = (247, 243, 234)   # warm newsprint
INK     = (26, 26, 26)
MUTED   = (90, 86, 78)
RULE    = (180, 172, 156)
CARD    = (255, 255, 255)
CARD_BG = (250, 247, 240)

REGION = {
    "EUROPE":  (31,  90, 180),   # blue
    "AMERICAS": (22, 138,  86),   # green
    "ASIA":    (214, 116,  20),   # orange
    "MIDEAST": (178,  34,  34),   # red
    "AFRICA":  (112,  70, 158),   # purple
    "OCEANIA": (12,  140, 148),   # teal
    "SPACE":   (110,  70, 180),   # violet
    "MARKETS": (160, 120,   0),   # gold
    "WORLD":   (90,  90,  90),    # grey
}

# ---------------------------------------------------------------- canvas
px = bytearray(W * H * 3)
for i in range(0, len(px), 3):
    px[i], px[i + 1], px[i + 2] = PAPER


def set_px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        o = (y * W + x) * 3
        px[o], px[o + 1], px[o + 2] = c


def fill_rect(x, y, w, h, c):
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    for yy in range(y0, y1):
        o = (yy * W + x0) * 3
        for xx in range(x0, x1):
            px[o], px[o + 1], px[o + 2] = c
            o += 3


def hline(x, y, w, c):
    fill_rect(x, y, w, 1, c)


def vline(x, y, h, c):
    fill_rect(x, y, 1, h, c)


def line(x0, y0, x1, y1, c):
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        set_px(x0, y0, c)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


def circle(cx, cy, r, c, fill=True):
    for yy in range(cy - r, cy + r + 1):
        for xx in range(cx - r, cx + r + 1):
            d = (xx - cx) ** 2 + (yy - cy) ** 2
            if fill:
                if d <= r * r:
                    set_px(xx, yy, c)
            else:
                if r * r - 2 * r <= d <= r * r:
                    set_px(xx, yy, c)


def ellipse(cx, cy, rx, ry, c):
    for yy in range(cy - ry, cy + ry + 1):
        for xx in range(cx - rx, cx + rx + 1):
            if ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1:
                set_px(xx, yy, c)


def poly(points, c):
    """Scanline fill of a polygon given as [(x, y), ...]."""
    if len(points) < 3:
        return
    ys = [p[1] for p in points]
    for y in range(min(ys), max(ys) + 1):
        xs = []
        n = len(points)
        for i in range(n):
            x0, y0 = points[i]
            x1, y1 = points[(i + 1) % n]
            if (y0 <= y < y1) or (y1 <= y < y0):
                xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            for x in range(int(xs[i]), int(xs[i + 1]) + 1):
                set_px(x, y, c)


def triangle(p1, p2, p3, c):
    poly([p1, p2, p3], c)


# ---------------------------------------------------------------- 5x7 font
# Each glyph: 7 rows, each a 5-bit integer (bit 4 = leftmost pixel).
def _g(*rows):
    return rows


FONT = {
    "A": _g(0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    "B": _g(0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110),
    "C": _g(0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110),
    "D": _g(0b11110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b11110),
    "E": _g(0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111),
    "F": _g(0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000),
    "G": _g(0b01110, 0b10001, 0b10000, 0b10111, 0b10001, 0b10001, 0b01111),
    "H": _g(0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    "I": _g(0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    "J": _g(0b00111, 0b00010, 0b00010, 0b00010, 0b00010, 0b10010, 0b01100),
    "K": _g(0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001),
    "L": _g(0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111),
    "M": _g(0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001),
    "N": _g(0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001, 0b10001),
    "O": _g(0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    "P": _g(0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000),
    "Q": _g(0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10010, 0b01101),
    "R": _g(0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001),
    "S": _g(0b01111, 0b10000, 0b10000, 0b01110, 0b00001, 0b00001, 0b11110),
    "T": _g(0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100),
    "U": _g(0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    "V": _g(0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100),
    "W": _g(0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b10101, 0b01010),
    "X": _g(0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001),
    "Y": _g(0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100),
    "Z": _g(0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111),
    "0": _g(0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110),
    "1": _g(0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    "2": _g(0b01110, 0b10001, 0b00001, 0b00110, 0b01000, 0b10000, 0b11111),
    "3": _g(0b11111, 0b00010, 0b00100, 0b00010, 0b00001, 0b10001, 0b01110),
    "4": _g(0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010),
    "5": _g(0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110),
    "6": _g(0b00110, 0b01000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110),
    "7": _g(0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000),
    "8": _g(0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110),
    "9": _g(0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00010, 0b01100),
    " ": _g(0, 0, 0, 0, 0, 0, 0),
    ".": _g(0, 0, 0, 0, 0, 0b01100, 0b01100),
    ",": _g(0, 0, 0, 0, 0b01100, 0b00100, 0b01000),
    ":": _g(0, 0b01100, 0b01100, 0, 0b01100, 0b01100, 0),
    ";": _g(0, 0b01100, 0b01100, 0, 0b01100, 0b00100, 0b01000),
    "!": _g(0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0, 0b00100),
    "?": _g(0b01110, 0b10001, 0b00001, 0b00110, 0b00100, 0, 0b00100),
    "'": _g(0b00100, 0b00100, 0b01000, 0, 0, 0, 0),
    '"': _g(0b01010, 0b01010, 0b01010, 0, 0, 0, 0),
    "-": _g(0, 0, 0, 0b01110, 0, 0, 0),
    "(": _g(0b00010, 0b00100, 0b01000, 0b01000, 0b01000, 0b00100, 0b00010),
    ")": _g(0b01000, 0b00100, 0b00010, 0b00010, 0b00010, 0b00100, 0b01000),
    "/": _g(0b00001, 0b00010, 0b00010, 0b00100, 0b01000, 0b01000, 0b10000),
    "%": _g(0b11001, 0b11010, 0b00010, 0b00100, 0b01000, 0b01011, 0b10011),
    "$": _g(0b00100, 0b01111, 0b10100, 0b01110, 0b00101, 0b11110, 0b00100),
    "&": _g(0b01100, 0b10010, 0b10100, 0b01000, 0b10101, 0b10010, 0b01101),
    "+": _g(0, 0b00100, 0b00100, 0b11111, 0b00100, 0b00100, 0),
    "=": _g(0, 0, 0b11111, 0, 0b11111, 0, 0),
    "*": _g(0, 0b10101, 0b01110, 0b11111, 0b01110, 0b10101, 0),
    "#": _g(0b01010, 0b01010, 0b11111, 0b01010, 0b11111, 0b01010, 0b01010),
    "@": _g(0b01110, 0b10001, 0b10111, 0b10101, 0b10110, 0b10000, 0b01110),
    "|": _g(0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100),
}


def text_w(s, scale=1):
    return len(s) * 6 * scale - scale


def draw_text(x, y, s, scale=1, color=INK):
    s = s.upper()
    cx = x
    for ch in s:
        g = FONT.get(ch)
        if g is None:
            cx += 6 * scale
            continue
        for r in range(7):
            row = g[r]
            for c in range(5):
                if row & (1 << (4 - c)):
                    fill_rect(cx + c * scale, y + r * scale, scale, scale, color)
        cx += 6 * scale


def draw_text_centered(x, y, w, s, scale=1, color=INK):
    draw_text(x + (w - text_w(s, scale)) // 2, y, s, scale, color)


def wrap_text(s, max_chars):
    words = s.split(" ")
    lines, cur = [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if len(trial) <= max_chars:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def text_block(x, y, s, max_chars, scale=1, color=INK, leading=None):
    lh = leading if leading is not None else 9 * scale
    for i, ln in enumerate(wrap_text(s, max_chars)):
        draw_text(x, y + i * lh, ln, scale, color)
    return len(wrap_text(s, max_chars))


# ---------------------------------------------------------------- PNG encode
def _crc(data):
    return zlib.crc32(data) & 0xFFFFFFFF


def _chunk(typ, data):
    return struct.pack(">I", len(data)) + typ + data + struct.pack(">I", _crc(typ + data))


def encode_png():
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter: none
        raw += px[y * W * 3:(y + 1) * W * 3]
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + _chunk(b"IEND", b""))

# ---------------------------------------------------------------- world map
# Coarse continent outlines as (lon, lat) lists; equirectangular projection.
MAP_X, MAP_Y, MAP_W, MAP_H = 14, 306, 646, 158
SEA = (214, 230, 238)
LAND = (232, 222, 200)
LAND_EDGE = (170, 158, 130)


def map_xy(lon, lat):
    return (MAP_X + int((lon + 180) / 360 * MAP_W),
            MAP_Y + int((90 - lat) / 180 * MAP_H))


CONTINENTS = [
    # North America
    [(-168, 66), (-140, 70), (-120, 72), (-95, 80), (-85, 80), (-75, 72),
     (-65, 60), (-55, 52), (-60, 47), (-70, 42), (-75, 35), (-80, 32),
     (-81, 26), (-90, 21), (-97, 16), (-92, 14), (-83, 9), (-79, 9),
     (-83, 15), (-90, 14), (-97, 16), (-105, 20), (-110, 23), (-114, 29),
     (-120, 34), (-125, 40), (-124, 48), (-130, 55), (-150, 60), (-165, 60)],
    # Greenland
    [(-55, 60), (-45, 60), (-40, 64), (-32, 68), (-25, 70), (-20, 74),
     (-25, 76), (-40, 78), (-55, 76), (-58, 70), (-55, 64)],
    # South America
    [(-79, 9), (-72, 12), (-62, 10), (-52, 5), (-50, 0), (-44, -3),
     (-35, -8), (-38, -15), (-40, -22), (-48, -28), (-57, -35), (-65, -41),
     (-68, -50), (-70, -54), (-73, -50), (-73, -37), (-71, -30), (-70, -18),
     (-77, -12), (-80, -5), (-81, 0), (-79, 7)],
    # Europe
    [(-10, 36), (-9, 43), (-2, 48), (-4, 50), (0, 51), (3, 53), (8, 57),
     (10, 59), (18, 56), (21, 55), (24, 59), (30, 60), (30, 70), (25, 71),
     (18, 70), (12, 66), (5, 60), (5, 58), (-2, 57), (-5, 50), (-10, 43),
     (-9, 37)],
    # Africa
    [(-6, 35), (10, 37), (20, 32), (32, 31), (35, 28), (37, 22), (43, 12),
     (48, 11), (51, 10), (44, 0), (40, -10), (35, -18), (32, -26),
     (26, -33), (19, -35), (15, -27), (12, -18), (9, -1), (9, 4), (-8, 4),
     (-13, 8), (-17, 15), (-16, 20), (-15, 27), (-10, 31)],
    # Asia
    [(30, 70), (40, 73), (60, 73), (70, 72), (90, 75), (110, 76),
     (130, 72), (160, 70), (178, 66), (170, 60), (162, 56), (158, 52),
     (142, 50), (140, 40), (135, 35), (130, 33), (127, 35), (122, 38),
     (120, 32), (122, 28), (120, 23), (110, 20), (108, 18), (105, 10),
     (103, 8), (100, 7), (98, 10), (95, 16), (92, 21), (89, 22), (86, 20),
     (80, 15), (77, 8), (75, 12), (72, 20), (68, 23), (66, 25), (61, 25),
     (57, 26), (52, 26), (50, 29), (48, 30), (44, 29), (40, 31), (36, 36),
     (35, 36), (30, 36), (28, 41), (27, 41), (23, 40), (20, 40), (18, 42),
     (15, 44), (12, 45), (8, 44), (3, 43), (0, 40), (-2, 37), (-6, 36),
     (-10, 36)],
    # Australia
    [(113, -22), (114, -30), (115, -35), (120, -34), (129, -32), (132, -32),
     (135, -35), (137, -35), (140, -38), (142, -39), (147, -39), (150, -37),
     (153, -32), (153, -27), (150, -23), (146, -19), (142, -15), (142, -11),
     (137, -12), (135, -12), (132, -11), (130, -13), (126, -14), (122, -17),
     (118, -20)],
    # United Kingdom
    [(-5, 50), (-3, 53), (-5, 56), (-3, 58), (-1, 57), (0, 53), (1, 51)],
    # Japan
    [(130, 31), (133, 34), (137, 35), (140, 38), (141, 41), (143, 43),
     (141, 45)],
    # New Zealand
    [(167, -45), (170, -42), (174, -38), (177, -38), (175, -41), (172, -43),
     (168, -46)],
]


def draw_map():
    fill_rect(MAP_X - 4, MAP_Y - 4, MAP_W + 8, MAP_H + 8, CARD)
    fill_rect(MAP_X, MAP_Y, MAP_W, MAP_H, SEA)
    for cont in CONTINENTS:
        pts = [map_xy(lon, lat) for lon, lat in cont]
        poly(pts, LAND)
        for i in range(len(pts)):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % len(pts)]
            line(x0, y0, x1, y1, LAND_EDGE)
    # graticule
    for lon in range(-150, 151, 30):
        x, _ = map_xy(lon, 0)
        for yy in range(MAP_Y, MAP_Y + MAP_H, 4):
            set_px(x, yy, (190, 208, 216))
    for lat in (-60, -30, 0, 30, 60):
        _, y = map_xy(0, lat)
        for xx in range(MAP_X, MAP_X + MAP_W, 4):
            set_px(xx, y, (190, 208, 216))
    # Indonesia dots
    for lon, lat in [(95, 5), (100, 0), (105, -5), (110, -7), (115, -8),
                     (120, -10), (125, -9), (130, -3), (135, -4), (140, -8)]:
        x, y = map_xy(lon, lat)
        ellipse(x, y, 4, 2, LAND)


def draw_pin(num, lon, lat, color, dx=0, dy=0):
    """Numbered pin; dx/dy shift the label bubble off the true point."""
    x, y = map_xy(lon, lat)
    circle(x, y, 3, INK)
    circle(x, y, 2, color)
    bx, by = x + dx, y + dy
    if dx or dy:
        line(x, y, bx, by, INK)
    label = str(num)
    bw = len(label) * 6 + 4
    fill_rect(bx - bw // 2, by - 5, bw, 11, INK)
    draw_text(bx - (len(label) * 6 - 1) // 2, by - 3, label, 1, (255, 255, 255))


# ---------------------------------------------------------------- illustrations
# Every illustration draws inside (x, y, w, h) with a pale tint background.

def ill_market(x, y, w, h):
    fill_rect(x, y, w, h, (246, 226, 224))
    # falling line chart
    pts = [(x + 8, y + 14), (x + 22, y + 22), (x + 34, y + 18), (x + 48, y + 34),
           (x + 62, y + 30), (x + 76, y + 52), (x + 90, y + 48), (x + 104, y + 68)]
    for i in range(len(pts) - 1):
        line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], (178, 34, 34))
        line(pts[i][0], pts[i][1] + 1, pts[i + 1][0], pts[i + 1][1] + 1, (178, 34, 34))
    # bars, descending like the line
    for i, bh in enumerate([58, 44, 48, 34, 26, 18]):
        fill_rect(x + 10 + i * 16, y + h - 6 - bh, 10, bh, (200, 90, 80))
    draw_text(x + 8, y + 2, "-3.7%", 1, (178, 34, 34))
    triangle((x + w - 16, y + 4), (x + w - 8, y + 4), (x + w - 12, y + 12), (178, 34, 34))


def ill_hormuz(x, y, w, h):
    fill_rect(x, y, w, h, (222, 236, 242))
    # sea
    fill_rect(x, y + h - 22, w, 22, (70, 130, 170))
    for i in range(4):
        line(x + 4 + i * 28, y + h - 12, x + 16 + i * 28, y + h - 12, (255, 255, 255))
    # tanker hull + containers
    poly([(x + 12, y + h - 24), (x + 96, y + h - 24), (x + 88, y + h - 12),
          (x + 20, y + h - 12)], (60, 60, 60))
    fill_rect(x + 22, y + h - 44, 14, 18, (200, 60, 40))
    fill_rect(x + 38, y + h - 44, 14, 18, (40, 120, 80))
    fill_rect(x + 54, y + h - 44, 14, 18, (220, 160, 40))
    fill_rect(x + 70, y + h - 44, 14, 18, (60, 90, 160))
    # flame + smoke
    poly([(x + 76, y + 26), (x + 84, y + 8), (x + 92, y + 26)], (230, 120, 20))
    poly([(x + 80, y + 26), (x + 84, y + 14), (x + 88, y + 26)], (250, 200, 40))
    circle(x + 88, y + 12, 5, (120, 120, 120))
    circle(x + 96, y + 8, 4, (150, 150, 150))


def ill_cop(x, y, w, h):
    fill_rect(x, y, w, h, (226, 240, 226))
    # globe with a crack
    circle(x + w // 2, y + h // 2 + 4, 40, (70, 130, 180))
    ellipse(x + w // 2 - 16, y + h // 2 - 6, 14, 9, (60, 160, 90))
    ellipse(x + w // 2 + 14, y + h // 2 + 16, 12, 7, (60, 160, 90))
    line(x + w // 2 - 8, y + h // 2 - 36, x + w // 2 + 5, y + h // 2 - 14, (178, 34, 34))
    line(x + w // 2 + 5, y + h // 2 - 14, x + w // 2 - 5, y + h // 2 + 7, (178, 34, 34))
    line(x + w // 2 - 5, y + h // 2 + 7, x + w // 2 + 9, y + h // 2 + 32, (178, 34, 34))
    line(x + w // 2 - 7, y + h // 2 - 36, x + w // 2 + 6, y + h // 2 - 14, (178, 34, 34))
    line(x + w // 2 + 6, y + h // 2 - 14, x + w // 2 - 4, y + h // 2 + 7, (178, 34, 34))
    draw_text(x + 6, y + 2, "COP31", 1, (26, 26, 26))
    draw_text(x + w - 48, y + h - 12, "NO DEAL", 1, (178, 34, 34))


def ill_drone_block(x, y, w, h):
    fill_rect(x, y, w, h, (238, 236, 230))
    # apartment block
    fill_rect(x + 8, y + 24, 26, 36, (140, 130, 120))
    for r in range(3):
        for c in range(2):
            fill_rect(x + 12 + c * 11, y + 29 + r * 11, 6, 7, (250, 220, 90))
    # broken corner + smoke
    poly([(x + 8, y + 24), (x + 22, y + 24), (x + 18, y + 33), (x + 8, y + 31)], (90, 85, 80))
    circle(x + 20, y + 16, 4, (150, 150, 150))
    circle(x + 27, y + 12, 3, (170, 170, 170))
    # drone
    fill_rect(x + 42, y + 12, 14, 5, INK)
    line(x + 39, y + 10, x + 59, y + 10, INK)
    line(x + 39, y + 19, x + 59, y + 19, INK)
    circle(x + 49, y + 14, 2, (178, 34, 34))


def ill_ship(x, y, w, h):
    fill_rect(x, y, w, h, (222, 236, 242))
    fill_rect(x, y + h - 14, w, 14, (70, 130, 170))
    # listing corvette
    poly([(x + 6, y + 34), (x + 52, y + 26), (x + 50, y + 36), (x + 10, y + 44)], (90, 90, 90))
    fill_rect(x + 24, y + 20, 14, 8, (120, 120, 120))
    line(x + 30, y + 20, x + 30, y + 10, INK)
    circle(x + 30, y + 8, 2, (178, 34, 34))
    # drone boat + splash
    poly([(x + 40, y + h - 18), (x + 58, y + h - 18), (x + 56, y + h - 12),
          (x + 42, y + h - 12)], (40, 40, 40))
    for sx, sy in [(44, 46), (49, 43), (54, 46)]:
        line(x + sx, y + sy, x + sx + 2, y + sy - 5, (255, 255, 255))


def ill_missile(x, y, w, h):
    fill_rect(x, y, w, h, (238, 232, 226))
    # missile diagonal, inside the 62px box
    line(x + 8, y + 50, x + 46, y + 18, INK)
    line(x + 8, y + 53, x + 46, y + 21, INK)
    poly([(x + 46, y + 18), (x + 56, y + 24), (x + 46, y + 21)], (178, 34, 34))
    triangle((x + 8, y + 50), (x + 18, y + 45), (x + 14, y + 56), (178, 34, 34))
    # flame
    poly([(x + 6, y + 52), (x + 2, y + 60), (x + 10, y + 58)], (230, 120, 20))
    # dotted trajectory
    for i in range(4):
        circle(x + 12 + i * 11, y + 36 - i * 7, 2, (120, 120, 120))


def ill_capitol(x, y, w, h):
    fill_rect(x, y, w, h, (232, 236, 242))
    # dome
    ellipse(x + w // 2, y + 26, 20, 12, (90, 110, 150))
    fill_rect(x + w // 2 - 20, y + 26, 40, 5, (90, 110, 150))
    fill_rect(x + w // 2 - 2, y + 10, 4, 6, (90, 110, 150))
    circle(x + w // 2, y + 9, 2, (160, 120, 0))
    # columns + base
    for i in range(4):
        fill_rect(x + 12 + i * 11, y + 33, 5, 20, (200, 200, 205))
    fill_rect(x + 9, y + 53, 44, 5, (90, 110, 150))


def ill_cuffs(x, y, w, h):
    fill_rect(x, y, w, h, (240, 232, 222))
    # two cuffs, inside the 62px box
    circle(x + 19, y + 32, 11, INK, fill=False)
    circle(x + 19, y + 32, 7, (200, 200, 200))
    circle(x + 43, y + 32, 11, INK, fill=False)
    circle(x + 43, y + 32, 7, (200, 200, 200))
    line(x + 28, y + 26, x + 34, y + 26, INK)
    line(x + 28, y + 38, x + 34, y + 38, INK)
    # small star above
    for dx, dy in [(0, -3), (0, 3), (-3, 0), (3, 0)]:
        set_px(x + 31 + dx, y + 12 + dy, (178, 34, 34))
    set_px(x + 31, y + 12, (178, 34, 34))


def ill_tennis(x, y, w, h):
    fill_rect(x, y, w, h, (226, 240, 226))
    # racket, inside the 62px box
    ellipse(x + 26, y + 24, 14, 18, (120, 80, 40))
    ellipse(x + 26, y + 24, 11, 15, (250, 247, 240))
    for i in range(3):
        hline(x + 17, y + 15 + i * 8, 18, (120, 80, 40))
        vline(x + 20 + i * 7, y + 9, 30, (120, 80, 40))
    line(x + 26, y + 42, x + 34, y + 58, (120, 80, 40))
    # ball
    circle(x + 48, y + 46, 7, (200, 220, 60))
    line(x + 43, y + 41, x + 46, y + 51, (255, 255, 255))


def ill_golf(x, y, w, h):
    fill_rect(x, y, w, h, (226, 240, 226))
    # green
    ellipse(x + w // 2, y + h - 12, 26, 9, (70, 170, 90))
    # flag + hole
    line(x + 28, y + 10, x + 28, y + 46, INK)
    poly([(x + 28, y + 10), (x + 48, y + 15), (x + 28, y + 22)], (178, 34, 34))
    ellipse(x + 24, y + 48, 5, 2, INK)
    circle(x + 42, y + 48, 3, (255, 255, 255))


def ill_moto(x, y, w, h):
    fill_rect(x, y, w, h, (238, 232, 226))
    # wheels
    circle(x + 18, y + 46, 10, INK, fill=False)
    circle(x + 44, y + 46, 10, INK, fill=False)
    circle(x + 18, y + 46, 3, (120, 120, 120))
    circle(x + 44, y + 46, 3, (120, 120, 120))
    # body
    poly([(x + 18, y + 46), (x + 30, y + 28), (x + 40, y + 30), (x + 44, y + 46)],
         (178, 34, 34))
    line(x + 30, y + 28, x + 26, y + 22, INK)
    # checkered flag, small, top right inside the box
    for r in range(3):
        for c in range(3):
            if (r + c) % 2 == 0:
                fill_rect(x + 48 + c * 4, y + 6 + r * 4, 4, 4, INK)
    line(x + 48, y + 6, x + 48, y + 26, INK)


def ill_mercury(x, y, w, h):
    fill_rect(x, y, w, h, (232, 228, 240))
    # dotted orbit ellipse around the planet
    import math
    for t in range(0, 360, 12):
        a = math.radians(t)
        ox = int(x + 26 + 24 * math.cos(a))
        oy = int(y + 36 + 9 * math.sin(a))
        set_px(ox, oy, (120, 120, 120))
    # Mercury with craters
    circle(x + 26, y + 36, 15, (170, 150, 130))
    circle(x + 20, y + 30, 3, (140, 120, 100))
    circle(x + 32, y + 41, 4, (140, 120, 100))
    circle(x + 30, y + 28, 2, (140, 120, 100))
    # spacecraft on the orbit, top right
    fill_rect(x + 46, y + 20, 10, 6, (90, 110, 150))
    fill_rect(x + 40, y + 22, 6, 3, (40, 90, 160))
    fill_rect(x + 56, y + 22, 6, 3, (40, 90, 160))


def ill_taiwan(x, y, w, h):
    fill_rect(x, y, w, h, (240, 232, 220))
    # candlesticks falling, inside the 62px box
    for i, (top, bot) in enumerate([(14, 30), (18, 34), (22, 38), (26, 42), (30, 46)]):
        bx = x + 8 + i * 10
        fill_rect(bx, y + top, 6, bot - top, (178, 34, 34))
        line(bx + 3, y + top - 3, bx + 3, y + bot + 3, (178, 34, 34))

# ---------------------------------------------------------------- stories
# Every story: (region, headline, dek, map lon/lat or None).
# All 50 happened or were first reported on Monday 23 November 2026,
# verified against reporting dated that day (Reuters, AP, BBC, AFP,
# Al Jazeera, CNBC-TV18, Rivkin, Dawn/IQAir, national wires).

HEROES = [
    ("MARKETS", "AI ROUT: WALL ST IN CORRECTION",
     "S&P 500 -3.7% to 6,910, Nasdaq 100 -5.6%, worst week since Mar 2020. "
     "Nvidia -14% as the SEC probes its accounting. Seventh straight losing session.",
     "ILL_MARKET", (-74, 41)),
    ("MIDEAST", "TANKERS HIT IN THE STRAIT OF HORMUZ",
     "At least 3 tankers struck Fri-Sat, 2 more hit mines on Sunday. Iran says "
     "ships entered a restricted zone. Shipping attacks at their highest since the war began.",
     "ILL_HORMUZ", (56, 26)),
    ("EUROPE", "COP31 COLLAPSES: NO CLIMATE DEAL",
     "Record overtime ends in failure over the fossil-fuel deadlock. Australia's PM "
     "calls it a sign of difficult geopolitical times. About 200 nations leave empty-handed.",
     "ILL_COP", (30, 37)),
]

CARDS = [
    ("EUROPE", "DRONE HITS FLAT BLOCK NEAR KYIV",
     "2 killed, 11 missing, incl. 2 children, in Dymer. Rescuers still dig through rubble.",
     "ILL_DRONE", (31, 51)),
    ("AFRICA", "SEA DRONES HIT RUSSIAN SHIP IN LIBYA",
     "Corvette Merkury severely damaged at Benghazi base, later capsizes. 10 hurt.",
     "ILL_SHIP", (20, 32)),
    ("EUROPE", "POLAND: 3 OBJECTS WERE RUSSIAN MISSILES",
     "Debris that fell on Friday confirmed as cruise missiles. NATO to meet.",
     "ILL_MISSILE", (22, 50)),
    ("AMERICAS", "DEMOCRATS WIN 258 HOUSE SEATS",
     "Largest House majority since 1992 after flipping a North Carolina seat.",
     "ILL_CAPITOL", (-77, 39)),
    ("AMERICAS", "SINALOA KINGPIN CAPTURED",
     "FBI most-wanted 'El Chapo Isidro' seized; 11 killed in firefights.",
     "ILL_CUFFS", (-107, 25)),
    ("EUROPE", "ALCARAZ WINS FIRST ATP FINALS",
     "Beats world No.1 Zverev 6-2, 7-6 in Turin. 14th straight win after wrist injury.",
     "ILL_TENNIS", (7, 45)),
    ("AMERICAS", "THITIKUL'S THIRD STRAIGHT LPGA CROWN",
     "Final-round 65 wins the CME Group Tour Championship by 2 shots in Florida.",
     "ILL_GOLF", (-81, 28)),
    ("EUROPE", "MARQUEZ SEALS 8TH MOTOGP TITLE",
     "Eighth premier-class crown at the Portuguese GP, won by Bezzecchi.",
     "ILL_MOTO", (-8, 37)),
    ("SPACE", "BEPICOLOMBO ENTERS MERCURY ORBIT",
     "After an 8-year journey, only the 2nd mission ever to orbit Mercury.",
     "ILL_MERCURY", (9, 50)),
    ("ASIA", "TAIWAN BANS SHORT SELLING",
     "FSC acts from today after shares fell 17.5% in a week to 36,033.",
     "ILL_TAIWAN", (121, 25)),
]

# (region, one-line brief) — 37 briefs, numbered 14-50.
BRIEFS = [
    ("EUROPE", "FINLAND: RUSSIA STARTS TOWING DRONE-HIT BALTIC SHIP"),
    ("EUROPE", "RUSSIAN CARGO SHIP STILL BURNING OFF FINLAND"),
    ("AMERICAS", "HEGSETH CURBS US-CANADA DEFENCE TIES IN SECRET MEMO"),
    ("MIDEAST", "IRAN TO RATION ELECTRICITY AS GRID REELS FROM STRIKES"),
    ("MIDEAST", "IRAN FM: CASE TO CHANGE NUCLEAR DOCTRINE HAS STRONG LOGIC"),
    ("AMERICAS", "US HAWKS URGE TRUMP TO STRIKE IRAN AGAIN; HE SAYS NO RUSH"),
    ("EUROPE", "UKRAINE PEACE: US ENVOYS SEE PROGRESS, NATO-STYLE GUARANTEES"),
    ("EUROPE", "EU PUSHES EUR45BN LOAN FOR UKRAINE AMID BUDGET FIGHT"),
    ("WORLD", "128 STATES AGREE TO PURSUE RULES ON KILLER ROBOTS BY 2028"),
    ("ASIA", "SOUTH KOREA EDUCATION MINISTER QUITS OVER AI EXAM CHEATING"),
    ("AMERICAS", "SKUBAL AGREES 9-YEAR, $450M DEAL WITH THE METS"),
    ("EUROPE", "FIFA TO CONFIRM UK AS HOST OF 2035 WOMEN'S WORLD CUP"),
    ("EUROPE", "LIVERPOOL THRASH 10-MAN MAN UTD 4-0; UTD 19TH"),
    ("EUROPE", "GERWYN PRICE WINS GRAND SLAM OF DARTS 16-11"),
    ("AMERICAS", "BOCA JUNIORS WIN COPA SUDAMERICANA 2-0"),
    ("AFRICA", "SUDAN DRONE STRIKES HIT KHARTOUM, DAMAGE UN FACILITY"),
    ("MIDEAST", "SETTLERS TORCH 12 PALESTINIAN VEHICLES NEAR RAMALLAH"),
    ("AFRICA", "24 CIVILIANS KILLED IN FRESH SOUTH SUDAN VIOLENCE"),
    ("AFRICA", "35 FULANIS KILLED IN REVENGE ATTACKS IN NIGERIA"),
    ("AFRICA", "WHO CHIEF PLEADS FOR PEACE IN EBOLA-HIT DR CONGO"),
    ("ASIA", "INDONESIA FACTORY FIRE: 7 BODIES FOUND, 50 MISSING"),
    ("ASIA", "LAHORE WORLD'S MOST POLLUTED CITY AGAIN, AQI 538"),
    ("ASIA", "SHURI CASTLE REOPENS 7 YEARS AFTER FIRE DESTROYED IT"),
    ("ASIA", "MYANMAR JUNTA-BACKED GOVT CALLS ASEAN MOVE UNFAIR"),
    ("EUROPE", "THOUSANDS MARCH IN LISBON AS LIVING COSTS FUEL ANGER"),
    ("AMERICAS", "3 KILLED, 1 WOUNDED IN SHOOTING AT OHIO BABY SHOWER"),
    ("AMERICAS", "FBI CRIME DATABASE HACKED; USDA PAYMENTS SYSTEM BREACHED"),
    ("AMERICAS", "DELTA GROUNDS THOUSANDS OF FLIGHTS AFTER SYSTEM FAILURE"),
    ("AMERICAS", "US ARMY TO DETONATE MUNITIONS IN IOWA, DEFYING COURT"),
    ("AMERICAS", "BOLSONARO STABLE IN INTENSIVE CARE, DOCTORS SAY"),
    ("MIDEAST", "NETANYAHU, EISENKOT END TALKS WITH NO GOVT DEAL"),
    ("MIDEAST", "SAUDI COALITION INTERCEPTS HOUTHI MISSILE; 2 HURT IN BAHRAIN"),
    ("ASIA", "NORTH KOREA'S KIM: COUNTRY SEEKS SECURITY, NOT SUPREMACY"),
    ("ASIA", "CHINA AGREES TO SET UP AI TALKS MECHANISM"),
    ("EUROPE", "UK GOVT TO MAKE CASE FOR GREATER CONTROL OF UTILITIES"),
    ("EUROPE", "COMPASS GROUP PLANS TO MOVE LISTING LONDON TO NEW YORK"),
    ("OCEANIA", "ALBANESE BLAMES COP31 FAILURE ON DIFFICULT TIMES"),
]

ILL = {
    "ILL_MARKET": ill_market, "ILL_HORMUZ": ill_hormuz, "ILL_COP": ill_cop,
    "ILL_DRONE": ill_drone_block, "ILL_SHIP": ill_ship, "ILL_MISSILE": ill_missile,
    "ILL_CAPITOL": ill_capitol, "ILL_CUFFS": ill_cuffs, "ILL_TENNIS": ill_tennis,
    "ILL_GOLF": ill_golf, "ILL_MOTO": ill_moto, "ILL_MERCURY": ill_mercury,
    "ILL_TAIWAN": ill_taiwan,
}

STATS = [
    ("-3.7%", "S&P 500, INTO CORRECTION"),
    ("-5.6%", "NASDAQ 100, WORST WEEK SINCE 2020"),
    ("258", "DEMOCRAT HOUSE SEATS, MOST SINCE 1992"),
    ("128", "STATES BACK KILLER-ROBOT RULES"),
    ("538", "LAHORE AQI, WORLD'S WORST"),
    ("50", "STORIES FROM 6 REGIONS + SPACE"),
]

SOURCES = ("SOURCES: REUTERS - AP - BBC - AFP - AL JAZEERA - CNBC-TV18 - RIVKIN - "
           "DAWN/IQAIR - NATIONAL WIRES. ALL 50 STORIES HAPPENED OR WERE FIRST "
           "REPORTED ON MONDAY 23 NOVEMBER 2026.")

# ---------------------------------------------------------------- layout
def draw_masthead():
    fill_rect(10, 8, 1004, 3, INK)
    draw_text(10, 16, "THE WORLD IN ONE DAY", 3, INK)
    draw_text(10, 44, "MONDAY 23 NOVEMBER 2026  -  50 STORIES  -  6 REGIONS + SPACE",
              1, MUTED)
    # date box, right
    fill_rect(806, 14, 208, 40, INK)
    draw_text_centered(806, 20, 208, "23 NOV 2026", 2, (255, 255, 255))
    draw_text_centered(806, 38, 208, "MONDAY", 1, (200, 200, 200))
    hline(10, 60, 1004, RULE)


def draw_region_strip():
    counts = {}
    for region, _, _, _, _ in HEROES:
        counts[region] = counts.get(region, 0) + 1
    for region, _, _, _, _ in CARDS:
        counts[region] = counts.get(region, 0) + 1
    for region, _ in BRIEFS:
        counts[region] = counts.get(region, 0) + 1
    order = ["EUROPE", "AMERICAS", "ASIA", "MIDEAST", "AFRICA", "OCEANIA",
             "SPACE", "MARKETS", "WORLD"]
    x = 10
    for region in order:
        n = counts.get(region, 0)
        if n == 0:
            continue
        label = "%s %d" % (region, n)
        w = text_w(label, 1) + 16
        fill_rect(x, 66, w, 18, REGION[region])
        draw_text(x + 8, 71, label, 1, (255, 255, 255))
        x += w + 6
    draw_text(x + 4, 71, "TOTAL 50", 1, INK)


def draw_hero(i, region, headline, dek, ill_key, pin):
    x = 10 + i * 336
    y = 90
    w, h = 328, 206
    fill_rect(x, y, w, h, CARD)
    fill_rect(x, y, w, 3, REGION[region])
    # illustration
    ILL[ill_key](x + 8, y + 8, w - 16, 96)
    draw_text(x + 10, y + 110, "%d  %s" % (i + 1, region), 1, REGION[region])
    text_block(x + 10, y + 126, headline, 26, scale=2, leading=18)
    text_block(x + 10, y + 164, dek, 52, scale=1, color=MUTED, leading=10)


def draw_map_panel():
    draw_text(14, 292, "WHERE IT HAPPENED", 1, INK)
    draw_map()
    pins = []
    for i, (region, _, _, _, ll) in enumerate(HEROES):
        pins.append((i + 1, ll, REGION[region]))
    for j, (region, _, _, _, ll) in enumerate(CARDS):
        pins.append((j + 4, ll, REGION[region]))
    offsets = {1: (-16, -14), 2: (16, 2), 3: (20, 10), 4: (-38, -24), 5: (16, 16),
               6: (-46, 10), 7: (-18, 12), 8: (-22, 0), 9: (-30, 18), 10: (0, 16),
               11: (-22, 12), 12: (8, -24), 13: (14, -10)}
    for num, (lon, lat), color in pins:
        dx, dy = offsets.get(num, (0, -14))
        draw_pin(num, lon, lat, color, dx, dy)
    # day in numbers panel
    px0, py0 = 668, 292
    draw_text(px0, 292, "THE DAY IN NUMBERS", 1, INK)
    fill_rect(px0, 306, 346, 158, CARD)
    for i, (big, small) in enumerate(STATS):
        cx = px0 + 8 + (i % 2) * 170
        cy = 314 + (i // 2) * 50
        draw_text(cx, cy, big, 2, REGION["MIDEAST"] if i < 2 else INK)
        text_block(cx, cy + 16, small, 24, scale=1, color=MUTED, leading=9)


def draw_small_card(j, region, headline, dek, ill_key):
    col, row = j % 5, j // 5
    x = 10 + col * 203
    y = 474 + row * 96
    w, h = 197, 90
    fill_rect(x, y, w, h, CARD)
    fill_rect(x, y, 3, h, REGION[region])
    ILL[ill_key](x + 7, y + 6, 62, 62)
    draw_text(x + 75, y + 6, "%d %s" % (j + 4, region), 1, REGION[region])
    text_block(x + 75, y + 18, headline, 19, scale=1, leading=9)
    text_block(x + 75, y + 46, dek, 19, scale=1, color=MUTED, leading=9)


def draw_briefs():
    draw_text(10, 672, "THE REST OF THE DAY  -  37 MORE STORIES", 1, INK)
    hline(10, 686, 1004, RULE)
    col_w = 497
    for i, (region, line_) in enumerate(BRIEFS):
        col = i // 19
        row = i % 19
        x = 10 + col * 507
        y = 692 + row * 15
        num = i + 14
        draw_text(x, y, "%02d" % num, 1, REGION[region])
        draw_text(x + 20, y, line_, 1, INK)
    hline(10, 980, 1004, RULE)


def draw_footer():
    text_block(10, 988, SOURCES, 165, scale=1, color=MUTED, leading=10)


def main():
    draw_masthead()
    draw_region_strip()
    for i, (region, headline, dek, ill_key, ll) in enumerate(HEROES):
        draw_hero(i, region, headline, dek, ill_key, ll)
    draw_map_panel()
    for j, (region, headline, dek, ill_key, ll) in enumerate(CARDS):
        draw_small_card(j, region, headline, dek, ill_key)
    draw_briefs()
    draw_footer()
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "out")
    os.makedirs(out_dir, exist_ok=True)
    data = encode_png()
    with open(os.path.join(out_dir, "entry.png"), "wb") as f:
        f.write(data)


if __name__ == "__main__":
    main()
