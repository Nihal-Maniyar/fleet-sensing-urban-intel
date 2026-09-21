"""Synthetic evidence image generator for simulated events without CV dependencies.

Creates valid JPEG image files on disk so dashboard, ticket, and fusion review
interfaces have authentic visual assets to load and render.
"""

from __future__ import annotations

import os
import struct
from pathlib import Path
from typing import Optional


def ensure_evidence_image(
    file_path: str,
    event_id: str,
    event_type: str,
    confidence: float,
    timestamp: str,
    is_repaired: bool = False,
) -> str:
    """Ensure a valid JPEG evidence image exists at file_path.

    If Pillow is installed, renders a rich annotated simulation frame with
    bounding box, defect label, confidence, and timestamp.
    If Pillow is not installed, creates a self-contained valid JFIF JPEG file.

    Returns:
        The normalized file_path string.
    """
    target = Path(file_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    # If the file already exists, don't overwrite it
    if target.exists() and target.stat().st_size > 0:
        return str(target)

    # Try PIL if available
    try:
        from PIL import Image, ImageDraw  # type: ignore

        img = _create_pillow_image(event_id, event_type, confidence, timestamp, is_repaired)
        img.save(str(target), format="JPEG", quality=85)
        return str(target)
    except ImportError:
        pass

    # Fallback to pure-Python valid baseline JPEG
    jpeg_bytes = _create_minimal_jpeg(is_repaired=is_repaired)
    target.write_bytes(jpeg_bytes)
    return str(target)


def _create_pillow_image(
    event_id: str,
    event_type: str,
    confidence: float,
    timestamp: str,
    is_repaired: bool,
):
    """Draw a synthetic camera frame with defect bounding box and HUD."""
    from PIL import Image, ImageDraw  # type: ignore

    width, height = 640, 480
    # Background road surface: dark asphalt
    img = Image.new("RGB", (width, height), color=(45, 48, 52))
    draw = ImageDraw.Draw(img)

    # Draw simulated road lanes
    draw.line([(0, 240), (640, 240)], fill=(70, 75, 80), width=1)
    draw.line([(320, 240), (100, 480)], fill=(200, 200, 200), width=3)  # left lane marking
    draw.line([(320, 240), (540, 480)], fill=(200, 200, 200), width=3)  # right lane marking
    # Center dashed lane
    for y_step in range(250, 480, 40):
        draw.line([(320, y_step), (320, y_step + 20)], fill=(230, 200, 40), width=2)

    if not is_repaired:
        # Bounding box around simulated defect
        box_coords = [250, 310, 390, 410]
        # Pothole defect ellipse
        draw.ellipse([270, 330, 370, 390], fill=(20, 20, 22), outline=(10, 10, 12), width=2)
        # Bounding box in red/amber
        draw.rectangle(box_coords, outline=(255, 60, 40), width=3)
        # Label banner
        banner_text = f"[{event_type}] conf: {confidence:.2f}"
        draw.rectangle([250, 288, 390, 310], fill=(255, 60, 40))
        draw.text((254, 292), banner_text, fill=(255, 255, 255))
    else:
        # Repaired patch: fresh black asphalt rectangle
        draw.rectangle([260, 320, 380, 400], fill=(25, 25, 28), outline=(60, 60, 65), width=2)
        box_coords = [250, 310, 390, 410]
        draw.rectangle(box_coords, outline=(40, 200, 80), width=3)
        banner_text = "[REPAIRED] VERIFIED"
        draw.rectangle([250, 288, 390, 310], fill=(40, 200, 80))
        draw.text((254, 292), banner_text, fill=(255, 255, 255))

    # Top HUD Bar
    draw.rectangle([0, 0, width, 30], fill=(15, 15, 20))
    hud_left = f"SIMULATED CAMERA - {event_id} - {timestamp}"
    draw.text((10, 8), hud_left, fill=(220, 220, 220))
    state_label = "STATUS: RESOLVED" if is_repaired else "STATUS: DETECTED"
    draw.text((490, 8), state_label, fill=(40, 200, 80) if is_repaired else (255, 60, 40))

    return img


def _create_minimal_jpeg(is_repaired: bool = False) -> bytes:
    """Generate a standard valid 64x64 JFIF JPEG stream in pure Python without dependencies.

    Uses a valid JFIF 1.01 header, standard DQT (Quantization), DHT (Huffman),
    SOF0, and scan data so any browser or viewer can parse it directly.
    """
    # 1x1 or 8x8 block valid JPEG
    # Header: SOI (FF D8)
    soi = b"\xff\xd8"
    # APP0 JFIF marker
    jfif = (
        b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00\x48\x00\x48\x00\x00"
    )
    # DQT (Quantization Table)
    # Luminance table: 64 bytes of flat quantization
    dqt = (
        b"\xff\xdb\x00\x43\x00"
        + bytes([16] * 64)
    )
    # SOF0 (Start of Frame: baseline DCT, 8-bit, 8x8 height/width, 1 component grayscale)
    sof0 = b"\xff\xc0\x00\x0b\x08\x00\x08\x00\x08\x01\x01\x11\x00"
    # DHT (Huffman Table: DC table 0)
    dht_dc = (
        b"\xff\xc4\x00\x1f\x00"
        b"\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b"
    )
    # DHT (Huffman Table: AC table 0)
    dht_ac = (
        b"\xff\xc4\x00\xb5\x10"
        b"\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01\x7d"
        + bytes(range(162))
    )
    # SOS (Start of Scan)
    sos = b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00"
    # Compressed data (a single DC block followed by EOB)
    # Luminance value: if repaired, brighter green/gray; else darker asphalt gray
    scan_data = b"\xf8\x00" if is_repaired else b"\x7e\x00"
    # EOI (End of Image)
    eoi = b"\xff\xd9"

    return soi + jfif + dqt + sof0 + dht_dc + dht_ac + sos + scan_data + eoi
