#!/usr/bin/env python3
"""Ragnarok Online .spr/.act -> GIFs + sprite sheets.

Uso: python3 ro_sprite.py arquivo.spr arquivo.act pasta_saida [--scale 2]
"""
import struct, sys, os, json, argparse
from PIL import Image

# ---------- SPR ----------
def read_spr(path):
    d = open(path, 'rb').read()
    assert d[:2] == b'SP', 'nao e SPR'
    minor, major = d[2], d[3]
    ver = major + minor / 10
    off = 4
    n_idx, = struct.unpack_from('<H', d, off); off += 2
    n_rgba = 0
    if ver >= 2.0:
        n_rgba, = struct.unpack_from('<H', d, off); off += 2
    pal = d[-1024:]
    palette = [(pal[i*4], pal[i*4+1], pal[i*4+2]) for i in range(256)]
    imgs = []
    for _ in range(n_idx):
        w, h = struct.unpack_from('<HH', d, off); off += 4
        if ver >= 2.1:
            size, = struct.unpack_from('<H', d, off); off += 2
            raw = d[off:off+size]; off += size
            px = bytearray(); i = 0
            while i < len(raw):
                b = raw[i]; i += 1
                if b == 0:
                    cnt = raw[i]; i += 1
                    px += b'\x00' * (cnt if cnt else 1)
                else:
                    px.append(b)
            px = px[:w*h]
        else:
            px = d[off:off+w*h]; off += w*h
        im = Image.new('RGBA', (w, h))
        im.putdata([(0, 0, 0, 0) if p == 0 else palette[p] + (255,) for p in px])
        imgs.append(im)
    rgba = []
    for _ in range(n_rgba):
        w, h = struct.unpack_from('<HH', d, off); off += 4
        raw = d[off:off+w*h*4]; off += w*h*4
        im = Image.frombytes('RGBA', (w, h), raw, 'raw', 'ABGR').transpose(Image.FLIP_TOP_BOTTOM)
        rgba.append(im)
    return ver, imgs, rgba

# ---------- ACT ----------
def read_act(path):
    d = open(path, 'rb').read()
    assert d[:2] == b'AC', 'nao e ACT'
    minor, major = d[2], d[3]
    ver = major + minor / 10
    n_act, = struct.unpack_from('<H', d, 4)
    off = 16
    actions = []
    for _ in range(n_act):
        n_fr, = struct.unpack_from('<I', d, off); off += 4
        frames = []
        for _ in range(n_fr):
            off += 32
            n_ly, = struct.unpack_from('<I', d, off); off += 4
            layers = []
            for _ in range(n_ly):
                x, y, spr, mirror = struct.unpack_from('<iiiI', d, off); off += 16
                L = dict(x=x, y=y, spr=spr, mirror=mirror, color=(255,)*4, sx=1.0, sy=1.0, rot=0, type=0)
                if ver >= 2.0:
                    L['color'] = tuple(d[off:off+4]); off += 4
                    L['sx'], = struct.unpack_from('<f', d, off); off += 4
                    L['sy'] = L['sx']
                    if ver >= 2.4:
                        L['sy'], = struct.unpack_from('<f', d, off); off += 4
                    L['rot'], L['type'] = struct.unpack_from('<ii', d, off); off += 8
                    if ver >= 2.5:
                        off += 8
                layers.append(L)
            sound = -1
            if ver >= 2.0:
                sound, = struct.unpack_from('<i', d, off); off += 4
            if ver >= 2.3:
                n_anc, = struct.unpack_from('<i', d, off); off += 4
                off += 16 * n_anc
            frames.append(dict(layers=layers, sound=sound))
        actions.append(frames)
    sounds = []
    if ver >= 2.1 and off < len(d):
        n_snd, = struct.unpack_from('<i', d, off); off += 4
        for _ in range(n_snd):
            sounds.append(d[off:off+40].split(b'\x00')[0].decode('latin1')); off += 40
    intervals = [4.0] * n_act
    if ver >= 2.2 and off + 4 * n_act <= len(d):
        intervals = list(struct.unpack_from('<%df' % n_act, d, off))
    return ver, actions, sounds, intervals

# ---------- render ----------
def layer_image(L, imgs, rgba):
    if L['spr'] < 0:
        return None
    src = imgs if L['type'] == 0 else rgba
    if L['spr'] >= len(src):
        return None
    im = src[L['spr']]
    if L['mirror']:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    w, h = im.size
    nw, nh = max(1, round(w * abs(L['sx']))), max(1, round(h * abs(L['sy'])))
    if (nw, nh) != (w, h):
        im = im.resize((nw, nh), Image.NEAREST)
    r, g, b, a = L['color']
    if (r, g, b, a) != (255, 255, 255, 255):
        ch = im.split()
        im = Image.merge('RGBA', [c.point(lambda v, k=k: v * k // 255) for c, k in zip(ch, (r, g, b, a))])
    if L['rot']:
        im = im.rotate(-L['rot'], expand=True, resample=Image.NEAREST)
    return im

def frame_bbox(frame, imgs, rgba):
    box = None
    for L in frame['layers']:
        im = layer_image(L, imgs, rgba)
        if im is None:
            continue
        w, h = im.size
        x0, y0 = L['x'] - w // 2, L['y'] - h // 2
        b = (x0, y0, x0 + w, y0 + h)
        box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
    return box

def render_frame(frame, imgs, rgba, canvas, origin):
    out = Image.new('RGBA', canvas, (0, 0, 0, 0))
    for L in frame['layers']:
        im = layer_image(L, imgs, rgba)
        if im is None:
            continue
        w, h = im.size
        out.alpha_composite(im, (origin[0] + L['x'] - w // 2, origin[1] + L['y'] - h // 2))
    return out

MONSTER_GROUPS = ['idle', 'walk', 'attack', 'hurt', 'death']
DIRS = ['S', 'SW', 'W', 'NW', 'N', 'NE', 'E', 'SE']

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spr'); ap.add_argument('act'); ap.add_argument('out')
    ap.add_argument('--scale', type=int, default=2)
    ap.add_argument('--name', default=None)
    a = ap.parse_args()
    name = a.name or os.path.splitext(os.path.basename(a.spr))[0]
    os.makedirs(a.out, exist_ok=True)
    sver, imgs, rgba = read_spr(a.spr)
    aver, actions, sounds, intervals = read_act(a.act)
    print(f'SPR v{sver}: {len(imgs)} indexadas, {len(rgba)} RGBA | ACT v{aver}: {len(actions)} acoes')

    # canvas comum a todas as acoes -> mesmo ponto de chao em tudo
    box = None
    for act in actions:
        for f in act:
            b = frame_bbox(f, imgs, rgba)
            if b:
                box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
    pad = 2
    W, H = box[2] - box[0] + pad * 2, box[3] - box[1] + pad * 2
    origin = (-box[0] + pad, -box[1] + pad)
    S = a.scale
    meta = dict(name=name, frame_w=W * S, frame_h=H * S, origin_x=origin[0] * S, origin_y=origin[1] * S,
                scale=S, actions=[])

    is_monster = len(actions) == 40
    for i, act in enumerate(actions):
        if is_monster:
            label = f'{MONSTER_GROUPS[i // 8]}_{DIRS[i % 8]}'
        else:
            label = f'action{i:02d}_{DIRS[i % 8]}'
        frames = [render_frame(f, imgs, rgba, (W, H), origin).resize((W * S, H * S), Image.NEAREST) for f in act]
        if not frames:
            continue
        ms = max(20, round(intervals[i] * 24))  # RO: intervalo * 24ms
        # sprite sheet horizontal
        sheet = Image.new('RGBA', (W * S * len(frames), H * S))
        for k, fr in enumerate(frames):
            sheet.paste(fr, (k * W * S, 0))
        sheet.save(os.path.join(a.out, f'{name}_{label}.png'))
        # GIF com fundo transparente
        loop = 1 if label.startswith('death') else 0
        frames[0].save(os.path.join(a.out, f'{name}_{label}.gif'), save_all=True, append_images=frames[1:],
                       duration=ms, loop=0, disposal=2, transparency=0)
        meta['actions'].append(dict(id=i, name=label, frames=len(frames), frame_ms=ms, loops=not label.startswith('death'),
                                    sheet=f'{name}_{label}.png'))
    json.dump(meta, open(os.path.join(a.out, f'{name}_meta.json'), 'w'), indent=2)
    return meta, (W * S, H * S)

if __name__ == '__main__':
    main()
