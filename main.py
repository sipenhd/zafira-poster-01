#!/usr/bin/env python3
"""ZAFIRA — a travel poster for a place that does not exist.

A desert at sunset with a sky train: vast dunes, a huge low orange sun,
a long elevated rail crossing the sky on slender stilts, a little train
of lit cars, warm orange-pink-purple sky, a tiny station and travellers,
retro travel-poster style with a bold title band.

Pure Python 3 stdlib only: no network, no input files, no fonts.
Paints 1024x1024 pixel-by-pixel (row fills + a small 5x7 bitmap font)
and writes its own PNG via zlib/struct. Deterministic (seeded RNG).

Writes $MAKEFUN_OUTPUT_DIR/entry.png (default: ./output/entry.png).
"""
import math
import os
import random
import struct
import zlib

W, H = 1024, 1024
OUT = os.environ.get("MAKEFUN_OUTPUT_DIR", "output")
PATH = os.path.join(OUT, "entry.png")

# --- palette ---
CREAM = (250, 238, 210)
INK = (28, 16, 48)          # deep plum, title band
SUN = (255, 214, 122)
SUN_CORE = (255, 232, 170)
RAIL = (46, 26, 60)
CAR = (58, 32, 74)
CAR_TOP = (90, 48, 96)
WINDOW = (255, 205, 110)
DUNE_FAR = (214, 130, 74)
DUNE_MID = (186, 102, 52)
DUNE_NEAR = (146, 72, 36)
DUNE_FRONT = (110, 52, 28)
STATION = (70, 34, 52)

rng = random.Random(20261121)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def sky_color(y):
    """Vertical gradient: plum -> magenta -> orange -> gold at horizon."""
    stops = [
        (0.00, (38, 22, 74)),
        (0.30, (96, 42, 96)),
        (0.52, (198, 84, 106)),
        (0.68, (248, 138, 80)),
        (0.80, (255, 178, 92)),
        (1.00, (255, 206, 120)),
    ]
    t = y / 640.0
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t0 <= t <= t1:
            return lerp(c0, c1, (t - t0) / (t1 - t0))
    return stops[-1][1]


# framebuffer: list of bytearray rows
fb = [bytearray(W * 3) for _ in range(H)]


def fill_row(y, x0, x1, color):
    if y < 0 or y >= H:
        return
    x0 = max(0, x0)
    x1 = min(W, x1)
    if x0 >= x1:
        return
    row = fb[y]
    row[x0 * 3:x1 * 3] = bytes(color) * (x1 - x0)


def fill_rect(x0, y0, x1, y1, color):
    for y in range(max(0, y0), min(H, y1)):
        fill_row(y, x0, x1, color)


def set_px(x, y, color):
    if 0 <= x < W and 0 <= y < H:
        fb[y][x * 3:x * 3 + 3] = bytes(color)


def disc(cx, cy, r, color):
    for y in range(max(0, cy - r), min(H, cy + r + 1)):
        dy = y - cy
        dx = int(math.sqrt(max(0, r * r - dy * dy)))
        fill_row(y, cx - dx, cx + dx + 1, color)


def ellipse(cx, cy, rx, ry, color):
    for y in range(max(0, cy - ry), min(H, cy + ry + 1)):
        dy = (y - cy) / ry
        dx = int(rx * math.sqrt(max(0.0, 1.0 - dy * dy)))
        fill_row(y, cx - dx, cx + dx + 1, color)


# --- sky ---
for y in range(0, 660):
    fill_row(y, 0, W, sky_color(y))

# --- stars (upper sky only, faint) ---
for _ in range(90):
    x = rng.randrange(0, W)
    y = rng.randrange(0, 260)
    b = rng.choice([200, 220, 240])
    set_px(x, y, (b, b, min(255, b + 10)))
    if rng.random() < 0.4:
        set_px(x + 1, y, (b, b, min(255, b + 10)))

# --- sun glow + sun ---
disc(700, 560, 210, (255, 170, 100))
disc(700, 560, 175, (255, 196, 120))
disc(700, 560, 145, SUN)
disc(700, 560, 110, SUN_CORE)

# --- clouds (soft clustered puffs, warm) ---
for cx, cy, rx, ry in [
    (180, 180, 150, 26), (330, 150, 110, 20), (880, 230, 170, 28),
    (120, 330, 120, 20), (900, 360, 130, 22), (520, 120, 130, 18),
]:
    for ox, oy, orx, ory in [
        (-rx // 2, 4, rx // 2, ry),
        (0, -6, rx * 2 // 3, ry + 6),
        (rx // 2, 4, rx // 2, ry),
    ]:
        ellipse(cx + ox, cy + oy, orx, ory, (255, 178, 150))
        ellipse(cx + ox, cy + oy + 6, orx - 12, max(4, ory - 8), (248, 150, 128))

# --- birds ---
def bird(x, y, s, color):
    for i in range(s):
        set_px(x - i, y + i // 2, color)
        set_px(x + i, y + i // 2, color)

for bx, by, bs in [(220, 260, 9), (260, 285, 7), (820, 200, 8), (860, 230, 6), (480, 300, 7)]:
    bird(bx, by, bs, (60, 30, 70))

# --- dunes (back to front, sine-wave ridges) ---
def dune_top(x, base, amp, freq, phase):
    return int(base + amp * math.sin(x * freq + phase)
               + 14 * math.sin(x * freq * 2.7 + phase * 2))

layers = [
    (560, 26, 0.006, 1.2, DUNE_FAR, 660),
    (610, 34, 0.005, 3.1, DUNE_MID, 760),
    (680, 42, 0.004, 5.0, DUNE_NEAR, 860),
    (770, 48, 0.0035, 2.0, DUNE_FRONT, H),
]
for base, amp, freq, phase, color, bottom in layers:
    for x in range(W):
        top = dune_top(x, base, amp, freq, phase)
        for y in range(max(0, top), bottom):
            set_px(x, y, color)

# dune crest highlights (thin light line along each ridge)
for base, amp, freq, phase, color, _ in layers:
    for x in range(0, W, 2):
        top = dune_top(x, base, amp, freq, phase)
        set_px(x, top, lerp(color, (255, 220, 160), 0.45))
        set_px(x, top + 1, lerp(color, (255, 220, 160), 0.25))

# --- sky rail: slender stilts + track ---
RAIL_Y = 430
fill_rect(0, RAIL_Y, W, RAIL_Y + 7, RAIL)
fill_rect(0, RAIL_Y + 12, W, RAIL_Y + 15, RAIL)
for sx in range(60, W, 130):
    top = dune_top(sx, 560, 26, 0.006, 1.2)
    fill_rect(sx, RAIL_Y + 15, sx + 6, top, RAIL)
    fill_rect(sx - 8, top - 6, sx + 14, top, RAIL)

# --- the sky train: 5 cars on the rail ---
train_x0 = 210
car_w, car_h, gap = 108, 42, 10
for i in range(5):
    x0 = train_x0 + i * (car_w + gap)
    y0 = RAIL_Y - car_h
    fill_rect(x0, y0, x0 + car_w, y0 + car_h, CAR)
    fill_rect(x0, y0, x0 + car_w, y0 + 8, CAR_TOP)
    # lit windows
    for wx in range(x0 + 12, x0 + car_w - 12, 26):
        fill_rect(wx, y0 + 14, wx + 16, y0 + 30, WINDOW)
    # wheels / bogies
    fill_rect(x0 + 14, RAIL_Y - 2, x0 + 30, RAIL_Y + 2, INK)
    fill_rect(x0 + car_w - 30, RAIL_Y - 2, x0 + car_w - 14, RAIL_Y + 2, INK)
# engine car: chimney + headlamp glow
fill_rect(train_x0 - 26, RAIL_Y - 30, train_x0 - 14, RAIL_Y - 6, CAR)
disc(train_x0 - 32, RAIL_Y - 12, 7, WINDOW)

# --- tiny station on the near dune + travellers ---
st_x, st_y = 820, dune_top(820, 680, 42, 0.004, 5.0)
fill_rect(st_x, st_y - 46, st_x + 90, st_y, STATION)
fill_rect(st_x - 8, st_y - 56, st_x + 98, st_y - 46, (200, 90, 70))
fill_rect(st_x + 30, st_y - 34, st_x + 60, st_y, WINDOW)
for tx in (760, 745, 905, 920):
    ty = dune_top(tx, 680, 42, 0.004, 5.0)
    fill_rect(tx, ty - 14, tx + 4, ty, INK)
    disc(tx + 2, ty - 18, 4, INK)

# --- title band ---
fill_rect(0, 868, W, H, INK)
fill_rect(0, 868, W, 874, CREAM)
fill_rect(0, 872, W, 874, (200, 90, 70))

# --- 5x7 bitmap font ---
FONT = {
    'A': ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    'C': ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    'D': ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    'E': ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    'F': ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    'H': ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    'I': ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    'K': ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    'N': ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    'O': ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    'R': ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    'S': ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    'T': ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    'U': ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    'Y': ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    'Z': ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    ' ': ["00000"] * 7,
    '.': ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
}


def draw_text(text, cx, y, scale, color):
    total = len(text) * 6 * scale - scale
    x = cx - total // 2
    for ch in text:
        glyph = FONT.get(ch, FONT[' '])
        for gy, row in enumerate(glyph):
            for gx, bit in enumerate(row):
                if bit == '1':
                    fill_rect(x + gx * scale, y + gy * scale,
                              x + (gx + 1) * scale, y + (gy + 1) * scale, color)
        x += 6 * scale


draw_text("ZAFIRA", W // 2, 898, 11, CREAM)
draw_text("THE SKY TRAIN CROSSES THE DUNES", W // 2, 988, 3, (255, 178, 120))

# --- cream frame ---
fill_rect(0, 0, W, 14, CREAM)
fill_rect(0, H - 14, W, H, CREAM)
fill_rect(0, 0, 14, H, CREAM)
fill_rect(W - 14, 0, W, H, CREAM)


def write_png(path):
    raw = b"".join(b"\x00" + bytes(row) for row in fb)
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)


if __name__ == "__main__":
    write_png(PATH)
    print(PATH, os.path.getsize(PATH), "bytes")
