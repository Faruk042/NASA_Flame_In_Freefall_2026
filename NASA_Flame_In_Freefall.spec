# -*- mode: python ; coding: utf-8 -*-
import os
import sys
import glob
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

try:
    proje_kok = os.path.abspath(SPECPATH)
except NameError:
    proje_kok = os.path.abspath(os.path.dirname(__file__) if "__file__" in globals() else os.getcwd())

# 1. Birlikte paketlenecek veri ve doküman klasörleri
datas = []
for rel_item, dest in [
    ("veri", "veri"),
    ("docs", "docs"),
    ("KULLANIM_VE_OZELLIK_REHBERI.html", "."),
    ("KULLANIM_VE_OZELLIK_REHBERI.md", "."),
    ("README.md", "."),
    ("requirements.txt", "."),
]:
    full_p = os.path.join(proje_kok, rel_item)
    if os.path.exists(full_p):
        datas.append((full_p, dest))

# Dinamik yardımcı modüller
for py_file in glob.glob(os.path.join(proje_kok, "*.py")):
    datas.append((py_file, "."))

# CustomTkinter tema ve stil JSON dosyaları
datas += collect_data_files("customtkinter")

# 2. Gizli içe aktarmalar (Tüm NASA modülleri ve harici kütüphaneler)
hiddenimports = [
    "customtkinter",
    "darkdetect",
    "PIL",
    "PIL.Image",
    "PIL.ImageTk",
    "psutil",
    "requests",
    "urllib3",
    "ai_uzman_asistan",
    "mikroyercekimi_fizik_motoru",
    "nasa_ntrs_psi_veri_avcisi",
    "nasa_psi_veritabani",
    "ntrs_istemcisi",
    "optik_alev_goruntu_analizoru",
    "korpus_olusturucu",
    "literatur_ai",
    "veri_laboratuvari",
    "gorsel_uretici",
]
hiddenimports += collect_submodules("customtkinter")

a = Analysis(
    [os.path.join(proje_kok, "flame_in_freefall_app.py")],
    pathex=[proje_kok],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["unittest", "test", "tkinter.test"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="NASA_Flame_In_Freefall",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="NASA_Flame_In_Freefall",
)
