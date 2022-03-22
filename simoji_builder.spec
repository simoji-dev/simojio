# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

added_files = [('./simoji/lib/gui/icon/*', 'simoji/lib/gui/icon')]

import sys
sys.modules['FixTk'] = None

a = Analysis(['./simoji/main.py'],
             pathex=['[ADD-PATH-TO-TOP_LEVEL-FOLDER]'],
             binaries=[],
             datas=added_files,
             hiddenimports=['scipy.special.cython_special', 'tmm'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
#             excludes=['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

#a.datas += Tree('./lib', prefix='lib')
#a.datas += Tree('./modules', prefix='modules')
a.datas += Tree('./simoji', prefix='simoji')

# -- add/remove stuff from TOC to reduce size --

# Manually remove entire packages...
a.binaries = [x for x in a.binaries if not x[0].startswith("IPython")]
a.binaries = [x for x in a.binaries if not x[0].startswith("zmq")]

## Target remove specific ones...
#a.binaries = a.binaries - TOC([
# ('sqlite3.dll', None, None),
# ('tcl85.dll', None, None),
# ('tk85.dll', None, None),
# ('_sqlite3', None, None),
## ('_ssl', None, None),     # need to import _ssl package in runtime
# ('_tkinter', None, None)])

# Add a single missing dll...
# a.binaries = a.binaries + [
#  ('opencv_ffmpeg245_64.dll', 'C:\\Python27\\opencv_ffmpeg245_64.dll', 'BINARY')]

# Delete everything bar matplotlib data...
# a.datas = [x for x in a.datas if
#  os.path.dirname(x[1]).startswith("C:\\Python27\\Lib\\site-packages\\matplotlib")]

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
