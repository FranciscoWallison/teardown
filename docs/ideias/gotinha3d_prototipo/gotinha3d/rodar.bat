@echo off
setlocal
cd /d "%~dp0"
echo [1/6] Instalando dependencias Node (three.js e Playwright)...
call npm install || goto :erro
call npx playwright install chromium || goto :erro
echo [2/6] Instalando dependencias Python (numpy e Pillow)...
python -m pip install -r requirements.txt || goto :erro
echo [3/6] Subindo servidor local em http://127.0.0.1:8765 ...
start "servidor-gotinha" /min python -m http.server 8765 --bind 127.0.0.1
timeout /t 2 /nobreak >nul
echo [4/6] Renderizando os frames 3D...
node capture.mjs || goto :erro
echo [5/6] Pixelizando e exportando .spr/.act...
python run_pixelize.py || goto :erro
python export.py || goto :erro
python gotinha2d.py out\gotinha2d.spr out\gotinha2d.act || goto :erro
echo [6/6] Gerando comparacao...
python compare.py || goto :erro
echo.
echo Pronto. Resultados na pasta "out". Visualizador: http://127.0.0.1:8765/viewer.html
start "" http://127.0.0.1:8765/viewer.html
goto :fim
:erro
echo.
echo Algo falhou no passo acima. Copie a mensagem de erro e me mande.
:fim
pause
