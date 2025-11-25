# build.spec

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('C:/Program Files/GDAL', 'gdal_data'),
        ('C:/Program Files/GDAL/gdalplugins', 'gdalplugins'),
    ],
    hiddenimports=[
        'rasterio._env',
        'rasterio._shim',
        'rasterio._drivers',
        'rasterio._features',
        'rasterio._io',
        'rasterio._warp'
    ],
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='MeuPrograma',
    console=False,
)
