#!/usr/bin/env python3
"""Frames pixelizados -> gotinha3d.spr + gotinha3d.act, com o molde de timing do .act de referência.
Também gera sons próprios (sintetizados) para não depender dos sons do jogo de referência."""
import json, math, os, pickle, struct, wave
import numpy as np
import gotinha as G          # reaproveita write_spr / write_act
import pixelize as PX

AX, AY = 56, 78
molde = json.load(open('molde_referencia.json'))
frames = pickle.load(open('pix.pkl', 'rb'))
ACOES = ['idle', 'walk', 'attack', 'hurt', 'death']
DIRS = ['S', 'SW', 'W', 'NW', 'N', 'NE', 'E', 'SE']
SRC = {'S': ('S', 0), 'SW': ('SW', 0), 'W': ('W', 0), 'NW': ('NW', 0), 'N': ('N', 0),
       'NE': ('NW', 1), 'E': ('W', 1), 'SE': ('SW', 1)}   # RO: lado direito = esquerdo espelhado

# sons: mesmos frames do molde, nomes e arquivos nossos
SOM = {'poring_move.wav': 'gotinha_move.wav', 'poring_attack.wav': 'gotinha_attack.wav',
       'poring_damage.wav': 'gotinha_damage.wav', 'poring_die.wav': 'gotinha_die.wav', 'atk': 'atk'}
SOUNDS = ['atk', 'gotinha_move.wav', 'gotinha_attack.wav', 'gotinha_damage.wav', 'gotinha_die.wav']

images, cache = [], {}
def img_id(a):
    """recorta pelo bbox (largura par, centrada) e devolve (índice no SPR, offset x, offset y)."""
    ys, xs = np.where(a > 0)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    if (x1 - x0) % 2: x1 += 1
    if (y1 - y0) % 2: y1 += 1
    crop = np.zeros((y1 - y0, x1 - x0), np.uint8)
    sub = a[y0:min(y1, a.shape[0]), x0:min(x1, a.shape[1])]
    crop[:sub.shape[0], :sub.shape[1]] = sub
    key = crop.tobytes() + bytes(crop.shape)
    if key not in cache:
        cache[key] = len(images); images.append(crop)
    w, h = crop.shape[1], crop.shape[0]
    return cache[key], int(x0 + w // 2 - AX), int(y0 + h // 2 - AY)

acts, intervals = [], []
for g, acao in enumerate(ACOES):
    info = molde['acoes'][acao]
    snd = {k: SOUNDS.index(SOM[s]) for k, s in info['sons']}
    for d in DIRS:
        view, mirror = SRC[d]
        fr = []
        for k in range(info['frames']):
            sid, ox, oy = img_id(frames[f'{acao}_{view}_{k:02d}'])
            L = dict(x=-ox if mirror else ox, y=oy, spr=sid, mirror=mirror)
            if acao == 'death' and k >= info['frames'] - 4:     # poça some pela camada do ACT
                L['color'] = (255, 255, 255, [200, 150, 95, 40][k - (info['frames'] - 4)])
            f = dict(layers=[L])
            if k in snd: f['sound'] = snd[k]
            fr.append(f)
        acts.append(fr); intervals.append(info['intervalo'])

G.PAL = PX.PALETTE
os.makedirs('out', exist_ok=True)
G.write_spr('out/gotinha3d.spr', images)
G.write_act('out/gotinha3d.act', acts, SOUNDS, intervals)
print(f'{len(images)} imagens únicas, {len(acts)} ações')

# ---- sons sintetizados (48 kHz, determinísticos) ----
SR = 48000
def env(n, a=0.005, r=0.12):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / r)
def mix(*xs):
    n = max(len(x) for x in xs); out = np.zeros(n)
    for x in xs: out[:len(x)] += x
    return out
def save(name, x):
    x = x / (np.max(np.abs(x)) + 1e-9) * 0.7
    with wave.open(f'out/{name}', 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
rng = np.random.default_rng(3)
def blip(f0, f1, dur, r):
    n = int(SR * dur); t = np.arange(n) / SR
    f = np.linspace(f0, f1, n); ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * env(n, r=r)
def noise_burst(dur, r, lp=0.15):
    n = int(SR * dur); x = rng.standard_normal(n)
    y = np.zeros(n)
    for i in range(1, n): y[i] = y[i - 1] + lp * (x[i] - y[i - 1])
    return y * env(n, r=r)
save('gotinha_move.wav', blip(380, 620, 0.12, 0.04))                                  # "plip" do pulinho
save('gotinha_attack.wav', mix(blip(300, 900, 0.18, 0.06), 0.6 * noise_burst(0.25, 0.08)))  # bote + respingo
save('gotinha_damage.wav', blip(700, 260, 0.2, 0.07))                                   # "uh" descendo
save('gotinha_die.wav', mix(0.5 * blip(500, 120, 0.4, 0.15), noise_burst(0.6, 0.18, 0.25))) # estouro + chuva
print('sons:', sorted(f for f in os.listdir('out') if f.endswith('.wav')))
