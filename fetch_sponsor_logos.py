#!/usr/bin/env python3
"""
Fetch sponsor logos from https://www.emfcamp.org/sponsors

Downloads logos for the Palladium, Gold, and Badge tiers, converts SVGs to PNG,
and resizes all images to fit the badge's 240x240 round display.

Outputs PNGs to logos/ and updates the _SPONSORS list in app.py.

Requirements: pip install requests beautifulsoup4 cairosvg Pillow
"""

import io
import os
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

try:
    import cairosvg
except ImportError:
    cairosvg = None

try:
    from PIL import Image
except ImportError:
    Image = None

BASE_URL = "https://www.emfcamp.org"
SPONSORS_URL = f"{BASE_URL}/sponsors"
TARGET_TIERS = {"palladium", "gold", "badge"}
# Badge display is 240x240 but round — keep logos within a central area
LOGO_MAX_SIZE = 200


def fetch_sponsors():
    """Scrape the sponsors page and return a list of (tier, name, logo_url)."""
    resp = requests.get(SPONSORS_URL)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    sponsors = []
    for tier in TARGET_TIERS:
        container = soup.find("div", class_=re.compile(rf"sponsors-list--{tier}"))
        if container is None:
            print(f"Warning: tier '{tier}' not found on page")
            continue
        for sponsor_div in container.find_all("div", class_="sponsor"):
            img = sponsor_div.find("img")
            if img is None:
                continue
            name = img.get("alt", "unknown").strip()
            src = img.get("src", "")
            url = urljoin(BASE_URL, src)
            sponsors.append((tier, name, url))
            print(f"  [{tier}] {name}: {url}")

    return sponsors


def download_logo(url):
    """Download a logo and return (content_bytes, extension)."""
    resp = requests.get(url)
    resp.raise_for_status()
    ext = os.path.splitext(url.split("?")[0])[1].lower()
    return resp.content, ext


def svg_to_png(svg_bytes):
    """Convert SVG bytes to PNG bytes."""
    if cairosvg is None:
        print("Warning: cairosvg not installed, skipping SVG conversion")
        return None
    return cairosvg.svg2png(bytestring=svg_bytes, output_width=LOGO_MAX_SIZE)


def resize_to_fit(png_bytes, max_size=LOGO_MAX_SIZE):
    """Resize a PNG so it fits within max_size x max_size, preserving aspect ratio."""
    if Image is None:
        print("Warning: Pillow not installed, skipping resize")
        return png_bytes

    img = Image.open(io.BytesIO(png_bytes))
    img = img.convert("RGBA")

    w, h = img.size
    if w > max_size or h > max_size:
        scale = min(max_size / w, max_size / h)
        new_w, new_h = int(w * scale), int(h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def sanitise_filename(name):
    """Turn a sponsor name into a safe filename."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def update_app_py(app_path, manifest):
    """Update the _SPONSORS list in app.py with the new manifest data."""
    with open(app_path, "r") as f:
        content = f.read()

    # Build the new _SPONSORS block
    lines = ["_SPONSORS = ["]
    for entry in manifest:
        lines.append(
            f'    ("{entry["tier"]}", "{entry["name"]}", '
            f'"{entry["file"]}", {entry["w"]}, {entry["h"]}),'
        )
    lines.append("]")
    new_block = "\n".join(lines)

    # Replace the existing _SPONSORS block
    pattern = r"_SPONSORS\s*=\s*\[.*?\]"
    updated, count = re.subn(pattern, new_block, content, count=1, flags=re.DOTALL)
    if count == 0:
        print("Warning: could not find _SPONSORS list in app.py to update")
        return False

    with open(app_path, "w") as f:
        f.write(updated)
    return True


def main():
    project_dir = Path(__file__).resolve().parent
    logos_dir = project_dir / "logos"
    app_path = project_dir / "app.py"

    logos_dir.mkdir(parents=True, exist_ok=True)

    print(f"Fetching sponsors from {SPONSORS_URL}...")
    sponsors = fetch_sponsors()
    if not sponsors:
        print("No sponsors found!")
        sys.exit(1)

    print(f"\nFound {len(sponsors)} sponsors in tiers: {', '.join(TARGET_TIERS)}")

    manifest = []
    for tier, name, url in sponsors:
        print(f"\nProcessing: {name} ({tier})...")
        try:
            data, ext = download_logo(url)
        except Exception as e:
            print(f"  Failed to download: {e}")
            continue

        # Convert SVG to PNG
        if ext == ".svg":
            print("  Converting SVG to PNG...")
            data = svg_to_png(data)
            if data is None:
                continue
            ext = ".png"

        # Resize raster images
        if ext in (".png", ".jpg", ".jpeg"):
            print("  Resizing to fit display...")
            data = resize_to_fit(data)

        # Get final image dimensions for aspect-ratio-correct rendering
        img_w, img_h = 0, 0
        if Image is not None:
            img = Image.open(io.BytesIO(data))
            img_w, img_h = img.size

        filename = f"{sanitise_filename(name)}.png"
        filepath = logos_dir / filename
        with open(filepath, "wb") as f:
            f.write(data)
        print(f"  Saved: {filepath} ({len(data)} bytes, {img_w}x{img_h})")
        manifest.append(
            {"tier": tier, "name": name, "file": filename, "w": img_w, "h": img_h}
        )

    # Update _SPONSORS in app.py
    if app_path.exists():
        if update_app_py(app_path, manifest):
            print(f"\nUpdated _SPONSORS in {app_path}")
        else:
            print(f"\nWarning: failed to update {app_path}")
    else:
        print(f"\nWarning: {app_path} not found, skipping app.py update")

    print(f"\nDone! {len(manifest)} logos saved to {logos_dir}")


if __name__ == "__main__":
    main()
