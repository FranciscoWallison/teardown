#!/usr/bin/env python3
"""Render 3D (2x) -> pixel art na paleta da Gotinha.

1. Reduz 2x2 -> 1 px por moda (a cor mais frequente entre os pixels opacos).
2. Remapeia o corpo por faixa de luminância (dark/mid/light) e as cores chapadas
   (olho, boca, brilho, bochecha) pela cor mais próxima da paleta.
3. Contorno de 1 px (selout simples: tom mais escuro da rampa) e limpeza de pixels órfãos.
Saída: frames indexados (numpy uint8) prontos para o SPR.
"""
import glob, os, sys
import numpy as np
from PIL import Image

PAL_COLORS = {
    'outline': (22, 52, 120), 'dark': (40, 96, 190), 'mid': (66, 140, 230),
    'light': (120, 190, 250), 'pale': (180, 228, 255), 'white': (245, 252, 255),
    'eye': (14, 26, 58), 'mouth': (30, 60, 130), 'blush': (150, 170, 240),
}
NAMES = list(PAL_COLORS)
IDX = {k: i + 1 for i, k in enumerate(NAMES)}
PALETTE = [(255, 0, 255)] + [PAL_COLORS[k] for k in NAMES] + [(255, 0, 255)] * (255 - len(NAMES))
FLAT = {  # cores chapadas renderizadas como MeshBasic (valor exato do three.js, em sRGB)
    'eye': (14, 26, 58), 'white': (245, 252, 255), 'mouth': (30, 60, 130), 'blush': (150, 170, 240),
}


def downsample_mode(rgba, ss=2):
    h, w = rgba.shape[0] // ss, rgba.shape[1] // ss
    out = np.zeros((h, w, 4), np.uint8)
    blocks = rgba[:h * ss, :w * ss].reshape(h, ss, w, ss, 4).transpose(0, 2, 1, 3, 4).reshape(h, w, ss * ss, 4)
    for y in range(h):
        for x in range(w):
            px = blocks[y, x]
            op = px[px[:, 3] > 127]
            if len(op) * 2 < ss * ss:  # menos da metade opaca -> transparente
                continue
            vals, counts = np.unique(op[:, :3], axis=0, return_counts=True)
            out[y, x, :3] = vals[np.argmax(counts)]
            out[y, x, 3] = 255
    return out


# limiares sobre d = dot(normal, luz)*0.5+0.5 (gravado em cinza pelo shader do corpo)
BANDS = [(0.50, 'dark'), (0.74, 'mid'), (0.93, 'light'), (1.01, 'pale')]


def classify(rgb):
    """devolve nome da paleta para uma cor renderizada"""
    r, g, b = [int(v) for v in rgb]
    if abs(r - g) <= 2 and abs(g - b) <= 2:   # cinza = corpo (shader de luz)
        d = r / 255
        for lim, name in BANDS:
            if d < lim:
                return name
    best, bd = None, 1e9
    for k, c in FLAT.items():
        d = sum((a - b2) ** 2 for a, b2 in zip((r, g, b), c))
        if d < bd:
            best, bd = k, d
    if bd < 30 ** 2:
        return best
    return None  # corpo (toon) -> decide por luminância


def to_indexed(rgba, body_levels):
    h, w = rgba.shape[:2]
    out = np.zeros((h, w), np.uint8)
    lum = (0.299 * rgba[..., 0] + 0.587 * rgba[..., 1] + 0.114 * rgba[..., 2])
    for y in range(h):
        for x in range(w):
            if rgba[y, x, 3] == 0:
                continue
            k = classify(rgba[y, x, :3]) or 'mid'
            out[y, x] = IDX[k]
    return out


def clean_orphans(img):
    """pixel cercado (4-vizinhos) por uma única outra cor assume essa cor (só no corpo)."""
    body = {IDX['dark'], IDX['mid'], IDX['light'], IDX['pale']}
    out = img.copy()
    h, w = img.shape
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            c = img[y, x]
            if c not in body:
                continue
            n = [img[y - 1, x], img[y + 1, x], img[y, x - 1], img[y, x + 1]]
            if all(v == n[0] for v in n) and n[0] != c and n[0] in body:
                out[y, x] = n[0]
    return out


def outline(img):
    m = img > 0
    pad = np.pad(m, 1)
    inner = pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:]
    edge = m & ~inner
    out = img.copy()
    out[edge] = IDX['outline']
    return out


def body_levels(all_rgba):
    """limiares de luminância a partir dos tons que o toon realmente produziu no corpo"""
    lums = []
    for rgba in all_rgba:
        op = rgba[rgba[..., 3] > 0]
        for c in np.unique(op[:, :3], axis=0):
            if classify(c) is None:
                lums.append(0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2])
    u = sorted(set(round(l) for l in lums))
    # agrupa os tons do toon (saltos > 4) e põe os limiares entre os grupos:
    # 3 grupos -> dark/mid/light ; 4 grupos -> dark/mid/light/pale
    groups = [[u[0]]]
    for v in u[1:]:
        (groups[-1].append(v) if v - groups[-1][-1] <= 4 else groups.append([v]))
    cuts = [(groups[i][-1] + groups[i + 1][0]) / 2 for i in range(len(groups) - 1)][:3]
    while len(cuts) < 3:
        cuts.append(1e9)
    return tuple(cuts)


def process(frames_dir):
    files = sorted(glob.glob(os.path.join(frames_dir, '*.png')))
    rgbas = {f: downsample_mode(np.array(Image.open(f).convert('RGBA'))) for f in files}
    lv = BANDS
    res = {}
    for f, rgba in rgbas.items():
        idx = to_indexed(rgba, lv)
        idx = clean_orphans(idx)
        idx = outline(idx)
        res[os.path.basename(f)[:-4]] = idx
    return res, lv


if __name__ == '__main__':
    res, lv = process(sys.argv[1] if len(sys.argv) > 1 else 'frames3d')
    print('limiares de luz:', lv, 'frames:', len(res))
