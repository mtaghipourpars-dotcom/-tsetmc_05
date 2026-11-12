"""Optional public-source retrieval; original files are not redistributed in this project."""
import urllib.request,json,hashlib,argparse
from pathlib import Path
from urllib.parse import quote
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dest',type=Path,required=True);a=p.parse_args();a.dest.mkdir(parents=True,exist_ok=True)
    for s in json.loads((ROOT/'external_sources.json').read_text()):
        url='https://raw.githubusercontent.com/'+s['source_repository']+'/'+s['source_commit']+'/'+quote(s['path'])
        raw=urllib.request.urlopen(url,timeout=30).read()
        actual=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        if actual!=s['git_blob_sha']:raise ValueError('Fingerprint mismatch')
        (a.dest/s['path']).write_bytes(raw)
        print(s['path'],len(raw),'verified')
