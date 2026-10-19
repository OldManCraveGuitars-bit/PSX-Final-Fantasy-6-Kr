"""v084: atomic enemy-name references and editor-managed Locke terminology.

Preserve all font mappings, field pointers and cache routes from v083. The six
changed dialogue streams fit their original Huffman allocations.
"""
import json,struct,shutil
import lz4.block
from emu import ROOT
from pac import compress,decompress
from cdimage import build_image,sha256
from battle_big_text import compile_runtime,FONT_OFFSET,CODE_OFFSET

def read_json(path):return json.loads(path.read_text('utf8'))
def save_json(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf8')
def jump(a):return 0x08000000|((a>>2)&0x3ffffff)

def main():
    tag='v084';name='FF6-KR-main-development-'+tag
    src=ROOT/'work/v083-cache-payloads';dest=ROOT/'work/v084-cache-payloads'
    old=ROOT/'work/candidates/FF6-KR-main-development-v083'
    assert sha256(old/(old.name+'.bin'))=='4db454fb1964b9a1590f3cddcfab9ad1cfa381627c089fc4d7f0f653928b393c'
    report=read_json(old/'build-report.json')
    changes={p:(src/p).read_bytes() for p in report['changed_files']}
    # Immutable metadata for every bank whose generated report will change.
    snap=ROOT/'work/snapshots/v083-before-enemy-name-fix';snap.mkdir(parents=True,exist_ok=True)
    for f in ['dialogue-runtime.json','dialogue-native-layout.json','menu-catalog-encoded.json','menu-catalog-insertion.json','omake-insertion.json','psx-ui-insertion.json']:
        if not (snap/f).exists():shutil.copy2(ROOT/'analysis'/f,snap/f)
    big=read_json(old/'battle-big-text-insertion.json')
    overlay=bytearray(decompress(changes['BTL/BATTLE.PAC'])[0]);data=bytearray(changes['BTL/FF6_BTL.BIN'])
    lut=bytes(data[0x3c00+big['small_lut_offset']:0x3c00+big['small_lut_offset']+2496])
    code,symbols=compile_runtime();lut_at=(CODE_OFFSET+len(code)+3)&~3
    assert lut_at+len(lut)<=FONT_OFFSET+1248*22
    data[0x3c00+CODE_OFFSET:0x3c00+FONT_OFFSET+1248*22]=bytes(FONT_OFFSET+1248*22-CODE_OFFSET)
    data[0x3c00+CODE_OFFSET:0x3c00+CODE_OFFSET+len(code)]=code
    data[0x3c00+lut_at:0x3c00+lut_at+len(lut)]=lut
    struct.pack_into('<I',data,0x3bb4,0x8019b800+lut_at)
    for h in big['hooks']:
        at=h['address']-0x800c8000
        assert struct.unpack_from('<I',overlay,at)[0]==jump(big['symbols'][h['symbol']])
        struct.pack_into('<I',overlay,at,jump(symbols[h['symbol']]))
        h['bytes']=overlay[at:at+8].hex()
    struct.pack_into('<I',overlay,0x98,symbols['kr_big_ref_case'])
    assert struct.unpack_from('<I',overlay,0x896e8)[0]==0x3c038003
    packed=compress(bytes(overlay));assert len(packed)<=len(changes['BTL/BATTLE.PAC'])
    changes['BTL/BATTLE.PAC']=packed+bytes(len(changes['BTL/BATTLE.PAC'])-len(packed))
    changes['BTL/FF6_BTL.BIN']=bytes(data)
    big.update(symbols=symbols,runtime_bytes=len(code),small_lut_offset=lut_at,
        enemy_reference_copy='Write all four reference bytes before native display; FF operands never pass through the sentinel copier.')

    from prepare_translation import main as consolidate,clean
    consolidate()
    from dte import compress_text
    from korean_codec import CONTROL
    from textlayout import wrap
    runtime=read_json(snap/'dialogue-runtime.json');layout=read_json(snap/'dialogue-native-layout.json')
    encoding=read_json(ROOT/'work/korean_encoding.json')
    mapping={c:bytes.fromhex(v) for c,v in encoding['mapping'].items()}
    assigned={c:bytes.fromhex(v) for c,v in encoding['replaced'].items()}
    dictionary=[(r['text'],bytes.fromhex(r['bytes'])) for r in read_json(ROOT/'analysis/korean-mte-plan.json')['dictionary']]
    script=bytearray(changes['NAR/NAR_BIN3.BIN'])
    at=runtime['symbols']['kr_dialogue_huffman']-0x801a6200
    table=script[at:at+352];h=struct.unpack('<48H',table[:96]);alphabet=table[96:];codes={}
    for n in range(1,16):
        for j in range(h[n]):codes[alphabet[h[32+n]+j]]=(h[16+n]+j,n)
    def pack_text(raw):
        out=bytearray(struct.pack('<H',len(raw)));bits=n=0
        for c in raw:
            v,k=codes[c];bits=(bits<<k)|v;n+=k
            while n>=8:n-=8;out.append((bits>>n)&255)
        if n:out.append((bits<<(8-n))&255)
        return bytes(out)
    manual=read_json(ROOT/'translations/manual_dialogue.json');prose=[]
    widths=changes['NAR/NAR_BIN.BIN'][0x646d0:0x64bd0]
    for row in layout:
        if '보물 사냥꾼' not in row['translation']:continue
        idx=row['id'];text=wrap(clean(manual[str(idx)]),mapping,assigned,widths)
        assert CONTROL.findall(text)==CONTROL.findall(row['translation'])
        before=pack_text(bytes.fromhex(runtime['streams'][idx]))
        raw=compress_text(text,mapping,dictionary)+b'\0';after=pack_text(raw);off=runtime['offsets'][idx]
        assert script[off:off+len(before)]==before and len(after)<=len(before),(idx,len(after),len(before))
        script[off:off+len(before)]=after+bytes(len(before)-len(after))
        prose.append(dict(id=idx,before=row['translation'],after=text,offset=off,capacity=len(before),used=len(after)))
        row['translation']=text;runtime['streams'][idx]=raw.hex()
    assert len(prose)==6
    runtime['raw_bytes']=sum(len(bytes.fromhex(x)) for x in runtime['streams'])
    changes['NAR/NAR_BIN3.BIN']=bytes(script)

    # Menu jobs share the stable small atlas; repack only the existing name pool.
    from menu_catalog import patch as patch_catalog
    small=read_json(ROOT/'analysis/small-text-insertion.json')
    menu,_=patch_catalog(bytearray(changes['HAR/MENUMENU.BIN']),0x31200+small['label_pool_bytes'],small['mapping'])
    changes['HAR/MENUMENU.BIN']=bytes(menu)
    # Save preview jobs use a separate native font bank. Rebuild that bank and
    # its labels together through the existing guarded PSX GUI builder.
    from psx_ui import patch as patch_psx
    changes=patch_psx(changes)
    # Bonus job: same glyph atlas, one new string in the documented free pool.
    bonus=read_json(old/'omake-insertion.json');omake=bytearray(decompress(changes['OMAKEDIR/OMAKE.PAC'])[0])
    text=read_json(ROOT/'translations/omake-small.ko.json')['strings'][710];stream=bytearray()
    for c in text:
        if ord(c)<128:stream.append(ord(c))
        else:
            i=bonus['small_mapping'][c];stream+=bytes((0x10+(i>>7),0x80+(i&127)))
    stream.append(0);off=(0x21648+bonus['pool_bytes']+1)&~1
    assert off+len(stream)<=0x2b930 and not any(omake[off:off+len(stream)])
    omake[off:off+len(stream)]=stream
    struct.pack_into('<I',omake,bonus['small_directory_address']-0x800c8000+710*4,0x800c8000+off)
    bonus['small_encoded'][710]=stream.hex();bonus['pool_bytes']=off+len(stream)-0x21648
    packed=compress(bytes(omake));assert len(packed)<=bonus['compressed_read_bytes']
    changes['OMAKEDIR/OMAKE.PAC']=packed
    bonus['overlay_packed_bytes']=len(packed)

    # Replace the compressed mirrors within their unchanged sector allocations.
    cache=report['field_cache'];disc=bytearray((src/'menu-disc.bin').read_bytes());mirror=[]
    def replace_bank(at,capacity,raw,label):
        packed=lz4.block.compress(bytes(raw),mode='high_compression',compression=12,store_size=True)
        assert len(packed)<=capacity,(label,len(packed),capacity)
        disc[at:at+capacity]=packed+bytes(capacity-len(packed))
        assert lz4.block.decompress(packed)==bytes(raw)
        mirror.append(dict(label=label,offset=at,capacity=capacity,packed_bytes=len(packed)))
    first,second=cache['menu_part_bytes']
    replace_bank(0,first,menu[:0x33000],'menu first')
    replace_bank(first,second,menu[0x52000:0x60000],'menu second')
    at=0x40000+cache['full_reload']['first_read_bytes']
    capacity=cache['full_reload']['second_read_bytes']-0x22800
    replace_bank(at,capacity,script,'field script')
    report['payload_directory']=dest.relative_to(ROOT).as_posix()
    dest.mkdir(exist_ok=True)
    for p,b in changes.items():
        out=dest/p;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(b)
    (dest/'menu-disc.bin').write_bytes(disc)
    payload=dict(changes);payload['HAR/MENUMENU.BIN']=bytes(disc)
    _,built=build_image(ROOT,payload,name,relocations=report['relocations'],resizes={'DEODIR/DEO.PAC':0x13000,'BTL/BATTLE.PAC':0x4c000,'NAR/NAR_BIN3.BIN':0x20000})
    report.update(built);report['enemy_attack_fix']=big['enemy_reference_copy'];report['locke_term']='트레저 헌터'
    folder=ROOT/'work/candidates'/name
    save_json(folder/'build-report.json',report)
    for f in ['new_dialogue_offsets.json','omake-runtime.bin']:shutil.copy2(old/f,folder/f)
    for p in [folder/'battle-big-text-insertion.json',ROOT/'analysis/battle-big-text-insertion.json',ROOT/'analysis/v084-battle-big-text-insertion.json']:save_json(p,big)
    for p in [folder/'omake-insertion.json',ROOT/'analysis/omake-insertion.json']:save_json(p,bonus)
    for f,value in [('dialogue-runtime.json',runtime),('dialogue-native-layout.json',layout)]:save_json(ROOT/'analysis'/f,value)
    (ROOT/'work/battle-overlay-small-names.bin').write_bytes(overlay)
    (ROOT/'work/battle-korean-data.bin').write_bytes(data)
    save_json(ROOT/'analysis/v084-terminology-insertion.json',dict(dialogue=prose,job='트레저 헌터',bonus_job_string=710,mirror_banks=mirror,field_pointers_and_font_exact=True,cache_routes_exact=True))
    print(built['target_sha256'],flush=True)

if __name__=='__main__':main()
