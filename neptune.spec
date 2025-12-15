# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for Neptune CLI."""

from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

block_cipher = None

# Collect all data and submodules for packages with dynamic imports
datas = []
binaries = []
hiddenimports = []

# Packages that need full collection due to dynamic imports
packages_to_collect = [
    # Core
    'neptune_mcp',
    'pydantic',
    'pydantic_settings',
    'pydantic_core',
    'fastmcp',
    'neptune_common',
    'loguru',
    'click',
    'platformdirs',
    'requests',
    'certifi',
    'anyio',
    'starlette',
    'uvicorn',
    'httpx',
    'httpcore',
    'sse_starlette',
    'mcp',
    # fastmcp dependencies
    'authlib',
    'cyclopts',
    'exceptiongroup',
    'jsonschema_path',
    'openapi_pydantic',
    'pyperclip',
    'dotenv',
    'rich',
    'websockets',
    # py-key-value-aio dependencies
    'key_value',
    'beartype',
    'diskcache',
    'pathvalidate',
    'cachetools',
    'keyring',
    'jaraco',
    'jeepney',
    'secretstorage',
    # requests dependencies
    'urllib3',
    'charset_normalizer',
    'idna',
]

for package in packages_to_collect:
    try:
        pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(package)
        datas += pkg_datas
        binaries += pkg_binaries
        hiddenimports += pkg_hiddenimports
    except Exception:
        pass

# Add the mcp_instructions.md data file
datas += [('src/neptune_mcp/mcp_instructions.md', 'neptune_mcp')]

# Ensure diskcache submodules are collected
hiddenimports += collect_submodules('diskcache')

# Additional hidden imports for stdlib modules used dynamically
hiddenimports += [
    'webbrowser',
    'subprocess',
    'urllib.parse',
    'http.server',
    'json',
    'typing_extensions',
    'annotated_types',
    'email.mime.text',
    'pickletools',
    'pickle',
    'struct',
    'codecs',
    'io',
    'sqlite3',
    'difflib',
    # encodings and string handling
    'stringprep',
    'encodings.idna',
    'idna',
    # requests/urllib3 dependencies
    'urllib3',
    'urllib3.util',
    'urllib3.util.ssl_',
    'urllib3.contrib',
    'charset_normalizer',
    'chardet',
    'socks',
    'sockshandler',
]

a = Analysis(
    ['src/neptune_mcp/cli.py'],
    pathex=['src'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['runtime_hook.py'],
    excludes=[
        'authlib.integrations.sqla_oauth2',  # Requires sqlalchemy which we don't need
    ],
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
    name='neptune',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
