"""Bootstrap a private virtual environment without administrator access."""
import hashlib
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
if sys.version_info < (3, 12):
    raise SystemExit('Python 3.12 or newer is required. Install Python 3.12 from python.org.')
venv = root / '.venv-local'
python = venv / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
requirements = root / 'requirements-local.txt'
marker = venv / '.requirements-sha256'
fingerprint = hashlib.sha256(requirements.read_bytes()).hexdigest()
if not python.is_file():
    subprocess.run([sys.executable, '-m', 'venv', str(venv)], check=True)
if not marker.exists() or marker.read_text() != fingerprint:
    print('Installing packages. Internet is required on the first run.', flush=True)
    subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(requirements)], cwd=root, check=True)
    marker.write_text(fingerprint)
try:
    result = subprocess.run([str(python), '-m', 'src.local_server', *sys.argv[1:]], cwd=root)
    raise SystemExit(result.returncode)
except KeyboardInterrupt:
    pass
