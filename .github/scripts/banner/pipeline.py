#!/usr/bin/env python3
"""
Phase 1 banner data generation — dithered portrait + logo grids.
Source of truth: portrait.png, logos/*.svg, and this script.
Outputs: data/portrait.npz, data/logos.npz.

generate_banner.py (same directory) turns these .npz files into the animated
dark.svg / light.svg.

Pipeline per Prompt.md:
- crop head+shoulders, 300x340 grid, 1-bit Floyd-Steinberg dither, serpentine
- contrast 1.3x, autocontrast(cutoff=1), UnsharpMask(radius=3, percent=140)
- dark: segment bg out (color-distance threshold, binary closing, fill holes,
  largest component) so dots draw the lit subject. light: keep bg, dots draw darks
- dot density matched to ~17k (dark) / ~39k (light) via a tone power transform,
  so the portrait keeps the reference's sparse, elegant look for any input photo
- logos rasterized from simple-icons SVGs by dense curve sampling
"""
import os, sys, math, json, argparse, html
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
LOGOS = os.path.join(HERE, "logos")

GRID_W, GRID_H = 300, 340          # portrait dot grid
CROP_FRAC = 0.92                   # head+shoulders crop of the square image
CONTRAST = 1.3
UNSHARP_R = 3
UNSHARP_P = 140

# ---------- portrait preparation ----------

def prep_portrait(path):
    """Load, crop, build a luminance tone image for dithering."""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    s = min(w, h)
    # center square crop
    left = (w - s) // 2; top = (h - s) // 2
    im = im.crop((left, top, left + s, top + s))
    # head+shoulders: keep the upper-central crop
    c = int(s * CROP_FRAC)
    x0 = (s - c) // 2; y0 = int(s * 0.04)
    im = im.crop((x0, y0, x0 + c, y0 + c))
    im = im.resize((GRID_W, GRID_H), Image.LANCZOS)
    # enhancement
    im = ImageEnhance.Contrast(im).enhance(CONTRAST)
    im = ImageOps.autocontrast(im, cutoff=1)
    im = im.filter(ImageFilter.UnsharpMask(radius=UNSHARP_R, percent=UNSHARP_P))
    return im

def segment_bg(im_arr, tol=0.08):
    """Return subject mask: True where subject (foreground).

    Border-seeded flood fill: the frame border is background; any pixel whose
    max-channel colour differs from its connected neighbour by < tol is part of
    the same background region and gets flooded out. This handles photo walls
    with uneven lighting better than a global gradient model (which lets a
    bright wall through and inflates dark-mode ink)."""
    a = im_arr.astype(np.float64) / 255.0
    h, w, _ = a.shape
    bg = np.zeros((h, w), dtype=bool)
    stack = []
    for x in range(w):
        bg[0, x] = bg[h - 1, x] = True
        stack.append((0, x)); stack.append((h - 1, x))
    for y in range(h):
        bg[y, 0] = bg[y, w - 1] = True
        stack.append((y, 0)); stack.append((y, w - 1))
    while stack:
        y, x = stack.pop()
        c = a[y, x]
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not bg[ny, nx]:
                if np.abs(a[ny, nx] - c).max() < tol:
                    bg[ny, nx] = True
                    stack.append((ny, nx))
    fg = ~bg
    # clean: closing then fill holes, keep largest component
    fg = ndimage.binary_closing(fg, iterations=6)
    fg = ndimage.binary_fill_holes(fg)
    lab, n = ndimage.label(fg)
    if n > 0:
        sizes = ndimage.sum(fg, lab, range(1, n + 1))
        keep = lab == (np.argmax(sizes) + 1)
        fg = keep
    fg = ndimage.binary_opening(fg, iterations=3)
    return fg

def tone_for_dither(im_arr, mask):
    """Single-hue tone in [0,1]; density encodes the portrait.
    dark: lit subject only (mask foreground); light: dark parts (invert)."""
    lum = np.array(Image.fromarray(im_arr).convert("L"), dtype=float) / 255.0
    # light mode: draw the DARK parts of the photo -> invert
    tone = 1.0 - lum
    # dark mode: draw the LIT subject -> mask foreground, value = lum inside
    tone_dark = lum * mask
    return tone_dark, tone

def floyd_steinberg(tone):
    """1-bit dither, serpentine scan. Returns bool grid (True=dot)."""
    a = tone.copy()
    h, w = a.shape
    out = np.zeros((h, w), dtype=bool)
    for y in range(h):
        if y % 2 == 0:
            rng = range(w)
        else:
            rng = range(w - 1, -1, -1)
        for x in rng:
            old = a[y, x]
            nv = 1.0 if old > 0.5 else 0.0
            out[y, x] = nv == 1.0
            err = old - nv
            if x + 1 < w: a[y, x + 1] += err * 7 / 16
            if y + 1 < h:
                if x > 0: a[y + 1, x - 1] += err * 3 / 16
                a[y + 1, x] += err * 5 / 16
                if x + 1 < w: a[y + 1, x + 1] += err * 1 / 16
    return out

def match_ink(tone, target_frac):
    """Scale a tone grid with tone**p so 1-bit dither ink lands on target_frac.
    Returns (tone_scaled, p). p>1 darkens midtones, keeping highlights dense."""
    if target_frac is None:
        return tone, 1.0
    tone = np.clip(tone, 0.0, 1.0)
    def ink(p):
        return floyd_steinberg(tone ** p).mean()
    if ink(1.0) <= target_frac:
        return tone, 1.0
    lo, hi = 1.0, 12.0
    for _ in range(28):
        mid = (lo + hi) / 2.0
        if ink(mid) > target_frac:
            lo = mid
        else:
            hi = mid
    p = (lo + hi) / 2.0
    return tone ** p, p

def runs_to_path(dots, cell, origin=(0, 0)):
    """Convert bool grid to horizontal run <path> data. crispEdges-friendly."""
    h, w = dots.shape
    segs = []
    for y in range(h):
        x = 0
        while x < w:
            if dots[y, x]:
                x0 = x
                while x < w and dots[y, x]:
                    x += 1
                x1 = x
                segs.append(f"M{origin[0]+x0*cell:.1f} {origin[1]+y*cell:.1f}h{x1-x0}")
            else:
                x += 1
    return "".join(segs)

# ---------- logo rasterization ----------

def rasterize_logo_svg(path, n=140):
    """Rasterize a simple-icons 24x24 SVG path to an n x n bool grid.
    cairosvg renders the real path; the alpha channel is the dot mask."""
    import io
    import cairosvg
    from PIL import Image

    png = cairosvg.svg2png(url=path, output_width=n, output_height=n)
    img = Image.open(io.BytesIO(png)).convert("RGBA")
    a = np.array(img)
    return a[:, :, 3] > 64

# ---------- main ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--portrait", default="portrait.png")
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--only-data", action="store_true")
    ap.add_argument("--target-ink-dark", type=float, default=0.167,
                    help="dark-mode dot density as a fraction of the grid (default 0.167 ~ 17k dots)")
    ap.add_argument("--target-ink-light", type=float, default=0.385,
                    help="light-mode dot density (default 0.385 ~ 39k dots)")
    ap.add_argument("--tol", type=float, default=0.08,
                    help="background flood-fill tolerance (default 0.08; raise to carve more)")
    args = ap.parse_args()

    os.makedirs(DATA, exist_ok=True)

    im = prep_portrait(args.portrait)
    arr = np.array(im)
    mask = segment_bg(arr, args.tol)
    tone_dark, tone_light = tone_for_dither(arr, mask)
    tone_dark, pd = match_ink(tone_dark, args.target_ink_dark)
    tone_light, pl = match_ink(tone_light, args.target_ink_light)
    dots_dark = floyd_steinberg(tone_dark)
    dots_light = floyd_steinberg(tone_light)
    # save source-of-truth data
    np.savez_compressed(
        os.path.join(DATA, "portrait.npz"),
        dots_dark=dots_dark, dots_light=dots_light, mask=mask,
    )
    print("portrait dots dark", int(dots_dark.sum()), "light", int(dots_light.sum()))
    print("density power: dark p=%.2f light p=%.2f" % (pd, pl))
    print("mask foreground px", int(mask.sum()), "of", mask.size)

    # logos
    logos = {}
    for fn in sorted(os.listdir(LOGOS)):
        if fn.endswith(".svg"):
            key = fn[:-4]
            g = rasterize_logo_svg(os.path.join(LOGOS, fn))
            if g is not None:
                logos[key] = g
                print("logo", key, "ink", int(g.sum()))
    np.savez_compressed(os.path.join(DATA, "logos.npz"), **logos)
    print("saved data/portrait.npz, data/logos.npz")

if __name__ == "__main__":
    main()
