"""Create a concise SIH demo video for the AnnSetu project."""
from pathlib import Path
import math
import textwrap

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT, FPS = 1280, 720, 30
OUT = Path(__file__).with_name("AnnSetu_SIH_Demo.mp4")
FONT = "C:/Windows/Fonts/arial.ttf"
FONT_BOLD = "C:/Windows/Fonts/arialbd.ttf"


def font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT, size)


def canvas():
    image = Image.new("RGB", (WIDTH, HEIGHT), "#071a2b")
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        t = y / HEIGHT
        draw.line((0, y, WIDTH, y), fill=(7, int(26 + 22 * t), int(43 + 28 * t)))
    return image, draw


def card(draw, box, title, body, accent="#43d17a"):
    x, y, w, h = box
    draw.rounded_rectangle((x, y, x + w, y + h), radius=20, fill="#102c43", outline="#28506b", width=2)
    draw.rounded_rectangle((x, y, x + 7, y + h), radius=4, fill=accent)
    draw.text((x + 28, y + 25), title, font=font(24, True), fill="white")
    lines = textwrap.wrap(body, width=max(20, int(w / 15)))
    for i, line in enumerate(lines[:4]):
        draw.text((x + 28, y + 70 + i * 30), line, font=font(18), fill="#c8d8e5")


def slide(title, subtitle, cards=None, metric=None, progress=None):
    image, draw = canvas()
    draw.text((72, 58), "ANNSETU", font=font(20, True), fill="#62e696")
    draw.text((72, 100), title, font=font(45, True), fill="white")
    for i, line in enumerate(textwrap.wrap(subtitle, width=70)):
        draw.text((74, 168 + i * 31), line, font=font(21), fill="#b9cad8")
    if metric:
        number, label = metric
        draw.rounded_rectangle((925, 72, 1190, 198), radius=18, fill="#143750")
        draw.text((954, 91), number, font=font(42, True), fill="#62e696")
        draw.text((954, 148), label, font=font(16), fill="#d2e3ec")
    if cards:
        for c in cards:
            card(draw, *c)
    if progress:
        labels, active = progress
        start_x, y, gap = 82, 620, 220
        for i, label in enumerate(labels):
            color = "#62e696" if i <= active else "#426174"
            draw.ellipse((start_x + i * gap, y, start_x + i * gap + 18, y + 18), fill=color)
            if i < len(labels) - 1:
                draw.line((start_x + i * gap + 20, y + 9, start_x + (i + 1) * gap - 10, y + 9), fill=color, width=4)
            draw.text((start_x + i * gap, y + 30), label, font=font(15, True), fill="#d4e2eb")
    return image


slides = [
    slide("A digital bridge between farmer and mandi", "AnnSetu makes agricultural procurement transparent, predictable and faster.", [
        ((74, 275, 345, 220), "SMART SLOTS", "Farmers choose a crop, centre, date and time slot."),
        ((468, 275, 345, 220), "LIVE QUEUE", "Gate entry and queue status are updated in real time."),
        ((862, 275, 345, 220), "TRACEABLE PAYMENTS", "Quality, weighment and mock PFMS payment are recorded."),
    ], ("140M", "farmers addressed")),
    slide("1. Farmer books a convenient slot", "A farmer selects crop, quantity, mandi and preferred time. AnnSetu generates a token and QR code.", [
        ((110, 275, 500, 200), "FARMER PORTAL", "Book a slot\nReceive QR token\nTrack the complete procurement timeline"),
        ((670, 275, 500, 200), "VERIFIED IN LIVE TEST", "New booking: COT-00003\nPreferred 09:00 slot accepted\n12.5 quintals declared"),
    ], progress=(["BOOK", "ARRIVE", "PROCESS", "PAY"], 0)),
    slide("2. Mandi staff manages entry and queue", "Staff scan or enter the token at the gate, then call the next farmer from a live queue.", [
        ((110, 275, 500, 200), "GATE ENTRY", "Token validation\nArrival status\nQueue position and estimated wait"),
        ((670, 275, 500, 200), "QUEUE CONTROL", "COT-00003 called\nReal-time room updates\nClear handoff to transaction desk"),
    ], progress=(["BOOK", "ARRIVE", "PROCESS", "PAY"], 1)),
    slide("3. Quality and weighment are recorded", "The staff captures the lot quality and weights. Validation prevents an invalid tare weight.", [
        ((110, 275, 500, 200), "QUALITY", "Moisture: 11.2%\nForeign matter: 0.4%\nResult: ACCEPTED"),
        ((670, 275, 500, 200), "WEIGHMENT", "Gross: 13.2 Q\nTare: 0.7 Q\nNet: 12.5 Q"),
    ], progress=(["BOOK", "ARRIVE", "PROCESS", "PAY"], 2)),
    slide("4. Officer confirms procurement and payment", "The officer approves only quality-cleared, weighed lots. Mock PFMS returns a payment reference and UTR.", [
        ((110, 275, 500, 200), "PROCUREMENT", "Status: CONFIRMED\nMSP-calculated amount\nDigital audit trail"),
        ((670, 275, 500, 200), "MOCK PFMS", "Status: PAID\nReference: PFMS-BB4D47L4SU\nUTR generated successfully"),
    ], progress=(["BOOK", "ARRIVE", "PROCESS", "PAY"], 3)),
    slide("5. Full transparency for every stakeholder", "Farmer timelines, officer monitoring and government analytics bring procurement into one trusted system.", [
        ((74, 275, 345, 200), "FARMER", "Timeline, notifications and payment status"),
        ((468, 275, 345, 200), "OFFICER", "Alerts, queue visibility and approvals"),
        ((862, 275, 345, 200), "GOVERNMENT", "Procurement analytics and anomaly flags"),
    ], ("100%", "digital audit trail")),
    slide("AnnSetu — ready for SIH demonstration", "Tested live with five role-based accounts: farmer, staff, officer, government admin and CSC operator.", [
        ((240, 295, 800, 150), "LIVE VALIDATION COMPLETE", "Health check passed • all five logins passed • end-to-end payment flow passed"),
    ], ("PAID", "end-to-end demo outcome")),
]


def frame(image, alpha=1.0):
    arr = np.asarray(image).copy()
    if alpha < 1:
        arr = (arr.astype(np.float32) * alpha).astype(np.uint8)
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


writer = cv2.VideoWriter(str(OUT), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (WIDTH, HEIGHT))
for image in slides:
    # 0.35 sec fade-in, 3.3 sec readable hold, 0.35 sec fade-out.
    for n in range(12):
        writer.write(frame(image, (n + 1) / 12))
    for _ in range(100):
        writer.write(frame(image))
    for n in range(12):
        writer.write(frame(image, 1 - (n + 1) / 12))
writer.release()
print(OUT)
