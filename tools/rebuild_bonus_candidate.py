"""Rebuild only bonus assets, preserving already verified gameplay payloads."""
import json,struct,sys
from textcodec import ROOT
from omake_runtime import patch
from cdimage import build_image

def main():
    name=sys.argv[1];folder=ROOT/'work/candidates'/name
    prior=json.loads((folder/'build-report.json').read_text('utf8'))
    changes={p.relative_to(ROOT/'work/modified').as_posix():p.read_bytes() for p in (ROOT/'work/modified').rglob('*') if p.is_file()}
    before=dict(changes);exe=bytearray(changes['SLPM_861.98']);original=(ROOT/'work/extracted/SLPM_861.98').read_bytes()
    prefix=0x80038000-struct.unpack_from('<I',exe,0x18)[0]
    old=json.loads((folder/'omake-insertion.json').read_text('utf8'))
    assert exe[0x2bcd0+prefix:0x2bcd4+prefix].hex()==old['relocation_msf']
    for at,length in [(0x1f5c,8),(0x2bcd0,4),(0x2928,4),(0x293c,4)]:
        exe[at+prefix:at+prefix+length]=original[at:at+length]
    changes['SLPM_861.98']=bytes(exe);changes=patch(changes)
    changed=[k for k in changes if changes[k]!=before[k]]
    assert set(changed)<={'OMAKEDIR/OMAKE.PAC','OMAKEDIR/ALLTIM.BIN','SLPM_861.98'},changed
    target,report=build_image(ROOT,changes,name,
        relocations={'HAR/MENUMENU.BIN':'DUMMY0.DAT','OMAKEDIR/OMAKE.PAC':{'reserve':'DUMMY0.DAT','sector_offset':256},'BTL/FF6_BTL.BIN':'DUMMY1.DAT','SLPM_861.98':'DUMMY2.DAT'},
        resizes={'DEODIR/DEO.PAC':0x13000,'BTL/BATTLE.PAC':0x4c000})
    prior.update(report);prior['bonus_menu_small_literals']=len(json.loads((ROOT/'translations/omake-small.ko.json').read_text('utf8'))['records'])
    (folder/'build-report.json').write_text(json.dumps(prior,ensure_ascii=False,indent=2)+'\n','utf8')
    for k in changed:(ROOT/'work/modified'/k).write_bytes(changes[k])
    for filename in ['omake-insertion.json']:(folder/filename).write_bytes((ROOT/'analysis'/filename).read_bytes())
    (folder/'omake-runtime.bin').write_bytes((ROOT/'work/omake-runtime.bin').read_bytes())
    print(dict(candidate=name,changed_payloads=changed))

if __name__=='__main__':main()
