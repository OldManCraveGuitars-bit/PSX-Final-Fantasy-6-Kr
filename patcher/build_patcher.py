"""Build with Python 3.13 and PyInstaller 6.22.3 on Windows x64."""
from pathlib import Path
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
manifest = json.loads((HERE / 'resources/manifest.json').read_text('utf-8'))
resources = ['manifest.json', manifest['patch']['name'], manifest['decoder']['name']]
resource_args = [arg for name in resources
                 for arg in ('--add-data', str(HERE / 'resources' / name) + ';resources')]
subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
    '--onefile', '--windowed', '--name', 'FF6-KR-Patcher-V0.77',
    '--distpath', str(HERE.parent / 'dist'), '--workpath', str(HERE.parent / '.build/patcher'),
    '--specpath', str(HERE.parent / '.build'),
    *resource_args, str(HERE / 'patcher.py')], check=True)
