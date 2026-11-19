#!/usr/bin/env python3
"""Comparação: referência oficial (só escala/timing) × Gotinha 2D (desenho por código) × Gotinha 3D→pixel.
Gera folha estática, WebP animado lado a lado e métricas de fluidez."""
import json
import numpy as np
from PIL import Image, ImageDraw
from ro_sprite import read_spr, read_act, render_frame, frame_bbox

import os
def _ref():
    # referência oficial é opcional: procure poring.spr/.act nesta pasta ou em reference/
    for base in ('.', 'reference'):
        for spr, act in (('poring.spr', 'poring.act'), ('b59617f9-poring.spr', 'ae5a9e55-poring.act')):
            if os.path.exists(os.path.join(base, spr)) and os.path.exists(os.path.join(base, act)):
                return os.path.join(base, spr), os.path.join(base, act)
    return None
SETS = []
if _ref():
    SETS.append(('Referência oficial\n(só escala e timing)', *_ref(), 'ref'))
else:
    print('aviso: poring.spr/.act não encontrados; comparação sem a referência oficial')
SETS += [('Gotinha 2D\n(desenho por código)', 'out/gotinha2d.spr', 'out/gotinha2d.act', '2d'),
         ('Gotinha 3D → pixel\n(este protótipo)', 'out/gotinha3d.spr', 'out/gotinha3d.act', '3d')]
GROUPS = ['idle', 'walk', 'attack', 'hurt', 'death']
DIR = 1  # SW
S = 3
CELL = (120, 110)
ORIGIN = (60, 88)
BG = (70, 90, 70, 255)

data = {}
for label, spr, act, key in SETS:
    v, imgs, rgba = read_spr(spr)
    av, acts, snd, iv = read_act(act)
    data[key] = (imgs, rgba, acts, iv)

def frame(key, g, k, d=DIR):
    imgs, rgba, acts, iv = data[key]
    a = acts[g * 8 + d]
    return render_frame(a[k % len(a)], imgs, rgba, CELL, ORIGIN)

# ---------- folha estática: frames-chave da direção SW ----------
KEYS = {'idle': [0, 2], 'walk': [0, 3, 5, 8], 'attack': [4, 9, 12, 16, 22], 'hurt': [0, 1, 3], 'death': [0, 2, 5, 10]}
cols = sum(len(v) for v in KEYS.values())
W, H = CELL[0] * S, CELL[1] * S
LBL = 150
sheet = Image.new('RGBA', (LBL + cols * W, 40 + len(SETS) * H), (38, 42, 48, 255))
dr = ImageDraw.Draw(sheet)
c = 0
for g, name in enumerate(GROUPS):
    for k in KEYS[name]:
        dr.text((LBL + c * W + 8, 12), f'{name} f{k}', fill=(230, 230, 230))
        for r, (label, _, _, key) in enumerate(SETS):
            cell = Image.new('RGBA', CELL, BG)
            cell.alpha_composite(frame(key, g, k))
            sheet.paste(cell.resize((W, H), Image.NEAREST), (LBL + c * W, 40 + r * H))
        c += 1
for r, (label, _, _, _) in enumerate(SETS):
    dr.multiline_text((8, 40 + r * H + H // 2 - 14), label, fill=(230, 230, 230))
sheet.save('out/comparacao_frames.png')

# ---------- WebP animado: as 5 ações lado a lado, 3 linhas ----------
SA = 2
CW, CH = CELL[0] * SA, CELL[1] * SA
out = []
for t in range(0, 2400, 24):
    canvas = Image.new('RGBA', (LBL + 5 * CW, 30 + 3 * CH), (38, 42, 48, 255))
    d2 = ImageDraw.Draw(canvas)
    for g, name in enumerate(GROUPS):
        d2.text((LBL + g * CW + 8, 8), name, fill=(230, 230, 230))
    for r, (label, _, _, key) in enumerate(SETS):
        d2.multiline_text((8, 30 + r * CH + CH // 2 - 14), label, fill=(230, 230, 230))
        imgs, rgba, acts, iv = data[key]
        for g in range(5):
            a = acts[g * 8 + DIR]
            ms = iv[g * 8 + DIR] * 24
            k = int(t // ms)
            k = min(k, len(a) - 1) if g == 4 else k % len(a)
            cell = Image.new('RGBA', CELL, BG)
            cell.alpha_composite(render_frame(a[k], imgs, rgba, CELL, ORIGIN))
            canvas.paste(cell.resize((CW, CH), Image.NEAREST), (LBL + g * CW, 30 + r * CH))
    out.append(canvas.convert('RGB'))
out[0].save('out/comparacao_animada.webp', save_all=True, append_images=out[1:], duration=24, loop=0, quality=92)

# ---------- 8 direções do 3D ----------
DIRS = ['S', 'SW', 'W', 'NW', 'N', 'NE', 'E', 'SE']
d8 = Image.new('RGBA', (8 * W, H + 30), (38, 42, 48, 255))
d3 = ImageDraw.Draw(d8)
for i, dn in enumerate(DIRS):
    for key in ['3d']:
        cell = Image.new('RGBA', CELL, BG); cell.alpha_composite(frame(key, 0, 0, i))
        d8.paste(cell.resize((W, H), Image.NEAREST), (i * W, 30))
    d3.text((i * W + 8, 8), dn + (' (espelho)' if dn in ('NE', 'E', 'SE') else ''), fill=(230, 230, 230))
d8.save('out/gotinha3d_8direcoes.png')

# ---------- métricas ----------
def alpha(im):
    return np.array(im)[..., 3] > 0
metrics = {}
for label, _, _, key in SETS:
    imgs, rgba, acts, iv = data[key]
    m = {}
    for g, name in enumerate(GROUPS[:4]):
        a = acts[g * 8 + DIR]
        areas, bases, cxs = [], [], []
        for f in a:
            al = alpha(render_frame(f, imgs, rgba, CELL, ORIGIN))
            ys, xs = np.where(al)
            areas.append(int(al.sum())); bases.append(int(ys.max())); cxs.append(float(xs.mean()))
        jumps = [abs(areas[i] - areas[i - 1]) / max(areas[i - 1], 1) for i in range(1, len(areas))]
        m[name] = dict(area_min=min(areas), area_max=max(areas),
                       maior_salto_area_pct=round(100 * max(jumps), 1),
                       salto_medio_area_pct=round(100 * sum(jumps) / len(jumps), 1))
        if name in ('idle', 'hurt'):
            m[name]['variacao_base_px'] = max(bases) - min(bases)
    m['imagens_unicas_no_spr'] = len(imgs)
    metrics[key] = m
json.dump(metrics, open('out/metricas.json', 'w'), indent=1, ensure_ascii=False)
print(json.dumps(metrics, indent=1, ensure_ascii=False))
