"""Incremental reported-issue build, preserving the verified v085 cache layout."""
import json,struct,shutil
import lz4.block
from textcodec import ROOT
from pac import compress,decompress
from cdimage import build_image
from build_main_dialogue import prepare_field
from small_runtime import compile_runtime
from world_menu_loading import patch as patch_world

NAME='FF6-KR-main-development-v086'
BASE=ROOT/'work/v085-cache-payloads'
OUT=ROOT/'work/v086-cache-payloads'
def jump(a,link=False):return ((3 if link else 2)<<26)|((a>>2)&0x3ffffff)
def pad(b,n):
    assert len(b)<=n,('allocation',len(b),n)
    return bytes(b)+bytes(n-len(b))
def packed(b,n,label,report):
    p=lz4.block.compress(bytes(b),mode='high_compression',compression=12,store_size=True)
    assert lz4.block.decompress(p)==b,label
    report[label]={'packed':len(p),'capacity':n,'decoded':len(b)}
    return pad(p,n)
def main():
    prior=ROOT/'work/candidates/FF6-KR-main-development-v085'
    old=json.loads((prior/'build-report.json').read_text('utf8'))
    changes={p:(BASE/p).read_bytes() for p in old['changed_files']}
    field,meta=prepare_field()
    overlay=bytearray(decompress(field['NAR/NARITA.PAC'])[0])
    old_overlay=decompress(changes['NAR/NARITA.PAC'])[0]
    at=0x800d238c-0x800c8000
    assert overlay[at:at+8]==bytes.fromhex('d249030c00000000')
    overlay[at:at+8]=old_overlay[at:at+8]
    field['NAR/NARITA.PAC']=pad(compress(bytes(overlay)),len(changes['NAR/NARITA.PAC']))
    script=bytearray(pad(field['NAR/NAR_BIN3.BIN'],0x20000))
    script[0x1fa00:]=changes['NAR/NAR_BIN3.BIN'][0x1fa00:]
    field['NAR/NAR_BIN3.BIN']=bytes(script)
    changes.update(field)
    menu=bytearray(changes['HAR/MENUMENU.BIN']);har=bytearray(decompress(changes['HAR/HARATA.PAC'])[0])
    code,syms=compile_runtime(True)
    small_path=ROOT/'analysis/small-runtime.json'
    small_runtime=json.loads(small_path.read_text('utf8'))
    small_runtime.update(symbols=syms,runtime_bytes=len(code))
    small_path.write_text(json.dumps(small_runtime,ensure_ascii=False,indent=2)+'\n','utf8')
    menu[0x2e000:0x30800]=pad(code,0x2800)
    menu[0x5f000:0x5f500]=pad((ROOT/'work/menu-big-runtime.bin').read_bytes(),0x500)
    menu[0x5f500:0x60000]=pad((ROOT/'work/menu-boost-runtime.bin').read_bytes(),0xb00)
    retarget={jump(v,link):jump(syms[k],link) for k,v in old['field_cache']['menu_symbols'].items() if k in syms for link in (False,True)}
    for at in range(0,len(har)-3,4):
        w=struct.unpack_from('<I',har,at)[0]
        if w in retarget:struct.pack_into('<I',har,at,retarget[w])
    changes['HAR/MENUMENU.BIN']=bytes(menu)
    changes['HAR/HARATA.PAC']=pad(compress(bytes(har)),old['field_cache']['har_read_bytes'])
    from battle_runtime import prepare
    from battle_big_text import patch
    resource,font,battle,small=prepare()
    data=bytearray(pad((ROOT/'work/extracted/BTL/FF6_BTL.BIN').read_bytes(),0x45000))
    data,resource,battle,big=patch(data,resource,battle,small)
    at=0x80169404-0x800c8000
    assert battle[at:at+8]==bytes.fromhex('212020020280053c')
    battle[at:at+8]=decompress(changes['BTL/BATTLE.PAC'])[0][at:at+8]
    changes['BTL/BATTLE.PAC']=pad(compress(bytes(battle)),len(changes['BTL/BATTLE.PAC']))
    changes['BTL/FF6_BTL.BIN']=bytes(resource+data)
    changes['SLPM_861.98']=patch_world(changes['SLPM_861.98'])
    (ROOT/'work/battle-korean-persistent.bin').write_bytes(resource)
    (ROOT/'work/battle-overlay-small-names.bin').write_bytes(battle)
    (ROOT/'work/battle-korean-data.bin').write_bytes(resource+data)
    disk=bytearray((BASE/'menu-disc.bin').read_bytes());banks={}
    def bank(at,raw,capacity,label):disk[at:at+capacity]=packed(raw,capacity,label,banks)
    p1,p2=old['field_cache']['menu_part_bytes']
    bank(0,menu[:0x33000],p1,'menu1');bank(p1,menu[0x52000:0x60000],p2,'menu2')
    full=old['field_cache']['full_reload'];a=0x40000;cap=full['first_read_bytes']
    bank(a,pad(changes['NAR/NAR_BIN.BIN'],full['decoded_field_bytes']),cap,'field_full');a+=cap
    cap=full['second_read_bytes']-0x22800
    bank(a,script,cap,'script');a+=cap
    disk[a:a+0x22800]=pad(changes['NAR/NARITA.PAC'],0x22800);a+=0x22800
    a+=old['field_cache']['routes']['MENU_NAME_BYTES']
    cap=old['field_cache']['field_fast_read_bytes']-0x22800
    bank(a,changes['NAR/NAR_BIN.BIN'][:0x58000],cap,'field_fast');a+=cap
    disk[a:a+0x22800]=pad(changes['NAR/NARITA.PAC'],0x22800)
    OUT.mkdir(exist_ok=True)
    for p,b in changes.items():
        target=OUT/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
        target=ROOT/'work/modified'/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
    (OUT/'menu-disc.bin').write_bytes(disk)
    disc_changes=dict(changes);disc_changes['HAR/MENUMENU.BIN']=bytes(disk)
    target,report=build_image(ROOT,disc_changes,NAME,relocations=old['relocations'],resizes={'DEODIR/DEO.PAC':0x13000,'BTL/BATTLE.PAC':0x4c000,'NAR/NAR_BIN3.BIN':0x20000})
    result={**old,**report};result['field_cache']['menu_symbols']=syms
    result.update(incremental_baseline='v085',dialogue_count=len(meta['rows']),glyph_count=len(meta['assigned']),
        bank_index=meta['bank_index'],dialogue_raw_bytes=meta['dialogue_report']['raw_bytes'],
        v086_banks=banks,v086_fixes=['config cursor native task preservation','native dynamic field numeral glyph preservation','world tent full OGA restore','dialogue proofreading and word-boundary preservation','Vargas tutorial layout'],
        v086_native_verification='pending',proofreading_report='analysis/v086-review-progress.json')
    (target.parent/'build-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    (target.parent/'new_dialogue_offsets.json').write_text(json.dumps(meta['new_offsets']),'utf8')
    for f in ('omake-insertion.json','omake-runtime.bin'):shutil.copy2(prior/f,target.parent/f)
    print(json.dumps({'candidate':str(target),'sha256':report['target_sha256'],'banks':banks},ensure_ascii=False))
if __name__=='__main__':main()
