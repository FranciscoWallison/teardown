#!/usr/bin/env python3
"""Gotinha - monstro original (bolha d'agua) em pixel art, gerado por codigo.
Gera gotinha.spr + gotinha.act (formato Ragnarok Online, layout padrao de monstro: 40 acoes)
usando o mesmo timing do poring (frames/intervalos por acao).
"""
import struct, math, random
import numpy as np

# ---------------- paleta ----------------
PAL = [(255, 0, 255)] * 256            # 0 = transparente (magenta, convencao RO)
COLORS = {
    'outline': (22, 52, 120),
    'dark':    (40, 96, 190),
    'mid':     (66, 140, 230),
    'light':   (120, 190, 250),
    'pale':    (180, 228, 255),
    'white':   (245, 252, 255),
    'eye':     (14, 26, 58),
    'mouth':   (30, 60, 130),
    'blush':   (150, 170, 240),
}
IDX = {}
for i, (k, c) in enumerate(COLORS.items(), start=1):
    PAL[i] = c; IDX[k] = i

CW, CH = 96, 80          # canvas de cada frame
AX, AY = 48, 66          # ponto de chao dentro do canvas
R = 15                   # raio do corpo
H_TIP = 2.35 * R         # altura total ate a ponta

VIEWS = ['S', 'SW', 'W', 'NW', 'N']

# ---------------- desenho ----------------
def body_mask(sx, sy, lean):
    """mascara booleana do corpo em forma de gota. y para cima a partir do chao."""
    ys, xs = np.mgrid[0:CH, 0:CW]
    X = (xs - AX + 0.5) / sx
    Y = (AY - ys - 0.5) / sy                # altura acima do chao, sem escala
    X = X - lean * (np.clip(Y, 0, None) / H_TIP) ** 2 * 8
    circ = X ** 2 + (Y - R) ** 2 <= R ** 2
    t = np.clip((Y - R) / (H_TIP - R), 0, 1)
    tip = (Y >= R) & (Y <= H_TIP) & (np.abs(X) <= R * (1 - t) ** 1.6)
    # base levemente achatada (gota apoiada)
    return (circ | tip) & (Y >= 0.3), X, Y

def shade(mask, X, Y):
    img = np.zeros((CH, CW), np.uint8)
    nx = X / R
    ny = (Y - R) / R
    light = -0.55 * nx + 0.65 * ny
    img[mask] = IDX['mid']
    img[mask & (light > 0.15)] = IDX['light']
    img[mask & (light < -0.45)] = IDX['dark']
    # reflexo interno embaixo (refracao da agua)
    img[mask & (ny < -0.62) & (np.abs(nx) < 0.55)] = IDX['pale']
    # brilho especular
    hl = ((nx + 0.42) ** 2 / 0.025 + (ny - 0.38) ** 2 / 0.07) <= 1
    img[mask & hl] = IDX['white']
    hl2 = ((nx + 0.12) ** 2 / 0.004 + (ny - 0.72) ** 2 / 0.004) <= 1
    img[mask & hl2] = IDX['pale']
    # contorno
    m = mask
    edge = m & ~(np.roll(m, 1, 0) & np.roll(m, -1, 0) & np.roll(m, 1, 1) & np.roll(m, -1, 1))
    img[edge] = IDX['outline']
    return img

def put(img, x, y, c):
    x, y = int(round(x)), int(round(y))
    if 0 <= x < CW and 0 <= y < CH:
        img[y, x] = IDX[c]

def draw_face(img, view, sx, sy, lean, expr):
    if view in ('NW', 'N'):
        return
    cy = AY - R * sy * 0.95
    shift = {'S': 0, 'SW': -3, 'W': -6}[view]
    eyes = {'S': [-5, 5], 'SW': [-7, 2], 'W': [-9]}[view]
    lean_px = lean * (R * 0.95 / H_TIP) ** 2 * 8 * sx
    for ex in eyes:
        x0 = AX + ex * sx + lean_px - 0.5
        if expr == 'squint':           # olhos fechados > <
            d = 1 if ex < shift else -1
            put(img, x0 - d, cy - 2, 'eye'); put(img, x0, cy - 1, 'eye'); put(img, x0 - d, cy, 'eye')
        else:
            for dy in range(-2, 2):
                put(img, x0, cy + dy, 'eye'); put(img, x0 + 1, cy + dy, 'eye')
            put(img, x0 + 1, cy - 2, 'white')
    # boca
    mx = AX + shift * sx + lean_px - 0.5
    my = cy + 3
    if expr == 'open':
        for dx in (-1, 0, 1):
            put(img, mx + dx, my, 'mouth'); put(img, mx + dx, my + 1, 'mouth')
    elif expr == 'squint':
        put(img, mx - 1, my + 1, 'mouth'); put(img, mx, my, 'mouth'); put(img, mx + 1, my + 1, 'mouth')
    else:
        put(img, mx - 1, my, 'mouth'); put(img, mx, my + 1, 'mouth'); put(img, mx + 1, my, 'mouth')
    if view == 'S':
        put(img, AX - 8 * sx, cy + 2, 'blush'); put(img, AX + 8 * sx, cy + 2, 'blush')

def droplet(img, x, y, r):
    """gotinha pequena; x,y relativos ao ponto de chao (y para cima)."""
    cx, cy = AX + x, AY - y
    for yy in range(int(cy - r - 2), int(cy + r + 2)):
        for xx in range(int(cx - r - 2), int(cx + r + 2)):
            dx, dy = xx + 0.5 - cx, yy + 0.5 - cy
            inside = dx * dx + dy * dy <= r * r or (dy < 0 and dy > -r * 1.8 and abs(dx) <= r * (1 + dy / (r * 1.8)))
            if inside and 0 <= xx < CW and 0 <= yy < CH:
                img[yy, xx] = IDX['light'] if dx < 0 and dy < 0 else IDX['mid']
    # contorno
    m = img > 0
    ring = np.zeros_like(m)
    y0, y1 = max(0, int(cy - r - 3)), min(CH, int(cy + r + 3))
    x0, x1 = max(0, int(cx - r - 3)), min(CW, int(cx + r + 3))
    sub = m[y0:y1, x0:x1]
    e = sub & ~(np.roll(sub, 1, 0) & np.roll(sub, -1, 0) & np.roll(sub, 1, 1) & np.roll(sub, -1, 1))
    img[y0:y1, x0:x1][e & (img[y0:y1, x0:x1] != IDX['outline'])] = IDX['outline']
    put(img, cx - r * 0.3, cy - r * 0.3, 'white')

def puddle(img, w, h):
    ys, xs = np.mgrid[0:CH, 0:CW]
    X = (xs - AX + 0.5) / w; Y = (ys - AY + 0.5) / h
    m = X ** 2 + Y ** 2 <= 1
    img[m & (img == 0)] = IDX['mid']
    img[m & (Y < -0.2)] = IDX['light']
    img[m & ((X + 0.35) ** 2 * 6 + (Y + 0.3) ** 2 * 3 <= 0.25)] = IDX['white']
    edge = m & ~(np.roll(m, 1, 0) & np.roll(m, -1, 0) & np.roll(m, 1, 1) & np.roll(m, -1, 1))
    img[edge] = IDX['outline']

def body(view, sx=1.0, sy=1.0, lean=0.0, expr='normal', drops=()):
    m, X, Y = body_mask(sx, sy, lean)
    img = shade(m, X, Y)
    draw_face(img, view, sx, sy, lean, expr)
    for (x, y, r) in drops:
        droplet(img, x, y, r)
    return img

# ---------------- animacoes (por vista; lean>0 = inclina para a esquerda/frente na vista lateral) ----------------
FACING = {'S': 0, 'SW': 1, 'W': 1, 'NW': 1, 'N': 0}

def anim_idle(v):   # 4 frames
    return [(body(v, sx, sy), 0, 0) for sx, sy in [(1, 1), (1.03, .96), (1.06, .93), (1.03, .96)]]

def anim_walk(v):   # 10 frames, pulinho
    f = FACING[v]
    seq = [(1.08, .88, 0, 0), (1.14, .80, 0, 0), (.92, 1.12, .5, -3), (.90, 1.15, .6, -7), (.92, 1.10, .4, -9),
           (.95, 1.05, .2, -8), (.97, 1.02, 0, -5), (1.12, .84, -.2, -1), (1.16, .80, 0, 0), (1.04, .95, 0, 0)]
    return [(body(v, sx, sy, -l * f), 0, dy) for sx, sy, l, dy in seq]

def anim_attack(v):  # 28 frames: preparo, bote, splash, volta
    f = FACING[v]; out = []
    for k in range(8):                       # preparo (encolhe e inclina pra tras)
        t = (k + 1) / 8
        out.append((body(v, 1 + .2 * t, 1 - .22 * t, .6 * t * f, 'normal'), -2 * t, 0))
    for k, (sx, sy, l, lunge, dy) in enumerate([(.85, 1.2, -.8, 3, -4), (.82, 1.25, -1, 7, -8), (.85, 1.18, -.9, 11, -7), (.95, 1.0, -.5, 13, -3)]):
        out.append((body(v, sx, sy, l * f, 'open'), lunge, dy))
    splash = [(-12, 6, 2), (12, 6, 2), (-7, 14, 2), (8, 14, 2), (0, 20, 2)]
    for k in range(4):                       # impacto com respingos
        s = 1 + k * .35
        drops = [(x * s, y * (1 + k * .2) - k * k * .8, r) for x, y, r in splash]
        out.append((body(v, 1.3 - .05 * k, .72 + .05 * k, 0, 'open', drops), 13, 0))
    for k in range(6):                       # respingos caem, corpo se recompoe
        s = 2.4 + k * .3
        drops = [(x * s * .6, max(0, y * 1.8 - (k + 4) ** 2 * .9), r) for x, y, r in splash] if k < 4 else []
        out.append((body(v, 1.1 - .02 * k, .92 + .015 * k, 0, 'normal', drops), 13, 0))
    for k in range(6):                       # volta pulando para o lugar
        t = (k + 1) / 6
        out.append((body(v, .95, 1.06, .3 * f, 'normal'), 13 * (1 - t), -6 * math.sin(math.pi * t)))
    return out

def anim_hurt(v):   # 5 frames
    seq = [(1.18, .82, -3, 'squint'), (.9, 1.12, -2, 'squint'), (1.05, .95, -1, 'squint'), (.98, 1.03, 0, 'normal'), (1, 1, 0, 'normal')]
    return [(body(v, sx, sy, 0, e), back, 0) for sx, sy, back, e in seq]

def anim_death(v):  # 17 frames: estoura em respingos e vira poca que some
    out = [(body(v, .9, 1.15, 0, 'squint'), 0, 0), (body(v, 1.35, .6, 0, 'squint'), 0, 0)]
    rnd = random.Random(7)
    parts = [(math.cos(a) * rnd.uniform(1.3, 2.2), rnd.uniform(2.5, 4.0), rnd.choice([2, 2, 3])) for a in
             [math.radians(d) for d in (200, 230, 255, 285, 310, 340, 160, 20)]]
    for k in range(15):
        img = np.zeros((CH, CW), np.uint8)
        pw = min(26, 14 + k * 2.2)
        puddle(img, pw, 3.5 + min(k, 4) * .4)
        t = k + 1
        for vx, vy, r in parts:
            x = vx * t * 1.6
            y = vy * t - .32 * t * t
            if y > 0:
                droplet(img, x, y + 2, r)
            elif t < 14:
                puddle_small = (abs(x) < CW / 2 - 4)
                if puddle_small:
                    cx = int(AX + x)
                    for dx in range(-r, r + 1):
                        put(img, cx + dx, AY, 'mid')
                    put(img, cx - r - 1, AY, 'outline'); put(img, cx + r + 1, AY, 'outline')
        out.append((img, 0, 0))
    return out

ACTIONS = [anim_idle, anim_walk, anim_attack, anim_hurt, anim_death]
# timing herdado do poring (intervalo em unidades de ~24ms) e frame de som
INTERVAL = [4.0, 1.0, 1.0, 4.0, 1.0]
SOUND_AT = {1: (5, 1), 2: (11, 2), 3: (1, 3), 4: (1, 4)}
SOUNDS = ['atk', 'poring_move.wav', 'poring_attack.wav', 'poring_damage.wav', 'poring_die.wav']
DIRS = ['S', 'SW', 'W', 'NW', 'N', 'NE', 'E', 'SE']
DIR_VIEW = {'S': ('S', 0), 'SW': ('SW', 0), 'W': ('W', 0), 'NW': ('NW', 0), 'N': ('N', 0),
            'NE': ('NW', 1), 'E': ('W', 1), 'SE': ('SW', 1)}
DIR_VEC = {'S': (0, 1), 'SW': (-1, .5), 'W': (-1, 0), 'NW': (-1, -.5), 'N': (0, -1),
           'NE': (1, -.5), 'E': (1, 0), 'SE': (1, .5)}

# ---------------- escrita SPR / ACT ----------------
def rle(px):
    out = bytearray(); i = 0
    while i < len(px):
        if px[i] == 0:
            n = 0
            while i < len(px) and px[i] == 0 and n < 255:
                n += 1; i += 1
            out += bytes([0, n])
        else:
            out.append(px[i]); i += 1
    return bytes(out)

def write_spr(path, images):
    d = bytearray(b'SP' + bytes([1, 2]) + struct.pack('<HH', len(images), 0))
    for im in images:
        h, w = im.shape
        data = rle(im.tobytes())
        d += struct.pack('<HHH', w, h, len(data)) + data
    for r, g, b in PAL:
        d += bytes([r, g, b, 0])
    open(path, 'wb').write(d)

def write_act(path, actions, sounds, intervals):
    d = bytearray(b'AC' + bytes([5, 2]) + struct.pack('<H', len(actions)) + b'\x00' * 10)
    for frames in actions:
        d += struct.pack('<I', len(frames))
        for fr in frames:
            d += b'\x00' * 32 + struct.pack('<I', len(fr['layers']))
            for L in fr['layers']:
                d += struct.pack('<iiiI', L['x'], L['y'], L['spr'], L['mirror'])
                d += bytes(L.get('color', (255, 255, 255, 255)))
                d += struct.pack('<ffiiii', 1.0, 1.0, 0, 0, CW, CH)
            d += struct.pack('<ii', fr.get('sound', -1), 0)
    d += struct.pack('<i', len(sounds))
    for s in sounds:
        d += s.encode().ljust(40, b'\x00')
    d += struct.pack('<%df' % len(intervals), *intervals)
    open(path, 'wb').write(d)

def build(out_spr, out_act):
    images, cache = [], {}
    def img_id(img):
        key = img.tobytes()
        if key not in cache:
            cache[key] = len(images); images.append(img)
        return cache[key]
    per_view = {v: [fn(v) for fn in ACTIONS] for v in VIEWS}
    acts, intervals = [], []
    for g in range(5):
        for dname in DIRS:
            view, mirror = DIR_VIEW[dname]
            vx, vy = DIR_VEC[dname]
            frames = []
            for k, (img, fwd, dy) in enumerate(per_view[view][g]):
                L = dict(x=int(round(vx * fwd)), y=int(round(vy * fwd * .6 + dy)) - (AY - CH // 2),
                         spr=img_id(img), mirror=mirror)
                if g == 4 and k >= 13:   # fade da poca usando alpha da camada
                    L['color'] = (255, 255, 255, [200, 150, 95, 40][k - 13])
                fr = dict(layers=[L])
                if g in SOUND_AT and SOUND_AT[g][0] == k:
                    fr['sound'] = SOUND_AT[g][1]
                frames.append(fr)
            acts.append(frames); intervals.append(INTERVAL[g])
    write_spr(out_spr, images)
    write_act(out_act, acts, SOUNDS, intervals)
    print(f'{len(images)} imagens unicas, {len(acts)} acoes')

if __name__ == '__main__':
    import sys
    build(sys.argv[1] if len(sys.argv) > 1 else 'gotinha.spr', sys.argv[2] if len(sys.argv) > 2 else 'gotinha.act')
