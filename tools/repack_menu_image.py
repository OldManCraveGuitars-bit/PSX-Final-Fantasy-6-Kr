"""Repack current decoded development payloads using the current menu loader."""
import json,sys,struct
from textcodec import ROOT
from cdimage import build_image
from menu_loading import prepare

def main():
    name=sys.argv[1];folder=ROOT/'work/candidates'/name
    report=json.loads((folder/'build-report.json').read_text('utf8'))
    changes={p:(ROOT/'work/modified'/p).read_bytes() for p in report['changed_files']}
    from movie_subtitles import prepare as prepare_resident
    code,_,_=prepare_resident()
    exe=bytearray(changes['SLPM_861.98']);base=struct.unpack_from('<I',exe,0x18)[0]
    for address,data in [(0x80037800,code),(0x80037680,(ROOT/'work/menu-lz4.bin').read_bytes())]:
        at=address-base+0x800;exe[at:at+len(data)]=data
    changes['SLPM_861.98']=bytes(exe)
    changes,disc,routes=prepare(changes)
    _,built=build_image(ROOT,disc,name,relocations={**report['relocations'],**routes},
        resizes={'DEODIR/DEO.PAC':0x13000,'BTL/BATTLE.PAC':0x4c000})
    report.update(built);report['menu_loading']=json.loads((ROOT/'analysis/menu-loading.json').read_text('utf8'))
    (folder/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    for p,data in changes.items():(ROOT/'work/modified'/p).write_bytes(data)
    print(built['target_sha256'])

if __name__=='__main__':main()
