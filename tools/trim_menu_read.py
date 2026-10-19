"""Relink a built candidate after reducing only the menu's zero-padding read."""
import json,struct,sys
from textcodec import ROOT
from cdimage import build_image
from small_runtime import MENU_READ_SIZE

def main():
    name=sys.argv[1];directory=ROOT/'work/candidates'/name
    report=json.loads((directory/'build-report.json').read_text('utf8'))
    changes={p:(ROOT/'work/modified'/p).read_bytes() for p in report['changed_files']}
    assert len(changes['HAR/MENUMENU.BIN'])==0x68000
    assert not any(changes['HAR/MENUMENU.BIN'][MENU_READ_SIZE:])
    exe=bytearray(changes['SLPM_861.98'])
    prefix=0x80038000-struct.unpack_from('<I',exe,0x18)[0];at=prefix+0x1f3c
    assert struct.unpack_from('<II',exe,at)==(0x3c090006,0x35298000)
    struct.pack_into('<II',exe,at,0x3c090000|(MENU_READ_SIZE>>16),0x35290000|(MENU_READ_SIZE&65535))
    changes['SLPM_861.98']=bytes(exe)
    _,updated=build_image(ROOT,changes,name,relocations=report['relocations'],
        resizes={'DEODIR/DEO.PAC':0x13000,'BTL/BATTLE.PAC':0x4c000})
    report.update(updated)
    report['menu_read_optimization']={'old_bytes':0x68000,'new_bytes':MENU_READ_SIZE,
        'omitted':'32 KiB write-only GPU packet pool; all packet words are assigned before use.'}
    (directory/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    (ROOT/'work/modified/SLPM_861.98').write_bytes(exe)
    path=ROOT/'analysis/small-runtime.json';r=json.loads(path.read_text('utf8'));r['menu_read_bytes']=MENU_READ_SIZE
    path.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n','utf8')
    print(report['menu_read_optimization'],updated['target_sha256'])

if __name__=='__main__':main()
