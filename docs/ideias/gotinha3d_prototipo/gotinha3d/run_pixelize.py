"""Passo 4: frames3d/*.png -> pix.pkl (pixel art indexada)."""
import pickle
import pixelize
res, _ = pixelize.process('frames3d')
pickle.dump(res, open('pix.pkl', 'wb'))
print('frames pixelizados:', len(res))
