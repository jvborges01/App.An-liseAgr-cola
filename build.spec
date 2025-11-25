# -*- mode: python ; coding: utf-8 -*-

import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hidden_imports = []
hidden_imports += collect_submodules('rasterio')
hidden_imports += collect_submodules('fiona')
hidden_imports += collect_submodules('geopandas')
hidden_imports += collect_submodules('osgeo')
hidden_imports += collect_submodules('matplotlib')

datas = []
datas += collect_data_files('rasterio')
datas += collect_data_files('fiona')
datas += collect_data_files('geopandas')
datas += collect_data_files('matplotlib')
datas += collect_data_files('osgeo')

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
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
    a.zipfiles,
    a.datas,
    [],
    name="AnaliseAgricola",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
