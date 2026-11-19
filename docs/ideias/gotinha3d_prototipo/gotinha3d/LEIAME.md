# Protótipo: Gotinha 3D → pixel art (técnica do teardown)

Monstro original (Gotinha) modelado em three.js; a estrutura (frames, intervalos, frames de som)
vem do .act de referência, sem nenhum pixel dele.

## Pipeline
1. `molde_referencia.json`: frames, intervalos e sons por ação, extraídos do .act de referência.
2. `scene.html`: modelo 3D por código; `pose(ação, fase 0..1)` é a única fonte de pose; câmera do RO
   (FOV 15°, 50° de cima); luz presa à câmera (luz "pintada"); `render()` é função pura.
3. `capture.mjs`: Chromium headless chama `SIM.render` para 5 vistas × 64 frames (320 PNGs em 2×).
4. `pixelize.py`: 2×2 → 1 px por moda, faixas de luz fixas (shader grava o ângulo com a luz),
   paleta da Gotinha, limpeza de órfãos, contorno de 1 px.
5. `export.py`: `.spr` + `.act` (40 ações, NE/E/SE espelhados como no RO, fade da poça pela camada)
   e 4 sons sintetizados próprios.
6. `compare.py`: folha comparativa, WebP animado e métricas.

## Rodar no Windows
Precisa de **Node.js 20+** e **Python 3** instalados.

1. Dê dois cliques em `rodar.bat` (ou rode `rodar.bat` no terminal dentro desta pasta).
2. Ele instala as dependências, renderiza os frames, pixeliza, exporta e abre o visualizador.
3. Os resultados ficam em `out/`.

Para só **ver a animação ao vivo** (sem exportar):

    npm install
    python -m http.server 8765 --bind 127.0.0.1

e abra http://127.0.0.1:8765/viewer.html no navegador.
O `scene.html` não roda com `node`: é uma página para o navegador.

Para incluir a referência oficial na comparação, copie `poring.spr` e `poring.act` para esta pasta
(ou para `reference/`). Sem eles, a comparação mostra só a versão 2D e a 3D.
