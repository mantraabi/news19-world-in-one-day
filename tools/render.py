#!/usr/bin/env python3
"""Authoring-time renderer for the world-news front page of 19 November 2026."""
from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
S = 2
W = 1024
PAPER = (250, 247, 240)
INK = (21, 24, 28)
MUTED = (76, 83, 91)
CRIMSON = (168, 31, 31)
RULE = (198, 192, 177)
TAG = (44, 58, 69)
WHITE = (255, 255, 255)

FACE_FILES = {
    "serif": "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    "sans": "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "sansb": "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
}

image = Image.new("RGB", (W * S, W * S), PAPER)
draw = ImageDraw.Draw(image)
_fonts: dict[tuple[int, str], ImageFont.FreeTypeFont] = {}
_boxes: list[dict] = []


def font(size: float, face: str) -> ImageFont.FreeTypeFont:
    key = (max(1, int(round(size * S))), face)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(FACE_FILES[face], key[0])
    return _fonts[key]


def X(value: float) -> int:
    return int(round(value * S))


def Y(value: float) -> int:
    return int(round(value * S))


def px_box(rect) -> list[int]:
    return [X(rect[0]), Y(rect[1]), X(rect[2]), Y(rect[3])]


def rule_line(rect, color=RULE, width=1.0) -> None:
    draw.rectangle(px_box(rect), fill=color)


def stroke(rect, color=INK, width=1.0) -> None:
    draw.rectangle(px_box(rect), outline=color, width=max(1, int(round(width * S))))


def line(points, color=INK, width=2.2) -> None:
    draw.line([(X(x), Y(y)) for x, y in points], fill=color, width=max(1, int(round(width * S))), joint="curve")


def poly(points, fill=None, outline=None, width=2.0) -> None:
    draw.polygon(
        [(X(x), Y(y)) for x, y in points],
        fill=fill,
        outline=outline,
        width=max(1, int(round(width * S))) if outline else 0,
    )


def disc(rect, fill=None, outline=None, width=2.0) -> None:
    draw.ellipse(
        px_box(rect),
        fill=fill,
        outline=outline,
        width=max(1, int(round(width * S))) if outline else 0,
    )


def arc(rect, start, end, color=INK, width=1.6) -> None:
    draw.arc(px_box(rect), start, end, fill=color, width=max(1, int(round(width * S))))


def measured(text: str, size: float, face: str, tracking: float = 0.0) -> float:
    f = font(size, face)
    if not tracking:
        return draw.textlength(text, font=f) / S
    return sum(draw.textlength(ch, font=f) for ch in text) / S + tracking * max(0, len(text) - 1)


def record(name, text, rect, size, face, cell, cell_rect, extra=None) -> None:
    entry = {
        "name": name,
        "text": text,
        "rect": [round(v, 2) for v in rect],
        "font_size": size,
        "face": face,
        "cell": cell,
        "cell_rect": [round(v, 2) for v in cell_rect],
    }
    if extra:
        entry.update(extra)
    _boxes.append(entry)


def put(x, y, text, size, face="sans", color=INK, tracking=0.0, align="left", cell="", cell_rect=None, name="") -> None:
    if cell_rect is None:
        cell_rect = (0, 0, W, W)
    width = measured(text, size, face, tracking)
    left = x - width if align == "right" else x
    f = font(size, face)
    if tracking:
        cursor = left
        for ch in text:
            draw.text((X(cursor), Y(y)), ch, font=f, fill=color, anchor="lt")
            cursor += draw.textlength(ch, font=f) / S + tracking
    else:
        draw.text((X(left), Y(y)), text, font=f, fill=color, anchor="lt")
    ascent, descent = f.getmetrics()
    height = (ascent + descent) / S
    record(name or text[:24], text, (left, y, left + width, y + height), size, face, cell, cell_rect)


def put_baseline(x, baseline, text, size, face="sans", color=INK, tracking=0.0, align="left", cell="", cell_rect=None, name="") -> None:
    f = font(size, face)
    ascent, _descent = f.getmetrics()
    put(x, baseline - ascent / S, text, size, face, color, tracking, align, cell, cell_rect, name)


def wrap_text(text: str, f: ImageFont.FreeTypeFont, width: float) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        trial = (current + " " + word).strip()
        if not current or draw.textlength(trial, font=f) / S <= width:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def fit(text: str, size: int, face: str, width: float, max_lines: int, floor: int):
    size_used = size
    while size_used > floor:
        f = font(size_used, face)
        lines = wrap_text(text, f, width)
        if len(lines) <= max_lines:
            return size_used, lines, False
        size_used -= 1
    f = font(floor, face)
    lines = wrap_text(text, f, width)
    truncated = len(lines) > max_lines
    lines = lines[:max_lines]
    if truncated and lines:
        last = lines[-1]
        while last and draw.textlength(last + "\u2026", font=f) / S > width:
            last = last[:-1].rstrip()
        lines[-1] = last + "\u2026"
    return floor, lines, truncated


def block(x, y, text, size, face, width, max_lines, leading, floor, color=INK, cell="", cell_rect=None, name="") -> float:
    if cell_rect is None:
        cell_rect = (0, 0, W, W)
    size_used, lines, truncated = fit(text, size, face, width, max_lines, floor)
    f = font(size_used, face)
    ascent, descent = f.getmetrics()
    for index, ln in enumerate(lines):
        draw.text((X(x), Y(y + index * leading)), ln, font=f, fill=color, anchor="lt")
    used = max(measured(ln, size_used, face) for ln in lines)
    height = (len(lines) - 1) * leading + (ascent + descent) / S
    record(
        name or text[:24],
        text,
        (x, y, x + used, y + height),
        size_used,
        face,
        cell,
        cell_rect,
        {"lines": lines, "truncated": truncated, "requested_size": size},
    )
    return y + height


def pill(x, top, label, cell, cell_rect) -> None:
    width = measured(label, 8.5, "sansb", 0.6)
    draw.rounded_rectangle(px_box([x, top + 2, x + width + 8, top + 15]), radius=X(2.5), fill=TAG)
    put(x + 4, top + 4, label, 8.5, "sansb", WHITE, tracking=0.6, cell=cell, cell_rect=cell_rect, name="tag")


LEAD = {
    "kicker": "ASIA-PACIFIC \u00b7 APEC \u00b7 SHENZHEN",
    "head": "Trump meets Xi and Putin, then a first US\u2013Russia\u2013China session",
    "deck": (
        "Trump told Xi that 'as long as the two of us are in charge' there would be no problem. "
        "Xi called the trilateral of 'groundbreaking significance'. Everything here happened, "
        "or was first reported, on Thursday 19 November 2026."
    ),
    "source": "AL JAZEERA \u00b7 AP \u00b7 REUTERS",
}

RIGHT = [
    {
        "key": "icj",
        "kicker": "THE HAGUE \u00b7 ICJ",
        "head": "UN court finds Myanmar committed genocide against Rohingya",
        "deck": "The court's first genocide finding against a state; The Gambia filed in 2019.",
        "num": "9-6",
    },
    {
        "key": "ipo",
        "kicker": "MARKETS \u00b7 IPO",
        "head": "Anthropic raises $81.3bn in the largest IPO on record",
        "deck": "980m shares at $83 valued the Claude maker near $1.5tn; trading was set to begin today.",
        "num": "$81.3BN",
    },
]

BAND = [
    {
        "key": "bridge",
        "kicker": "EUROPE \u00b7 KERCH STRAIT",
        "head": "Crimean Bridge struck again; road span collapses",
        "deck": "Video showed explosions before part of the crossing fell, the Russian-installed governor said.",
    },
    {
        "key": "hormuz",
        "kicker": "MIDDLE EAST \u00b7 HORMUZ",
        "head": "Tankers ablaze near Hormuz as Houthi missiles are intercepted",
        "deck": "Iran's army said three burned east of the strait; the Saudi-led coalition intercepted missiles aimed at Riyadh.",
    },
    {
        "key": "gta",
        "kicker": "CULTURE \u00b7 GAMING",
        "head": "Grand Theft Auto VI launches after a 13-year wait",
        "deck": "Critics called it a masterpiece; events ran from Miami and Dublin to billboards in Tokyo and Sydney.",
    },
]

BRIEFS = [
    ("ASIA \u00b7 TRADE", "Philippines and Chile sign a free-trade agreement at APEC"),
    ("ASIA \u00b7 KOREA", "IAEA says North Korea is expanding its uranium enrichment site"),
    ("ASIA \u00b7 CHIPS", "TSMC and Samsung suspend some chip shipments to Chinese customers"),
    ("ASIA \u00b7 JAPAN", "Japan's new premier cuts a lonely figure as Putin returns"),
    ("EUROPE \u00b7 UKRAINE", "Russian strike on Odesa kills four and injures at least 13"),
    ("EUROPE \u00b7 ENERGY", "Ukraine says it hit two refineries; Zelensky hails its own weapons"),
    ("EUROPE \u00b7 ARCTIC", "Denmark's parliament approves a security deal with Greenland and the US"),
    ("EUROPE \u00b7 ROYALS", "Catherine visits a Mumbai maternity hospital on the last day"),
    ("MIDDLE EAST \u00b7 GAZA", "Israeli military completes a rare ground operation beyond the Yellow Line"),
    ("MIDDLE EAST \u00b7 IRAN", "Trump, in an interview, says Iran seeks chemical and biological arms"),
    ("AFRICA \u00b7 MIGRATION", "Dozens missing after a boat carrying about 100 migrants sinks off Senegal"),
    ("AFRICA \u00b7 HEALTH", "DR Congo's Ebola outbreak spreads as patients avoid hospitals"),
    ("AFRICA \u00b7 ECONOMY", "Egypt secures a $2.3bn IMF deal as its recovery gathers pace"),
    ("AMERICAS \u00b7 HEALTH", "Unvaccinated Pennsylvania resident dies as US measles cases surge"),
    ("AMERICAS \u00b7 POLITICS", "Musk calls his record $446m midterm spending 'pretty foolish'"),
    ("AMERICAS \u00b7 TECH", "Waymo pauses driverless taxis on US freeways after California incidents"),
]

TICKER = [
    "IEA says the Iran war could permanently cut reliance on Hormuz",
    "Van Gogh sells for a record $190.4m after a row over its Nazi history",
    "Ronaldo outlines a Portugal retirement plan and a farewell game",
    "Musk calls Jensen Huang irreplaceable as Nvidia shares slip",
    "Hegseth hails Maduro's capture, then flies to Colombia for drug talks",
    "Milei's plan to suspend Argentina's primaries clears a key hurdle",
    "Record numbers of African migrants reach Spain's Canary Islands",
    "Uganda landslide survivors seek justice at the UN",
    "Fela Kuti inducted into the Rock & Roll Hall of Fame",
    "Jeffries on track to be the first Black speaker of the House",
]

TOTAL = 1 + len(RIGHT) + len(BAND) + len(BRIEFS) + len(TICKER)


def rotate(cx, cy, dx, dy, angle):
    cosine, sine = math.cos(angle), math.sin(angle)
    return cx + dx * cosine - dy * sine, cy + dx * sine + dy * cosine


def art_lead(x0, y0, x1, y1) -> None:
    stroke((x0, y0, x1, y1), RULE, 1)
    disc((x0 + 128, y0 + 24, x0 + 176, y0 + 72), fill=None, outline=CRIMSON, width=2.2)
    disc((x0 + 142, y0 + 38, x0 + 162, y0 + 58), fill=CRIMSON, outline=None)
    for angle in (-70, -50, -30, -10, 10, 30, 50, 70):
        cx, cy = x0 + 152, y0 + 48
        line(
            [
                (cx + 32 * math.cos(math.radians(angle)), cy + 32 * math.sin(math.radians(angle))),
                (cx + 41 * math.cos(math.radians(angle)), cy + 41 * math.sin(math.radians(angle))),
            ],
            CRIMSON,
            1.8,
        )
    line([(x0 + 10, y0 + 78), (x0 + 40, y0 + 70), (x0 + 228, y0 + 70), (x0 + 250, y0 + 78)], INK, 2.6)
    line([(x0 + 16, y0 + 84), (x0 + 244, y0 + 84)], INK, 1.6)
    for pole in (44, 124, 204):
        line([(x0 + pole, y0 + 84), (x0 + pole, y0 + 132)], INK, 2.0)
    panels = [
        (x0 + 46, y0 + 92, x0 + 86, y0 + 130, "stripes"),
        (x0 + 126, y0 + 92, x0 + 166, y0 + 130, "bands"),
        (x0 + 206, y0 + 92, x0 + 246, y0 + 130, "stars"),
    ]
    for px0, py0, px1, py1, kind in panels:
        if kind == "stripes":
            stroke((px0, py0, px1, py1), INK, 1.8)
            for offset in (10, 19, 28):
                line([(px0 + 1, py0 + offset), (px1 - 1, py0 + offset)], CRIMSON, 1.8)
        elif kind == "bands":
            stroke((px0, py0, px1, py1), INK, 1.8)
            draw.rectangle(px_box([px0 + 1, py0 + 13, px1 - 1, py0 + 25]), fill=MUTED)
            draw.rectangle(px_box([px0 + 1, py0 + 25, px1 - 1, py1 - 1]), fill=CRIMSON)
        else:
            draw.rectangle(px_box([px0, py0, px1, py1]), fill=CRIMSON, outline=INK, width=X(1.8))
            for dx, dy in ((6, 6), (13, 9), (7, 14)):
                disc((px0 + dx, py0 + dy, px0 + dx + 4, py0 + dy + 4), fill=PAPER)
    for step in (0, 88, 176):
        px0 = x0 + 18 + step
        poly(
            [(px0, y0 + 204), (px0 + 52, y0 + 204), (px0 + 44, y0 + 148), (px0 + 8, y0 + 148)],
            fill=PAPER,
            outline=INK,
            width=2.2,
        )
        line([(px0 + 8, y0 + 152), (px0 + 44, y0 + 152)], MUTED, 1.4)
        line([(px0 + 26, y0 + 148), (px0 + 22, y0 + 136)], INK, 1.8)
        disc((px0 + 19, y0 + 130, px0 + 25, y0 + 136), fill=INK)
    line([(x0 + 12, y0 + 206), (x0 + 248, y0 + 206)], INK, 2.2)


def art_icj(x0, y0, x1, y1) -> None:
    stroke((x0, y0, x1, y1), RULE, 1)
    cx = (x0 + x1) / 2
    head_x, head_y, angle = cx + 6, y0 + 26, -0.38
    corners = [
        rotate(head_x, head_y, -17, -7, angle),
        rotate(head_x, head_y, 17, -7, angle),
        rotate(head_x, head_y, 17, 7, angle),
        rotate(head_x, head_y, -17, 7, angle),
    ]
    poly(corners, fill=PAPER, outline=INK, width=2.2)
    handle_start = rotate(head_x, head_y, -10, 0, angle)
    line([handle_start, (cx - 20, y0 + 56)], INK, 4.4)
    poly([(cx - 20, y0 + 58), (cx + 16, y0 + 58), (cx + 12, y0 + 66), (cx - 16, y0 + 66)], fill=PAPER, outline=INK, width=2.2)
    line([(cx - 22, y0 + 66), (cx + 18, y0 + 66)], INK, 2.2)
    arc((x0 + 8, y0 + 44, x1 - 8, y1 - 4), 205, 335, MUTED, 1.6)
    for step in range(7):
        theta = math.radians(210 + step * 20)
        lx = cx + 33 * math.cos(theta)
        ly = y0 + 66 + 16 * math.sin(theta)
        disc((lx - 2, ly - 1.4, lx + 2, ly + 1.4), fill=MUTED)


def art_markets(x0, y0, x1, y1) -> None:
    stroke((x0, y0, x1, y1), RULE, 1)
    base = y1 - 10
    heights = (14, 21, 28, 35, 42)
    for index, height in enumerate(heights):
        bx = x0 + 9 + index * 11
        draw.rectangle(px_box([bx, base - height, bx + 8, base]), fill=PAPER, outline=INK, width=X(1.8))
    line([(x0 + 11, base - 30), (x0 + 32, base - 42), (x0 + 50, base - 52), (x0 + 66, base - 60)], CRIMSON, 2.2)
    poly([(x0 + 66, base - 60), (x0 + 58, base - 60), (x0 + 66, base - 50)], fill=CRIMSON)
    line([(x0 + 72, y0 + 16), (x0 + 72, y0 + 46)], INK, 1.8)
    draw.rectangle(px_box([x0 + 68, y0 + 24, x0 + 76, y0 + 36]), fill=CRIMSON, outline=INK, width=X(1.6))
    line([(x0 + 8, base), (x1 - 6, base)], INK, 2.2)


def art_bridge(x0, y0, x1, y1) -> None:
    stroke((x0, y0, x1, y1), RULE, 1)
    for offset in (0, 5, 10):
        yy = y1 - 18 + offset
        for step in range(3):
            bx = x0 + 8 + step * 26
            arc((bx, yy - 3.2, bx + 14, yy + 3.2), 200, 340, MUTED, 1.4)
    line([(x0 + 6, y0 + 40), (x0 + 33, y0 + 40)], INK, 3.2)
    line([(x0 + 59, y0 + 40), (x1 - 6, y0 + 40)], INK, 3.2)
    line([(x0 + 33, y0 + 40), (x0 + 40, y0 + 47)], INK, 2.2)
    line([(x0 + 59, y0 + 40), (x0 + 52, y0 + 49)], INK, 2.2)
    for tower in (x0 + 20, x1 - 20):
        line([(tower, y0 + 24), (tower, y0 + 62)], INK, 2.6)
        line([(tower - 6, y0 + 46), (tower + 6, y0 + 46)], INK, 2.0)
    for start, end in ((x0 + 20, x0 + 8), (x0 + 20, x0 + 32), (x1 - 20, x1 - 8), (x1 - 20, x1 - 33)):
        line([(start, y0 + 24), (end, y0 + 39)], INK, 1.4)
    for dx, dy, size in ((40, 52, 5), (47, 60, 4), (36, 64, 3)):
        draw.rectangle(px_box([x0 + dx, y0 + dy, x0 + dx + size, y0 + dy + size]), fill=INK)
    for angle in (200, 240, 280, 320, 20):
        line(
            [
                (x0 + 46 + 9 * math.cos(math.radians(angle)), y0 + 26 + 9 * math.sin(math.radians(angle))),
                (x0 + 46 + 15 * math.cos(math.radians(angle)), y0 + 26 + 15 * math.sin(math.radians(angle))),
            ],
            CRIMSON,
            1.6,
        )


def art_gulf(x0, y0, x1, y1) -> None:
    stroke((x0, y0, x1, y1), RULE, 1)
    for offset in (0, 6):
        yy = y1 - 16 + offset
        for step in range(3):
            bx = x0 + 8 + step * 26
            arc((bx, yy - 3.4, bx + 15, yy + 3.4), 200, 340, MUTED, 1.6)
    poly([(x0 + 8, y0 + 56), (x0 + 72, y0 + 56), (x0 + 63, y0 + 70), (x0 + 17, y0 + 70)], fill=PAPER, outline=INK, width=2.4)
    line([(x0 + 8, y0 + 56), (x0 + 72, y0 + 56)], INK, 2.6)
    draw.rectangle(px_box([x0 + 50, y0 + 40, x0 + 66, y0 + 56]), fill=PAPER, outline=INK, width=X(2.0))
    for step in range(3):
        draw.rectangle(px_box([x0 + 53 + step * 4, y0 + 45, x0 + 55 + step * 4, y0 + 49]), fill=INK)
    line([(x0 + 58, y0 + 40), (x0 + 58, y0 + 30)], INK, 2.0)
    line([(x0 + 58, y0 + 30), (x0 + 70, y0 + 30)], INK, 2.0)
    for cx in (x0 + 22, x0 + 34, x0 + 46):
        poly(
            [(cx, y0 + 30), (cx + 6, y0 + 40), (cx + 4, y0 + 47), (cx - 4, y0 + 47), (cx - 6, y0 + 40)],
            fill=CRIMSON,
            outline=INK,
            width=1.6,
        )
    for step in range(3):
        disc((x0 + 20 + step * 12, y0 + 22, x0 + 26 + step * 12, y0 + 27), fill=None, outline=MUTED, width=1.2)


def art_game(x0, y0, x1, y1) -> None:
    stroke((x0, y0, x1, y1), RULE, 1)
    towers = [(8, 44, 20), (22, 36, 32), (34, 42, 46), (48, 30, 60)]
    for left, top, right in towers:
        draw.rectangle(px_box([x0 + left, y0 + top, x0 + right, y0 + 58]), fill=MUTED)
        for row in range(top + 4, 56, 6):
            for col in range(left + 3, right - 1, 5):
                draw.rectangle(px_box([x0 + col, y0 + row, x0 + col + 2, y0 + row + 2]), fill=PAPER)
    draw.rounded_rectangle(px_box([x0 + 10, y0 + 60, x0 + 62, y0 + 78]), radius=X(6), fill=PAPER, outline=INK, width=X(2.2))
    draw.rectangle(px_box([x0 + 20, y0 + 66, x0 + 22, y0 + 74]), fill=INK)
    draw.rectangle(px_box([x0 + 17, y0 + 69, x0 + 25, y0 + 71]), fill=INK)
    disc((x0 + 46, y0 + 66, x0 + 51, y0 + 71), fill=CRIMSON)
    disc((x0 + 52, y0 + 71, x0 + 57, y0 + 76), fill=PAPER, outline=INK, width=1.4)
    put_baseline(
        x0 + 64,
        y0 + 58,
        "VI",
        19,
        "serif",
        INK,
        cell="art.gta",
        cell_rect=(x0, y0, x1, y1),
        name="art.gta.vi",
    )


def masthead() -> None:
    rule_line([30, 30, 994, 30.8])
    put_baseline(30, 88, "THE WORLD TODAY", 50, "serif", INK, cell="masthead", cell_rect=(30, 30, 994, 100), name="masthead.title")
    put_baseline(
        994,
        66,
        "THURSDAY 19 NOVEMBER 2026",
        16,
        "sansb",
        INK,
        align="right",
        cell="masthead",
        cell_rect=(30, 30, 994, 100),
        name="masthead.date",
    )
    put_baseline(
        994,
        88,
        f"{TOTAL} STORIES \u00b7 SIX REGIONS \u00b7 ONE PAGE",
        12.5,
        "sans",
        MUTED,
        tracking=1.6,
        align="right",
        cell="masthead",
        cell_rect=(30, 30, 994, 100),
        name="masthead.dek",
    )
    rule_line([30, 100, 994, 103], INK)


def lead_block() -> None:
    cell, cell_rect = "lead", (30, 112, 344, 400)
    put(30, 112, LEAD["kicker"], 10, "sansb", CRIMSON, tracking=1.2, cell=cell, cell_rect=cell_rect, name="lead.kicker")
    bottom = block(30, 129, LEAD["head"], 30, "serif", 310, 4, 33.5, 26, INK, cell, cell_rect, "lead.head")
    block(30, bottom + 9, LEAD["deck"], 12, "sans", 310, 5, 15.6, 10, MUTED, cell, cell_rect, "lead.deck")
    put(30, 386, LEAD["source"], 9, "sansb", MUTED, tracking=1.1, cell=cell, cell_rect=cell_rect, name="lead.src")
    art_lead(352, 112, 612, 330)


def right_stack() -> None:
    positions = ((112, 250), (262, 400))
    for card, (top, bottom) in zip(RIGHT, positions):
        cell = f"card.{card['key']}"
        cell_rect = (628, top, 862, bottom)
        put(628, top + 4, card["kicker"], 9.5, "sansb", CRIMSON, tracking=1.0, cell=cell, cell_rect=cell_rect, name=cell + ".kicker")
        end = block(628, top + 19, card["head"], 18, "serif", 230, 3, 20.3, 13, INK, cell, cell_rect, cell + ".head")
        block(628, end + 3, card["deck"], 10.5, "sans", 230, 2, 11.7, 10, MUTED, cell, cell_rect, cell + ".deck")
        put_baseline(628, bottom - 7, card["num"], 24, "serif", CRIMSON, cell=cell, cell_rect=cell_rect, name=cell + ".num")
        art = art_icj if card["key"] == "icj" else art_markets
        art(910, top + 2, 994, top + 86)


def second_band() -> None:
    for index, card in enumerate(BAND):
        x0 = 30 + index * 326
        cell = f"band.{card['key']}"
        cell_rect = (x0 + 100, 412, x0 + 302, 560)
        put(x0 + 100, 415, card["kicker"], 9.5, "sansb", CRIMSON, tracking=1.0, cell=cell, cell_rect=cell_rect, name=cell + ".kicker")
        end = block(x0 + 100, 429, card["head"], 19, "serif", 200, 3, 21.6, 13, INK, cell, cell_rect, cell + ".head")
        block(x0 + 100, end + 4, card["deck"], 10.5, "sans", 200, 3, 12.2, 10, MUTED, cell, cell_rect, cell + ".deck")
        art = {"bridge": art_bridge, "hormuz": art_gulf, "gta": art_game}[card["key"]]
        art(x0, 414, x0 + 92, 506)
    rule_line([30, 568, 994, 568.8])
    put(30, 578, "THE DAY IN BRIEF \u00b7 SIXTEEN MORE STORIES", 10, "sansb", INK, tracking=1.2, cell="brief.header", cell_rect=(30, 570, 994, 592), name="brief.header")
    rule_line([30, 592, 994, 592.8])
    for column in range(3):
        x = 265.5 + column * 243
        rule_line([x, 604, x + 0.8, 904], RULE, 1.0)
    for index, (tag, headline) in enumerate(BRIEFS):
        column, row = divmod(index, 4)
        x = 30 + column * 243
        top = 604 + row * 76
        cell = f"brief.{index + 1}"
        cell_rect = (x, top, x + 229, top + 72)
        pill(x, top, tag, cell, cell_rect)
        block(x, top + 17, headline, 13.5, "sansb", 229, 3, 16.2, 12, INK, cell, cell_rect, cell + ".head")


def ticker_band() -> None:
    rule_line([30, 912, 994, 912.8])
    cell, cell_rect = "ticker", (30, 912, 994, 992)
    put(30, 916, "ALSO TODAY", 10, "sansb", INK, tracking=1.2, cell=cell, cell_rect=cell_rect, name="ticker.label")
    for index, item in enumerate(TICKER):
        column, row = divmod(index, 5)
        x = 30 + column * 498
        y = 930 + row * 12.2
        disc((x, y + 4.2, x + 3.4, y + 7.6), fill=CRIMSON)
        block(x + 9, y, item, 9.5, "sans", 455, 1, 11, 8, MUTED, cell, cell_rect, f"ticker.{index + 1}")


def audit() -> dict:
    out_of_cell = []
    outside_page = []
    for box in _boxes:
        x0, y0, x1, y1 = box["rect"]
        cx0, cy0, cx1, cy1 = box["cell_rect"]
        if x0 < cx0 - 0.6 or y0 < cy0 - 0.6 or x1 > cx1 + 0.6 or y1 > cy1 + 0.6:
            out_of_cell.append({"name": box["name"], "rect": box["rect"], "cell_rect": box["cell_rect"]})
        if x0 < -0.6 or y0 < -0.6 or x1 > W + 0.6 or y1 > W + 0.6:
            outside_page.append({"name": box["name"], "rect": box["rect"]})
    overlaps = []
    for i, first in enumerate(_boxes):
        for second in _boxes[i + 1 :]:
            if first["cell"] != second["cell"]:
                continue
            ax0, ay0, ax1, ay1 = first["rect"]
            bx0, by0, bx1, by1 = second["rect"]
            width = min(ax1, bx1) - max(ax0, bx0)
            height = min(ay1, by1) - max(ay0, by0)
            if width > 0.05 and height > 0.05:
                overlaps.append(
                    {
                        "cell": first["cell"],
                        "a": first["name"],
                        "b": second["name"],
                        "area": round(width * height, 2),
                    }
                )
    truncations = [{"name": box["name"], "text": box["text"]} for box in _boxes if box.get("truncated")]
    shrunk = [
        {"name": box["name"], "requested": box["requested_size"], "used": box["font_size"]}
        for box in _boxes
        if box.get("requested_size") and box["font_size"] < box["requested_size"]
    ]
    return {
        "canvas": [W, W],
        "stories": TOTAL,
        "scale": S,
        "fonts": FACE_FILES,
        "boxes": _boxes,
        "out_of_cell": out_of_cell,
        "outside_page": outside_page,
        "overlaps": overlaps,
        "truncations": truncations,
        "shrunk": shrunk,
    }


def main() -> None:
    masthead()
    lead_block()
    right_stack()
    second_band()
    ticker_band()
    final = image.resize((W, W), Image.LANCZOS)
    entry_path = ROOT / "entry.png"
    final.save(entry_path, format="PNG", optimize=True)
    final.resize((300, 300), Image.LANCZOS).save(ROOT / "preview-300.png", format="PNG", optimize=True)
    report = audit()
    (ROOT / "layout-audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(
        f"stories={report['stories']} boxes={len(report['boxes'])} "
        f"out_of_cell={len(report['out_of_cell'])} outside_page={len(report['outside_page'])} "
        f"overlaps={len(report['overlaps'])} truncations={len(report['truncations'])} "
        f"shrunk={len(report['shrunk'])} bytes={entry_path.stat().st_size}"
    )
    for item in report["out_of_cell"]:
        print("  out_of_cell", item)
    for item in report["overlaps"]:
        print("  overlap", item)
    for item in report["truncations"]:
        print("  truncated", item)


if __name__ == "__main__":
    main()
