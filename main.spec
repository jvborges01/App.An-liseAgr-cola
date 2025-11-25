# main.spec — robusto para Rasterio, GDAL, Shapely, GEOS, PROJ, Fiona, etc.

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# ───────────────────────────────────────────────
# Dependências especiais
# ───────────────────────────────────────────────
datas  = []
binaries = []
hiddenimports = []

# Rasterio / GDAL / Fiona / PROJ / GEOS
for pkg in ["rasterio", "fiona", "geopandas", "shapely", "pyproj"]:
    datas += collect_data_files(pkg)
    hiddenimports += collect_submodules(pkg)

# GDAL runtime libs (Windows)
gdal_data = os.environ.get("GDAL_DATA")
if gdal_data:
    datas.append((gdal_data, "gdal_data"))

proj_data = os.environ.get("PROJ_LIB")
if proj_data:
    datas.append((proj_data, "proj_data"))

# ───────────────────────────────────────────────
# Configuração do executável
# ───────────────────────────────────────────────
block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[os.getcwd()],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    noarchive=False,
    strip=False,
    upx=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='AnaliseAgricola',
    console=False
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='AnaliseAgricola'
)
