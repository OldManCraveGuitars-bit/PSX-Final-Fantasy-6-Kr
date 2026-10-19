"""Build v082 from immutable v081 payloads with one guarded battle fix."""
import json,struct,shutil
from emu import ROOT
from pac import compress,decompress
from cdimage import build_image,sha256

def main():
    source=ROOT/'work/v081-cache-payloads'
    dest=ROOT/'work/v082-cache-payloads'
    old=ROOT/'work/candidates/FF6-KR-main-development-v081'
    name='FF6-KR-main-development-v082'
    report=json.loads((old/'build-report.json').read_text('utf8'))
    assert sha256(old/(old.name+'.bin'))=='2c65b033e89d0886623891bb19c8510239055d7ba88acd9a6ab68cb4a3a38dcf'
    changes={p:(source/p).read_bytes() for p in report['changed_files']}
    overlay=bytearray(decompress(changes['BTL/BATTLE.PAC'])[0])
    offset=0x801516e8-0x800c8000
    assert struct.unpack_from('<I',overlay,offset)[0]==0
    assert struct.unpack_from('<I',overlay,0x801517b4-0x800c8000)[0]==0x1440ffcc
    original=(ROOT/'work/decompressed/BTL/BATTLE.PAC').read_bytes()
    assert struct.unpack_from('<I',original,offset)[0]==0x3c038003
    struct.pack_into('<I',overlay,offset,0x3c038003)
    before=decompress(changes['BTL/BATTLE.PAC'])[0]
    assert before[:offset]==overlay[:offset] and before[offset+4:]==overlay[offset+4:]
    packed=compress(bytes(overlay));size=len(changes['BTL/BATTLE.PAC'])
    assert len(packed)<=size
    changes['BTL/BATTLE.PAC']=packed+bytes(size-len(packed))
    dest.mkdir(exist_ok=True)
    for p,data in changes.items():
        target=dest/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    shutil.copy2(source/'menu-disc.bin',dest/'menu-disc.bin')
    disc=dict(changes);disc['HAR/MENUMENU.BIN']=(dest/'menu-disc.bin').read_bytes()
    _,built=build_image(ROOT,disc,name,relocations=report['relocations'],resizes={'DEODIR/DEO.PAC':0x13000,'BTL/BATTLE.PAC':0x4c000,'NAR/NAR_BIN3.BIN':0x20000})
    report.update(built)
    report['payload_directory']=dest.relative_to(ROOT).as_posix()
    report['battle_window_fix']={'source':'v081','address':'0x801516e8','before':'0x00000000','after':'0x3c038003','loop_backedge':'0x801517b4','uncompressed_overlay_changed_bytes':4,'menu_cache_unchanged':True}
    folder=ROOT/'work/candidates'/name
    (folder/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    for p in ('new_dialogue_offsets.json','omake-runtime.bin','omake-insertion.json'):
        shutil.copy2(old/p,folder/p)
    print(built['target_sha256'],flush=True)

if __name__=='__main__':main()
