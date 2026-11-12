"""Local setup: preserve existing provider keys, generate an installation admin token."""
from pathlib import Path
import secrets

root=Path(__file__).resolve().parents[1]
target=root/'.env'
content=target.read_text(encoding='utf-8') if target.exists() else (root/'.env.example').read_text(encoding='utf-8')
lines=content.splitlines()
found=False
for i,line in enumerate(lines):
    if line.startswith('ADMIN_TOKEN='):
        found=True
        if line.partition('=')[2].strip() in ('','replace-with-a-long-random-value'):
            lines[i]='ADMIN_TOKEN='+secrets.token_urlsafe(32)
if not found:lines.append('ADMIN_TOKEN='+secrets.token_urlsafe(32))
target.write_text('\n'.join(lines)+'\n',encoding='utf-8')
target.chmod(0o600)
print('Configuration ready. The management key is in the local .env file.')
