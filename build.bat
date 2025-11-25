@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

echo =========================================
echo   Criando ambiente virtual...
echo =========================================
python -m venv venv
call venv\Scripts\activate

echo.
echo =========================================
echo   Atualizando pip
echo =========================================
python -m pip install --upgrade pip

echo.
echo =========================================
echo   Instalando dependencias LEVES
echo =========================================
pip install numpy matplotlib pandas pyinstaller

echo.
echo =========================================
echo   Instalando dependencias PESADAS (GDAL stack)
echo =========================================
REM ---- Usando wheels oficiais pré-compilados (não precisam compilar nada) ----

pip install https://download.lfd.uci.edu/pythonlibs/archived/GDAL-3.6.2-cp310-cp310-win_amd64.whl
pip install https://download.lfd.uci.edu/pythonlibs/archived/rasterio-1.3.9-cp310-cp310-win_amd64.whl
pip install https://download.lfd.uci.edu/pythonlibs/archived/Fiona-1.9.4-cp310-cp310-win_amd64.whl
pip install https://download.lfd.uci.edu/pythonlibs/archived/Shapely-2.0.2-cp310-cp310-win_amd64.whl

echo.
echo =========================================
echo   Instalando geopandas e skimage
echo =========================================
pip install geopandas scikit-image

echo.
echo =========================================
echo   Criando main.spec robusto...
echo =========================================

REM Apaga se já existir
del main.spec 2>nul

pyinstaller main.py ^
    --name GeoProcessApp ^
    --onefile ^
    --clean ^
    --collect-all rasterio ^
    --collect-all shapely ^
    --collect-all fiona ^
    --collect-all geopandas ^
    --collect-all skimage ^
    --add-data "%LOCALAPPDATA%\Programs\Python\Python310\Lib\site-packages\rasterio\gdal_data;gdal_data" ^
    --add-data "%LOCALAPPDATA%\Programs\Python\Python310\Lib\site-packages\rasterio\proj_data;proj_data"

echo.
echo =========================================
echo   Build finalizado!
echo   EXE gerado em: dist\GeoProcessApp.exe
echo =========================================

pause
