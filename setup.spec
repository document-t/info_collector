# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# 定义所有需要包含的文件和模块
a = Analysis(
    ['main.py'],  # 程序入口文件
    pathex=['.'],  # 项目根目录
    binaries=[],
    datas=[
        # 如果有UI资源文件，在此处添加
        # ('ui/*.png', 'ui'),
        # ('ui/*.ico', 'ui')
    ],
    hiddenimports=[
        'win32gui', 
        'win32process',
        'psutil',
        'cryptography.hazmat.backends',
        'cryptography.hazmat.backends.openssl'
    ],  # 显式声明可能被动态导入的模块
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 生成单个可执行文件
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='LocalInfoCollector',  # 生成的exe文件名
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # 启用压缩
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 调试阶段保留控制台窗口，发布时可改为False
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # 如果有图标，添加图标路径
    # icon='ui/icon.ico'
)
    