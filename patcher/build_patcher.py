"""Build with Python 3.13 and PyInstaller 6.22.3 on Windows x64."""
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
    '--onefile', '--windowed', '--name', 'FF6-KR-Patcher-V0.75',
    '--distpath', str(HERE.parent / 'dist'), '--workpath', str(HERE.parent / '.build/patcher'),
    '--specpath', str(HERE.parent / '.build'),
    '--add-data', str(HERE / 'resources') + ';resources', str(HERE / 'patcher.py')], check=True)
