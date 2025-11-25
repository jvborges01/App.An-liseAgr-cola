# main.spec — robusto para GDAL, Rasterio, Fiona, Shapely, Geopandas
# Funciona no GitHub Actions com Windows

import os
from PyInstaller.utils.hooks import collect_all

# Bibliotecas com dados extras
datas = []
binaries = []
hiddenimports = []

for pkg in ["rasterio", "fiona", "shapely", "pyproj", "geopandas"]:
    collected = collect_all(pkg)
    datas += collected["datas"]
    binaries += collected["binaries"]
    hiddenimports += collected["hiddenimports"]

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='MeuPrograma',
    debug=False,
    strip=False,
    upx=False
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    a.zipfiles,
    strip=False,
    upx=False,
    name='build'
)
