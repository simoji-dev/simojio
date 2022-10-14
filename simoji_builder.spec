# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

added_files = [('./simoji/lib/gui/icon/*', 'simoji/lib/gui/icon')]

import sys
sys.modules['FixTk'] = None

a = Analysis(['./simoji/main.py'],
             pathex=['[ADD-PATH-TO-TOP_LEVEL-FOLDER]'],
             binaries=[],
             datas=added_files,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

a.datas += Tree('./simoji', prefix='simoji')

# -- add/remove stuff from TOC to reduce size --

# Manually remove entire packages...
a.binaries = [x for x in a.binaries if not x[0].startswith("IPython")]
a.binaries = [x for x in a.binaries if not x[0].startswith("zmq")]

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='simoji',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True)
