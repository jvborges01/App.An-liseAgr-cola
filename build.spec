# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'rasterio',
        'rasterio._shim',
        'rasterio._base',
        'rasterio._io',
        'rasterio.sample',
        'rasterio.transform',
        'rasterio.crs',
        'fiona',
        'fiona._shim',
        'fiona.ogrext',
        'matplotlib.backends.backend_tkagg',
    ],
)

# Coleta COMPLETA de libs GIS
a.datas += collect_data_files('rasterio')
a.binaries += collect_dynamic_libs('rasterio')

a.datas += collect_data_files('fiona')
a.binaries += collect_dynamic_libs('fiona')

a.datas += collect_data_files('matplotlib')

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='AnaliseAgricola',
    debug=False,
    strip=False,
    upx=False,
    console=False,
)
