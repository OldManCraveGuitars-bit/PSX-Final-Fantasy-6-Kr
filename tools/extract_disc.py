"""Extract local FF6 PSX assets, preserving XA movies as raw sectors."""
from pathlib import Path
import sys, json, hashlib, importlib.util, os

ROOT = Path(__file__).resolve().parents[1]
SCANNER = Path(os.environ.get('FF6_DISC_SCANNER', str(ROOT/'local-tools/scan_psx_disc.py')))
if not SCANNER.is_file():
    raise SystemExit('Local PSX ISO scanner required: set FF6_DISC_SCANNER. See docs/DEVELOPMENT.md.')
spec = importlib.util.spec_from_file_location('psxiso', SCANNER)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

def main():
    inv = json.loads((ROOT/'analysis/disc_inventory.json').read_text('utf-8'))
    iso = module.PsxIso(Path(inv['source']['track_path']))
    manifest = []
    try:
        for e in inv['entries']:
            if e['is_directory'] or e['path'].startswith(('DUMMY','FAKE','SOUND/','STR/','OMAKEDIR/GALLERY')):
                continue
            out = ROOT/'work/extracted'/e['path']
            out.parent.mkdir(parents=True,exist_ok=True)
            if e['path'].startswith('MOVIE/'):
                iso.handle.seek(e['extent_lba']*2352)
                data = iso.handle.read((e['size']+2047)//2048*2352)
            else:
                data = iso.read_logical(e['extent_lba'],e['size'])
            out.write_bytes(data)
            manifest.append(dict(**e,extracted_bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
    finally:
        iso.close()
    (ROOT/'analysis/extracted_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n','utf-8')
    print(f'Extracted {len(manifest)} files')
    for e in manifest:
        if e['path'].endswith(('.PAC','.BIN')) or e['path'].startswith('SLPM'):
            data=(ROOT/'work/extracted'/e['path']).read_bytes()
            print(e['path'],len(data),data[:64].hex(' '))

if __name__=='__main__':
    main()
