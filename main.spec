# main.spec — robusto para Rasterio, GDAL, Shapely, GeoPandas

# IMPORTANTE:
# Rode sempre com:
#   pyinstaller main.spec

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Coleta automática de datas/libs importantes
datas  = collect_data_files("rasterio")
datas += collect_data_files("fiona")
datas += collect_data_files("geopandas")
datas += collect_data_files("shapely")
datas += collect_data_files("pyproj")

# Alguns pacotes precisam que módulos internos sejam incluídos
hiddenimports  = collect_submodules("rasterio")
hiddenimports += collect_submodules("fiona")
hiddenimports += collect_submodules("geopandas")
hiddenimports += collect_submodules("shapely")
hiddenimports += collect_submodules("pyproj")

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AnaliseAgricola',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,    # troque para False se NÃO quiser console
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='AnaliseAgricola'
)
