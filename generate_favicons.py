#!/usr/bin/env python3
"""
Generate complete favicon suite for Chilika Institute of Technology (CIT) Campus ERP:
- favicon.ico (multi-resolution 16x16, 32x32, 48x48)
- favicon-16x16.png
- favicon-32x32.png
- favicon-48x48.png
- apple-touch-icon.png (180x180)
- android-chrome-192x192.png
- android-chrome-512x512.png
- site.webmanifest
"""
import math
import struct
import zlib
import os
import json

def create_png(width, height, rgba_data):
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)

    raw_data = bytearray()
    row_bytes = width * 4
    for y in range(height):
        raw_data.append(0) # filter type 0 (None)
        raw_data.extend(rgba_data[y * row_bytes : (y + 1) * row_bytes])

    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
    idat = chunk(b'IDAT', zlib.compress(bytes(raw_data), 9))
    iend = chunk(b'IEND', b'')
    return sig + ihdr + idat + iend

def create_ico(png_dict):
    count = len(png_dict)
    header = struct.pack('<HHH', 0, 1, count)
    offset = 6 + 16 * count
    entries = []
    images = []
    for size, data in png_dict.items():
        w = size if size < 256 else 0
        h = size if size < 256 else 0
        entry = struct.pack('<BBBBHHII', w, h, 0, 0, 1, 32, len(data), offset)
        entries.append(entry)
        images.append(data)
        offset += len(data)
    return header + b''.join(entries) + b''.join(images)

def render_icon(size):
    buf = bytearray(size * size * 4)
    cx, cy = (size - 1) / 2.0, (size - 1) / 2.0
    corner_r = size * 0.22

    for y in range(size):
        for x in range(size):
            idx = (y * size + x) * 4
            dx = max(0.0, abs(x - cx) - (cx - corner_r))
            dy = max(0.0, abs(y - cy) - (cy - corner_r))
            dist_corner = math.sqrt(dx * dx + dy * dy)
            alpha_corner = max(0.0, min(1.0, corner_r - dist_corner + 0.5))

            if alpha_corner <= 0.0:
                buf[idx:idx+4] = b'\x00\x00\x00\x00'
                continue

            # Vertical gradient on CIT Maroon (#600f1c)
            grad = y / size
            cr = int(96 * (1.1 - 0.25 * grad))
            cg = int(15 * (1.1 - 0.25 * grad))
            cb = int(28 * (1.1 - 0.25 * grad))

            # Outer border line (gold #f59e0b)
            border_width = max(1.2, size * 0.04)
            is_border = (abs(x - cx) > cx - border_width or abs(y - cy) > cy - border_width or dist_corner > corner_r - border_width)
            if is_border:
                cr, cg, cb = 245, 158, 11

            # Academic Crest Geometry (Mortarboard & Arch)
            nx = (x - cx) / size
            ny = (y - cy) / size

            # Top Diamond (Cap)
            d_diamond = abs(nx) / 0.32 + abs(ny + 0.13) / 0.16
            if d_diamond <= 1.0:
                cr, cg, cb = 255, 255, 255
            elif -0.05 <= ny <= 0.22 and abs(nx) <= 0.22:
                # Lower Base / Pillars
                cr, cg, cb = 254, 243, 199
                # Gold tassel & trim
                if abs(nx) > 0.17 or ny > 0.17:
                    cr, cg, cb = 245, 158, 11
            elif 0.26 <= ny <= 0.36 and size >= 48:
                # Underline bar on larger icons
                if abs(nx) <= 0.28:
                    cr, cg, cb = 255, 255, 255

            ca = int(255 * alpha_corner)
            buf[idx] = max(0, min(255, cr))
            buf[idx+1] = max(0, min(255, cg))
            buf[idx+2] = max(0, min(255, cb))
            buf[idx+3] = ca
    return bytes(buf)

def generate_all():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    public_dir = os.path.join(base_dir, "public")
    assets_dir = os.path.join(base_dir, "assets")

    os.makedirs(public_dir, exist_ok=True)
    os.makedirs(assets_dir, exist_ok=True)

    sizes = [16, 32, 48, 180, 192, 512]
    png_images = {}

    for s in sizes:
        rgba = render_icon(s)
        png = create_png(s, s, rgba)
        png_images[s] = png

    # File mappings
    file_map = {
        "favicon-16x16.png": png_images[16],
        "favicon-32x32.png": png_images[32],
        "favicon-48x48.png": png_images[48],
        "apple-touch-icon.png": png_images[180],
        "android-chrome-192x192.png": png_images[192],
        "android-chrome-512x512.png": png_images[512],
    }

    # Generate multi-res ICO (16, 32, 48)
    ico_data = create_ico({
        16: png_images[16],
        32: png_images[32],
        48: png_images[48]
    })
    file_map["favicon.ico"] = ico_data

    # Generate site.webmanifest
    manifest = {
        "name": "Chilika Institute of Technology (CIT) Campus ERP",
        "short_name": "CIT Campus ERP",
        "description": "Academic Timetable & Venue Operations Platform for Chilika Institute of Technology",
        "icons": [
            {
                "src": "/public/android-chrome-192x192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "/public/android-chrome-512x512.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ],
        "theme_color": "#600f1c",
        "background_color": "#fbf6ee",
        "display": "standalone",
        "start_url": "/"
    }
    manifest_bytes = json.dumps(manifest, indent=2).encode('utf-8')
    file_map["site.webmanifest"] = manifest_bytes

    # Write to root, public/, and assets/
    destinations = [base_dir, public_dir, assets_dir]
    for dest in destinations:
        for filename, data in file_map.items():
            path = os.path.join(dest, filename)
            with open(path, "wb") as f:
                f.write(data)

    print(f"Successfully generated {len(file_map)} favicon & manifest assets in root, public/, and assets/!")

if __name__ == "__main__":
    generate_all()
