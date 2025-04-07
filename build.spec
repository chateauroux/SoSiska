# build.spec
block_cipher = None

a = Analysis(
    ['SoSiska.py'],
    binaries=[],
    datas=[
        ('C:/Python39/Lib/site-packages/PIL/', 'PIL')  # Путь к Pillow
    ],
    hiddenimports=[
        'PIL._tkinter_finder',
        'tkinter',
        'PIL.Image',
        'PIL.ImageTk'
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='SoSiska v0.2a',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Убрать консоль
    icon='SoSiska.ico'  # Иконка приложения (опционально)
)