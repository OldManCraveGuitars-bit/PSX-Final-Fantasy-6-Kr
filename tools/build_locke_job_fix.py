"""v085: restore Locke's job to Adventurer; preserve v084 dialogue and battle fixes."""
import json, shutil, struct
import lz4.block
from textcodec import ROOT
from cdimage import build_image, sha256
from pac import decompress
from menu_catalog import patch as patch_catalog
from psx_ui import patch as patch_psx


def read(path): return json.loads(path.read_text('utf8'))
def save(path, data): path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf8')


def main():
    name='FF6-KR-main-development-v085'
    old=ROOT/'work/candidates/FF6-KR-main-development-v084'
    src=ROOT/'work/v084-cache-payloads'
    restored=ROOT/'work/v083-cache-payloads'
    dest=ROOT/'work/v085-cache-payloads'
    assert not (ROOT/'work/candidates'/name).exists(), 'Candidate already exists; preserve it.'
    assert sha256(old/(old.name+'.bin'))=='6bb23a184380ce6c158185d4c634b4b0ca23a3196f16da47be2b40afd33b9454'
    report=read(old/'build-report.json')
    changes={p:(src/p).read_bytes() for p in report['changed_files']}
    backup=ROOT/'work/snapshots/v084-before-job-correction';backup.mkdir(parents=True,exist_ok=True)
    for f in ('menu-catalog-encoded.json','menu-catalog-insertion.json','menu-catalog-wide.json','psx-ui-insertion.json','omake-insertion.json'):
        if not (backup/f).exists():shutil.copy2(ROOT/'analysis'/f,backup/f)
    assert read(ROOT/'translations/menu-jobs.ko.json')['1']['translation']=='모험가'
    assert read(ROOT/'translations/omake-small.ko.json')['strings'][710]=='모험가'
    dialogue=read(ROOT/'translations/manual_dialogue.json')
    for idx in (42,48,134,1901,2616,2936):assert '트레저 헌터' in dialogue[str(idx)]

    # Re-encode against the old coherent menu bank and prove a byte-exact restore.
    small=read(ROOT/'analysis/small-text-insertion.json')
    menu,_=patch_catalog(bytearray((restored/'HAR/MENUMENU.BIN').read_bytes()),0x31200+small['label_pool_bytes'],small['mapping'])
    assert bytes(menu)==(restored/'HAR/MENUMENU.BIN').read_bytes()
    changes['HAR/MENUMENU.BIN']=bytes(menu)
    changes=patch_psx(changes)
    for p in ('DEODIR/DEO.PAC','DEODIR/ALLTIM.BIN'):
        assert changes[p]==(restored/p).read_bytes(),p

    # The only v084 bonus change was this job; restore its original complete bank.
    bonus=read(ROOT/'work/candidates/FF6-KR-main-development-v083/omake-insertion.json')
    changes['OMAKEDIR/OMAKE.PAC']=(restored/'OMAKEDIR/OMAKE.PAC').read_bytes()
    overlay=decompress(changes['OMAKEDIR/OMAKE.PAC'])[0]
    stream=bytearray()
    for c in '모험가':
        i=bonus['small_mapping'][c];stream+=bytes((0x10+(i>>7),0x80+(i&127)))
    stream.append(0)
    ptr=struct.unpack_from('<I',overlay,bonus['small_directory_address']-0x800c8000+710*4)[0]-0x800c8000
    assert overlay[ptr:ptr+len(stream)]==stream
    assert bonus['small_encoded'][710]==stream.hex()

    # Only restore the two menu mirrors. v084's field dialogue mirror stays exact.
    disc=bytearray((src/'menu-disc.bin').read_bytes())
    first,second=report['field_cache']['menu_part_bytes'];end=first+second
    disc[:end]=(restored/'menu-disc.bin').read_bytes()[:end]
    for start,capacity,raw in ((0,first,menu[:0x33000]),(first,second,menu[0x52000:0x60000])):
        packed=lz4.block.compress(bytes(raw),mode='high_compression',compression=12,store_size=True)
        assert bytes(disc[start:start+len(packed)])==packed and len(packed)<=capacity
        assert lz4.block.decompress(packed)==bytes(raw)
    assert bytes(disc[end:])==(src/'menu-disc.bin').read_bytes()[end:]
    changed=[p for p,b in changes.items() if b!=(src/p).read_bytes()]
    assert set(changed)=={'HAR/MENUMENU.BIN','DEODIR/DEO.PAC','DEODIR/ALLTIM.BIN','OMAKEDIR/OMAKE.PAC'}
    assert changes['NAR/NAR_BIN3.BIN']==(src/'NAR/NAR_BIN3.BIN').read_bytes()
    assert changes['BTL/FF6_BTL.BIN']==(src/'BTL/FF6_BTL.BIN').read_bytes()
    assert changes['BTL/BATTLE.PAC']==(src/'BTL/BATTLE.PAC').read_bytes()
    dest.mkdir(parents=True,exist_ok=True)
    for p,b in changes.items():
        out=dest/p;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(b)
    (dest/'menu-disc.bin').write_bytes(disc)
    payload=dict(changes);payload['HAR/MENUMENU.BIN']=bytes(disc)
    _,built=build_image(ROOT,payload,name,relocations=report['relocations'],resizes={'DEODIR/DEO.PAC':0x13000,'BTL/BATTLE.PAC':0x4c000,'NAR/NAR_BIN3.BIN':0x20000})
    report.update(built);report['payload_directory']=dest.relative_to(ROOT).as_posix()
    report['locke_term']={'dialogue':'트레저 헌터','job':'모험가'}
    folder=ROOT/'work/candidates'/name
    save(folder/'build-report.json',report)
    for f in ('new_dialogue_offsets.json','omake-runtime.bin','battle-big-text-insertion.json'):
        shutil.copy2(old/f,folder/f)
    save(folder/'omake-insertion.json',bonus);save(ROOT/'analysis/omake-insertion.json',bonus)
    result={'candidate':name,'sha256':built['target_sha256'],'baseline':'v084',
        'job':'모험가','dialogue_term':'트레저 헌터','dialogue_ids_unchanged':[42,48,134,1901,2616,2936],
        'changed_payloads':changed+['menu-disc.bin'],
        'job_banks_byte_exact_v083':True,'PSX_preview_rebuilt_with_coherent_font_bank':True,
        'bonus_job_710_native_reference_verified':True,'all_other_payloads_byte_exact_v084':True,
        'battle_attack_name_fix_preserved':True,'field_dialogue_and_cache_tail_byte_exact_v084':True,
        'cache_routes_and_sizes_unchanged':True}
    save(ROOT/'analysis/v085-job-correction.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':main()
