"""Build v083 from preserved v082, restoring original large numeral pixels."""
import json,struct,shutil
from emu import ROOT
from pac import compress,decompress
from cdimage import build_image,sha256
from battle_big_text import compile_runtime,FONT_OFFSET,CODE_OFFSET,DIGIT_FIRST,DIGIT_COUNT

def jump(a):return (2<<26)|((a>>2)&0x3ffffff)
def main():
    source=ROOT/'work/v082-cache-payloads';dest=ROOT/'work/v083-cache-payloads'
    old=ROOT/'work/candidates/FF6-KR-main-development-v082';name='FF6-KR-main-development-v083'
    assert sha256(old/(old.name+'.bin'))=='7c3524c47e1e36fb1f8632ac12a5f12c9a1744865ed7b1101b1aca30f18113a0'
    baseline=ROOT/'analysis/v082-battle-big-text-insertion.json'
    if not baseline.exists():shutil.copy2(ROOT/'analysis/battle-big-text-insertion.json',baseline)
    big=json.loads(baseline.read_text('utf8'));report=json.loads((old/'build-report.json').read_text('utf8'))
    changes={p:(source/p).read_bytes() for p in report['changed_files']}
    overlay=bytearray(decompress(changes['BTL/BATTLE.PAC'])[0]);data=bytearray(changes['BTL/FF6_BTL.BIN'])
    lut=bytes(data[0x3c00+big['small_lut_offset']:0x3c00+big['small_lut_offset']+1248*2])
    code,symbols=compile_runtime();lut_at=(CODE_OFFSET+len(code)+3)&~3
    assert lut_at+len(lut)<=FONT_OFFSET+1248*22
    data[0x3c00+CODE_OFFSET:0x3c00+FONT_OFFSET+1248*22]=bytes(FONT_OFFSET+1248*22-CODE_OFFSET)
    data[0x3c00+CODE_OFFSET:0x3c00+CODE_OFFSET+len(code)]=code
    data[0x3c00+lut_at:0x3c00+lut_at+len(lut)]=lut
    struct.pack_into('<I',data,0x3bb4,0x8019b800+lut_at)
    original=(ROOT/'work/extracted/BTL/FF6_BTL.BIN').read_bytes()
    from korean_codec import font_index
    assert not any(DIGIT_FIRST<=font_index(bytes.fromhex(h))<DIGIT_FIRST+DIGIT_COUNT for h in big['mapping'].values())
    for digit in range(DIGIT_COUNT):
        a=FONT_OFFSET+(1075+digit)*22;b=0x3c00+FONT_OFFSET+(DIGIT_FIRST+digit)*22
        data[b:b+22]=original[a:a+22]
    for hook in big['hooks']:
        at=hook['address']-0x800c8000
        assert struct.unpack_from('<I',overlay,at)[0]==jump(big['symbols'][hook['symbol']])
        struct.pack_into('<I',overlay,at,jump(symbols[hook['symbol']]))
        hook['bytes']=overlay[at:at+8].hex()
    assert struct.unpack_from('<I',overlay,0x38+0x18*4)[0]==big['symbols']['kr_big_ref_case']
    struct.pack_into('<I',overlay,0x38+0x18*4,symbols['kr_big_ref_case'])
    assert struct.unpack_from('<I',overlay,0x801516e8-0x800c8000)[0]==0x3c038003
    packed=compress(bytes(overlay));size=len(changes['BTL/BATTLE.PAC']);assert len(packed)<=size
    changes['BTL/BATTLE.PAC']=packed+bytes(size-len(packed));changes['BTL/FF6_BTL.BIN']=bytes(data)
    big.update(symbols=symbols,runtime_bytes=len(code),small_lut_offset=lut_at,
        digit_glyph_relocation={'original_first':1075,'safe_first':DIGIT_FIRST,'count':DIGIT_COUNT,'pixels':'original 12x11 glyphs, unchanged'})
    dest.mkdir(exist_ok=True)
    for p,b in changes.items():
        out=dest/p;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(b)
    shutil.copy2(source/'menu-disc.bin',dest/'menu-disc.bin')
    disc=dict(changes);disc['HAR/MENUMENU.BIN']=(dest/'menu-disc.bin').read_bytes()
    _,built=build_image(ROOT,disc,name,relocations=report['relocations'],resizes={'DEODIR/DEO.PAC':0x13000,'BTL/BATTLE.PAC':0x4c000,'NAR/NAR_BIN3.BIN':0x20000})
    report.update(built);report['payload_directory']=dest.relative_to(ROOT).as_posix();report['battle_digit_fix']=big['digit_glyph_relocation']
    folder=ROOT/'work/candidates'/name
    (folder/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    for p in ('new_dialogue_offsets.json','omake-runtime.bin','omake-insertion.json'):shutil.copy2(old/p,folder/p)
    for p in (folder/'battle-big-text-insertion.json',ROOT/'analysis/v083-battle-big-text-insertion.json',ROOT/'analysis/battle-big-text-insertion.json'):
        p.write_text(json.dumps(big,ensure_ascii=False,indent=2)+'\n','utf8')
    (ROOT/'work/battle-overlay-small-names.bin').write_bytes(overlay)
    (ROOT/'work/battle-korean-data.bin').write_bytes(data)
    print(built['target_sha256'],flush=True)

if __name__=='__main__':main()
