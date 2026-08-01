#!/usr/bin/env python3
"""
Phase 1 banner builder — turns data/portrait.npz + data/logos.npz into the
animated dark.svg / light.svg terminal banner (1180x610).

Structure (matches the approved reference style, per Prompt.md):
- defs: accent, asciiGrad, panelGrad, glow8, glow3, txtGlow, winClip, tv rect
- chrome: title bar, VISUAL.MAP label, portrait frame, corner brackets
- portrait layer 1: ~60 interleaved random groups fade in (0.2s..2.17s)
- portrait layer 2: ~94 drift bands, each translating ~42% toward the logo
  centroid while fading, on the 13.9s loop
- logo layers: AWS, Azure, GCP and DevOps wordmarks drawn as path dots (same
  mechanism as the portrait so they render reliably), each fading in during its
  own slot of the loop while the portrait is hidden
- SYSTEM.INFO panel with dotted leaders, LIVE badge, email pill, 16 rows

Usage: python generate_banner.py [--outdir .] [--portrait-dots 900]
"""
import os, math, random
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
DEFAULT_OUT = os.path.join(HERE, "..", "..", "..")   # repo root

GRID_W, GRID_H = 300, 340
N_INTRO = 60
BAND_NOISE = 4.0
DRIFT_K = 0.44
LOGO_TARGET = (150, 175)          # grid-space centre for each scaled logo
LOGO_MAX = (175, 118)             # max grid-space w,h a logo may occupy
# each logo gets a slot in the 13.9s loop (keytimes/opacity values)
LOGO_SLOTS = [
    ("aws",   "0;0.300;0.320;0.415;0.435;1", "0;0;1;1;0;0"),
    ("azure", "0;0.435;0.455;0.550;0.570;1", "0;0;1;1;0;0"),
    ("gcp",   "0;0.570;0.590;0.685;0.705;1", "0;0;1;1;0;0"),
    ("devops","0;0.705;0.725;0.880;0.900;1", "0;0;1;1;0;0"),
]
KEYTIMES = "0.000;0.194;0.288;0.432;0.525;0.669;0.763;0.906;1.000"

PILL_EMAIL = "bhupendrabhati05@gmail.com"
TITLE = "bhupendrabhati05@gmail.com - % ./profile.sh --live"
ARIA = "Bhupendra Bhati \u2014 profile.sh --live"

# label, value, begin s, y  (spacing/timings from the reference panel)
INFO_ROWS = [
    ("Subject",     "Bhupendra Bhati",                         0.90, 162),
    ("Role",        "Cloud DevOps Engineer",                   1.02, 185),
    ("Origin",      "Jaipur, India",                           1.14, 208),
    ("Education",   "B.Tech. I.T., PG in Cloud Computing",     1.26, 231),
    ("Status",      "Building + Learning + Shipping",          1.38, 254),
    ("ToolChain",   "VS Code, Linux, Git, Docker, K8s, Terraform", 1.50, 277),
    ("Core.Lang",   "Bash/Shell Script, HCL",                  1.72, 308),
    ("Core.Frontend", "HTML, CSS",                             1.84, 331),
    ("Core.Backend",  "Nginx",                                 1.96, 354),
    ("Core.Database", "MySQL",                                 2.08, 377),
    ("Core.Infra",    "AWS, Azure, GCP",                       2.20, 400),
    ("Grid.Mail",     PILL_EMAIL,                              2.42, 431),
    ("Grid.Portfolio","coming soon",                           2.66, 477),
    ("Grid.LinkedIn", "bhupendrabhati",                        2.78, 500),
    ("Grid.GitHub",   "@bhupendrabhati",                       2.90, 523),
    ("Grid.Facebook", "PalEkHaseenLamha",                      3.02, 546),
]

THEMES = {
    "dark": dict(
        tv="tvdark", port="#A78BFA",
        accent=("#7C3AED", "#22D3EE", "#10B981"),
        ascii_=("#60A5FA", "#A78BFA", "#22D3EE"),
        panel=("#0A101F", "#0C1426"), bg="#070B16",
        titlebar="#0B1222", chrome_line="rgba(255,255,255,0.10)",
        title_fill="#94A3B8", visual_fill="#475569",
        frame_stroke="#22D3EE", frame_fill="#0A101F",
        frame_stroke2="rgba(34,211,238,0.35)",
        corner="#22D3EE", info="#22D3EE", live="#F87171",
        pill="#4C1D95", pill_txt="#E9D5FF",
        label="#22D3EE", dots="rgba(148,163,184,0.35)", value="#F8FAFC",
    ),
    "light": dict(
        tv="tvlight", port="#7C3AED",
        accent=("#2563EB", "#06B6D4", "#10B981"),
        ascii_=("#1D4ED8", "#7C3AED", "#0891B2"),
        panel=("#F8FAFC", "#EEF2F7"), bg="#FFFFFF",
        titlebar="#F1F5F9", chrome_line="rgba(15,23,42,0.10)",
        title_fill="#475569", visual_fill="#94A3B8",
        frame_stroke="#06B6D4", frame_fill="#F8FAFC",
        frame_stroke2="rgba(8,145,178,0.40)",
        corner="#06B6D4", info="#0891B2", live="#DC2626",
        pill="#DBEAFE", pill_txt="#1D4ED8",
        label="#0891B2", dots="rgba(15,23,42,0.25)", value="#0F172A",
    ),
}


def runs(positions):
    """Positions -> <path> d with horizontal runs merged (crispEdges friendly)."""
    by_row = {}
    for x, y in positions:
        by_row.setdefault(y, []).append(x)
    parts = []
    for y in sorted(by_row):
        xs = sorted(set(by_row[y]))
        i = 0
        while i < len(xs):
            x0 = x1 = xs[i]
            while i + 1 < len(xs) and xs[i + 1] == x1 + 1:
                x1 = xs[i + 1]
                i += 1
            w = x1 - x0 + 1
            parts.append("M%d %dh%dv1h-%dz" % (x0, y, w, w))
            i += 1
    return "".join(parts)


def dots_to_positions(dots):
    ys, xs = np.nonzero(dots)
    return list(zip(xs.tolist(), ys.tolist()))


def intro_groups(positions):
    """60 interleaved groups: dot i -> group i%60, scattered across the portrait."""
    groups = [[] for _ in range(N_INTRO)]
    for i, p in enumerate(positions):
        groups[i % N_INTRO].append(p)
    out = []
    for g in range(N_INTRO):
        begin = 0.20 + g * 0.0333
        out.append(
            '<g opacity="0"><animate attributeName="opacity" values="0;1" dur="0.9s" '
            'begin="%.2fs" fill="freeze" calcMode="spline" keyTimes="0;1" '
            'keySplines=".4 0 .2 1"/><path d="%s"/></g>\n' % (begin, runs(groups[g]))
        )
    return "".join(out)


def pick_band_cell(positions, rng, target=94):
    """Smallest cell size giving at most `target` non-empty drift bands."""
    for cell in (20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40):
        stride = math.ceil(GRID_W / cell)
        keys = set()
        for p in positions:
            nx = p[0] + rng.gauss(0, BAND_NOISE)
            ny = p[1] + rng.gauss(0, BAND_NOISE)
            keys.add((int(ny // cell) * stride) + int(nx // cell))
        if len(keys) <= target:
            return cell
    return 40


def drift_bands(positions, target, rng, cell):
    """Spatial cells with per-dot noise; each band drifts ~DRIFT_K to target."""
    stride = math.ceil(GRID_W / cell)
    cells = {}
    for p in positions:
        nx = p[0] + rng.gauss(0, BAND_NOISE)
        ny = p[1] + rng.gauss(0, BAND_NOISE)
        key = int(ny // cell) * stride + int(nx // cell)
        cells.setdefault(key, []).append(p)
    out = []
    for key in sorted(cells):
        pts = cells[key]
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        dx = int(round((target[0] - cx) * DRIFT_K + rng.uniform(-2, 2)))
        dy = int(round((target[1] - cy) * DRIFT_K + rng.uniform(-2, 2)))
        tv = ";%d %d;%d %d;%d %d;%d %d;%d %d;%d %d" % (dx, dy, dx, dy, dx, dy, dx, dy, dx, dy, dx, dy)
        out.append(
            '<g opacity="1"><animate attributeName="opacity" values="1;1;0;0;0;0;0;0;1" '
            'keyTimes="%s" dur="13.9s" begin="3.2s" repeatCount="indefinite"/>'
            '<animateTransform attributeName="transform" type="translate" '
            'values="0 0;0 0%s;0 0" keyTimes="%s" dur="13.9s" begin="3.2s" '
            'repeatCount="indefinite"/><path d="%s"/></g>\n'
            % (KEYTIMES, tv, KEYTIMES, runs(pts))
        )
    return "".join(out)


def fit_logo(logo_grid):
    """Scale a logo grid to fit LOGO_MAX (aspect preserved), centred at
    LOGO_TARGET, returning dot positions in grid coords."""
    ys, xs = np.nonzero(logo_grid)
    w = xs.max() - xs.min() + 1
    h = ys.max() - ys.min() + 1
    scale = min(LOGO_MAX[0] / w, LOGO_MAX[1] / h)
    cxs = (xs.min() + xs.max()) / 2.0
    cys = (ys.min() + ys.max()) / 2.0
    tx, ty = LOGO_TARGET
    return [
        (int(round(tx + (float(x) - cxs) * scale)),
         int(round(ty + (float(y) - cys) * scale)))
        for x, y in zip(xs.tolist(), ys.tolist())
    ]


def logo_layers(logos_data, fill):
    """One path-dot layer per cloud logo, each fading in during its slot on the
    loop while the portrait fades out (path-based, so it renders reliably)."""
    out = []
    for name, kt, val in LOGO_SLOTS:
        out.append(
            '<g transform="translate(50,86) scale(1.2400,1.4471)" fill="%s" '
            'shape-rendering="crispEdges" opacity="0">\n'
            '<animate attributeName="opacity" values="%s" keyTimes="%s" dur="13.9s" '
            'begin="3.2s" repeatCount="indefinite"/>\n'
            '<path d="%s"/>\n</g>\n' % (fill, val, kt, runs(fit_logo(logos_data[name])))
        )
    return "".join(out)


def info_panel(t):
    rows = []
    for label, value, begin, y in INFO_ROWS:
        dots = max(1, 78 - len(label) - 1 - (len(value) + 1))
        leader = "".join("." for _ in range(dots))
        rows.append(
            '<g opacity="0"><animate attributeName="opacity" from="0" to="1" dur="0.4s" '
            'begin="%.2fs" fill="freeze"/><animateTransform attributeName="transform" '
            'type="translate" values="-8 0;0 0" dur="0.4s" begin="%.2fs" fill="freeze"/>'
            '<text x="470" y="%d" font-size="14" textLength="655" '
            'lengthAdjust="spacingAndGlyphs" xml:space="preserve">'
            '<tspan fill="%s">%s </tspan><tspan fill="%s">%s</tspan>'
            '<tspan fill="%s" font-weight="600"> %s</tspan></text></g>\n'
            % (begin, begin, y, t["label"], label, t["dots"], leader, t["value"], value)
        )
    return "".join(rows)


def build_theme(name, portrait_dots, logos_data, rng):
    t = THEMES[name]
    positions = dots_to_positions(portrait_dots)
    target = LOGO_TARGET

    s = []
    a = s.append
    c0, c1, c2 = t["accent"]
    a0, a1, a2 = t["ascii_"]
    p0, p1 = t["panel"]
    a('<svg xmlns="http://www.w3.org/2000/svg" width="1180" height="610" '
      'viewBox="0 0 1180 610" '
      'font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,\'Liberation Mono\',monospace" '
      'role="img" aria-label="%s">\n' % ARIA)
    a("<defs>\n")
    a('<linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">\n')
    a('      <stop offset="0" stop-color="%s"><animate attributeName="stop-color" '
      'values="%s;%s;%s;%s" dur="10s" repeatCount="indefinite"/></stop>\n'
      % (c0, c0, c1, c2, c0))
    a('      <stop offset="0.5" stop-color="%s"><animate attributeName="stop-color" '
      'values="%s;%s;%s;%s" dur="10s" repeatCount="indefinite"/></stop>\n'
      % (c1, c1, c2, c0, c1))
    a('      <stop offset="1" stop-color="%s"><animate attributeName="stop-color" '
      'values="%s;%s;%s;%s" dur="10s" repeatCount="indefinite"/></stop>\n'
      % (c2, c2, c0, c1, c2))
    a("    </linearGradient>\n")
    a('<linearGradient id="asciiGrad" x1="0" y1="0" x2="0" y2="520" '
      'gradientUnits="userSpaceOnUse">\n')
    a('      <stop offset="0" stop-color="%s"/>\n      <stop offset="0.45" stop-color="%s"/>\n'
      '      <stop offset="1" stop-color="%s"/>\n' % (a0, a1, a2))
    a('      <animateTransform attributeName="gradientTransform" type="translate" '
      'values="0 -120; 0 120; 0 -120" dur="9s" repeatCount="indefinite"/>\n')
    a("    </linearGradient>\n")
    a('<linearGradient id="panelGrad" x1="0" y1="0" x2="0" y2="1">'
      '<stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>\n'
      % (p0, p1))
    a('<filter id="glow8" x="-60%%" y="-60%%" width="220%%" height="220%%">'
      '<feGaussianBlur stdDeviation="8"/></filter>\n')
    a('<filter id="glow3" x="-60%%" y="-60%%" width="220%%" height="220%%">'
      '<feGaussianBlur stdDeviation="3"/></filter>\n')
    a('<filter id="txtGlow" x="-30%%" y="-30%%" width="160%%" height="160%%">'
      '<feGaussianBlur stdDeviation="0.9" result="b"/><feMerge>'
      '<feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>\n')
    a('<clipPath id="winClip"><rect x="2" y="2" width="1176" height="606" rx="18"/></clipPath>\n')
    a("</defs>\n")
    a('<rect x="2" y="2" width="1176" height="606" rx="18" fill="%s"/>\n' % t["bg"])
    a('<g clip-path="url(#winClip)">\n')
    a('<rect x="2" y="2" width="1176" height="606" fill="url(#panelGrad)"/>\n')
    a('<rect x="2" y="2" width="1176" height="46" fill="%s"/>\n' % t["titlebar"])
    a('<line x1="2" y1="48" x2="1178" y2="48" stroke="%s"/>\n' % t["chrome_line"])
    a('<circle cx="30" cy="25.0" r="5.5" fill="#ff5f56"/>\n'
      '<circle cx="50" cy="25.0" r="5.5" fill="#ffbd2e"/>\n'
      '<circle cx="70" cy="25.0" r="5.5" fill="#27c93f"/>\n')
    a('<text x="590.0" y="29.0" text-anchor="middle" font-size="12" fill="%s">%s</text>\n'
      % (t["title_fill"], TITLE))
    a('<text x="38" y="74" font-size="10" letter-spacing="3" fill="%s">VISUAL.MAP</text>\n'
      % t["visual_fill"])
    a('<rect x="36" y="84" width="400" height="492" rx="10" fill="none" stroke="%s" '
      'stroke-width="2" opacity="0.45" filter="url(#glow3)"/>\n' % t["frame_stroke"])
    a('<rect x="36" y="84" width="400" height="492" rx="10" fill="%s" stroke="%s"/>\n'
      % (t["frame_fill"], t["frame_stroke2"]))

    # portrait layer 1 — intro fade-in
    a('<g transform="translate(50,86) scale(1.2400,1.4471)" fill="%s" '
      'shape-rendering="crispEdges">\n' % t["port"])
    a('<set attributeName="opacity" to="0" begin="3.2s"/>\n')
    a(intro_groups(positions))
    a("</g>\n")

    # portrait layer 2 — drift bands on the loop
    a('<g transform="translate(50,86) scale(1.2400,1.4471)" fill="%s" '
      'shape-rendering="crispEdges" opacity="0">\n' % t["port"])
    a('<set attributeName="opacity" to="1" begin="3.2s"/>\n')
    a(drift_bands(positions, target, rng, pick_band_cell(positions, rng)))
    a("</g>\n")

    # logo layers — AWS / Azure / GCP / DevOps fade in on their loop slots
    a(logo_layers(logos_data, t["port"]))

    # corner brackets
    c = t["corner"]
    a('<path d="M 50 84 L 36 84 L 36 98" fill="none" stroke="%s" stroke-width="2" opacity="0.8"/>\n' % c)
    a('<path d="M 422 84 L 436 84 L 436 98" fill="none" stroke="%s" stroke-width="2" opacity="0.8"/>\n' % c)
    a('<path d="M 50 576 L 36 576 L 36 562" fill="none" stroke="%s" stroke-width="2" opacity="0.8"/>\n' % c)
    a('<path d="M 422 576 L 436 576 L 436 562" fill="none" stroke="%s" stroke-width="2" opacity="0.8"/>\n' % c)

    # SYSTEM.INFO panel
    a('<text x="470" y="106" font-size="13" letter-spacing="2" fill="%s" '
      'filter="url(#txtGlow)">SYSTEM.INFO</text>\n' % t["info"])
    a('<line x1="566" y1="102" x2="1061" y2="102" stroke="%s"/>\n' % t["chrome_line"])
    a('<text x="1125" y="106" text-anchor="end" font-size="12" fill="%s" font-weight="700">'
      '<tspan>&#9679;</tspan> LIVE<animate attributeName="opacity" values="1;0.25;1" '
      'dur="1.6s" repeatCount="indefinite"/></text>\n' % t["live"])
    a('<g opacity="0"><animate attributeName="opacity" from="0" to="1" dur="0.5s" '
      'begin="0.6s" fill="freeze"/>\n')
    a('<rect x="470" y="122" width="245" height="20" rx="4" fill="%s"/>\n' % t["pill"])
    a('<text x="479" y="136" font-size="14" font-weight="700" fill="%s">%s</text>\n'
      % (t["pill_txt"], PILL_EMAIL))
    a('<line x1="725" y1="130" x2="1125" y2="130" stroke="%s"/>\n' % t["chrome_line"])
    a("</g>\n")
    a(info_panel(t))

    a('<rect x="3" y="3" width="1174" height="604" rx="17" fill="none" stroke="url(#accent)" '
      'stroke-width="3" opacity="0.55" filter="url(#glow8)"/>\n')
    a('<rect x="2" y="2" width="1176" height="604" rx="17" fill="none" stroke="url(#accent)" '
      'stroke-width="1.6"/>\n')
    a("</g>\n</svg>\n")
    return "".join(s)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=DEFAULT_OUT)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    pd = np.load(os.path.join(DATA, "portrait.npz"))
    ld = np.load(os.path.join(DATA, "logos.npz"))
    out = os.path.abspath(args.outdir)
    os.makedirs(out, exist_ok=True)

    for theme in ("dark", "light"):
        rng = random.Random(args.seed)
        svg = build_theme(theme, pd["dots_dark" if theme == "dark" else "dots_light"], ld, rng)
        path = os.path.join(out, "%s.svg" % theme)
        with open(path, "w") as f:
            f.write(svg)
        print("%s: %d KB" % (theme, len(svg) // 1024))


if __name__ == "__main__":
    main()
