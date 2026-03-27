# dictly.spec - PyInstaller build configuration
# Run: pyinstaller dictly.spec

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None
ROOT = Path.cwd()
ASSETS_DIR = ROOT / "assets"
ICON_ICO = ASSETS_DIR / "icon.ico"
ICON_ICNS = ASSETS_DIR / "icon.icns"

datas = collect_data_files("customtkinter")
if ASSETS_DIR.exists():
    for asset in ASSETS_DIR.iterdir():
        if asset.is_file():
            datas.append((str(asset), "assets"))

hiddenimports = sorted(
    set(
        [
            "customtkinter",
            "faster_whisper",
            "sounddevice",
            "pyperclip",
            "pynput",
            "pystray",
            "PIL",
            "PIL.Image",
            "PIL.ImageDraw",
            "numpy",
            "ctranslate2",
            "tokenizers",
            "huggingface_hub",
        ]
        + collect_submodules("customtkinter")
    )
)

a = Analysis(
    ["main.py"],
    pathex=[str(ROOT)],
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
    [],
    exclude_binaries=True,
    name="Dictly",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON_ICO) if ICON_ICO.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Dictly",
)

app = BUNDLE(
    coll,
    name="Dictly.app",
    icon=str(ICON_ICNS) if ICON_ICNS.exists() else None,
    bundle_identifier="com.dictly.app",
    info_plist={
        "NSMicrophoneUsageDescription": "Dictly needs microphone access for dictation.",
        "NSAppleEventsUsageDescription": "Dictly uses AppleScript to paste text.",
        "LSUIElement": True,
    },
)
