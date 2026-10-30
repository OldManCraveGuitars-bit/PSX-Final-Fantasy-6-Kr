"""Timed-dialogue correction on the published v087 payload/cache layout."""
import json,shutil
import lz4.block
from textcodec import ROOT
from pac import compress,decompress
from cdimage import build_image
from build_main_dialogue import prepare_field

NAME='FF6-KR-main-development-v088'

def pad(data,size):
    assert len(data)<=size,(len(data),size)
    return bytes(data)+bytes(size-len(data))

def main():
    prior=ROOT/'work/candidates/FF6-KR-main-development-v087'
    old=json.loads((prior/'build-report.json').read_text('utf8'))
    base=ROOT/'work/v087-cache-payloads';out=ROOT/'work/v088-cache-payloads'
    changes={p:(base/p).read_bytes() for p in old['changed_files']}
    field,meta=prepare_field()
    overlay=bytearray(decompress(field['NAR/NARITA.PAC'])[0])
    previous=decompress(changes['NAR/NARITA.PAC'])[0]
    at=0x800d238c-0x800c8000
    assert overlay[at:at+8]==bytes.fromhex('d249030c00000000')
    overlay[at:at+8]=previous[at:at+8]
    field['NAR/NARITA.PAC']=pad(compress(bytes(overlay)),len(changes['NAR/NARITA.PAC']))
    script=bytearray(pad(field['NAR/NAR_BIN3.BIN'],0x20000))
    script[0x1fa00:]=changes['NAR/NAR_BIN3.BIN'][0x1fa00:]
    field['NAR/NAR_BIN3.BIN']=bytes(script)
    changes.update(field)
    changed=[p for p,b in changes.items() if b!=(base/p).read_bytes()]
    assert set(changed)=={'NAR/NAR_BIN.BIN','NAR/NAR_BIN3.BIN','NAR/NARITA.PAC'},changed
    disk=bytearray((base/'menu-disc.bin').read_bytes());banks={}
    def bank(at,raw,capacity,label):
        packed=lz4.block.compress(bytes(raw),mode='high_compression',compression=12,store_size=True)
        assert lz4.block.decompress(packed)==raw
        disk[at:at+capacity]=pad(packed,capacity)
        banks[label]={'packed':len(packed),'capacity':capacity,'decoded':len(raw)}
    cache=old['field_cache'];full=cache['full_reload'];a=0x40000;cap=full['first_read_bytes']
    bank(a,pad(changes['NAR/NAR_BIN.BIN'],full['decoded_field_bytes']),cap,'field_full');a+=cap
    cap=full['second_read_bytes']-0x22800
    bank(a,script,cap,'script');a+=cap
    disk[a:a+0x22800]=pad(changes['NAR/NARITA.PAC'],0x22800);a+=0x22800
    a+=cache['routes']['MENU_NAME_BYTES']
    cap=cache['field_fast_read_bytes']-0x22800
    bank(a,changes['NAR/NAR_BIN.BIN'][:0x58000],cap,'field_fast');a+=cap
    disk[a:a+0x22800]=pad(changes['NAR/NARITA.PAC'],0x22800)
    # Both menu banks precede the field cache and stay byte-identical.
    assert disk[:0x40000]==(base/'menu-disc.bin').read_bytes()[:0x40000]
    for name,b in changes.items():
        dst=out/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(b)
        if name in changed:(ROOT/'work/modified'/name).write_bytes(b)
    (out/'menu-disc.bin').write_bytes(disk)
    disc=dict(changes);disc['HAR/MENUMENU.BIN']=bytes(disk)
    image,report=build_image(ROOT,disc,NAME,relocations=old['relocations'],resizes={'DEODIR/DEO.PAC':0x13000,'BTL/BATTLE.PAC':0x4c000,'NAR/NAR_BIN3.BIN':0x20000})
    result={**old,**report,'incremental_baseline':'v087','payload_directory':'work/v088-cache-payloads',
        'v088_changed_payloads':changed,'v088_banks':banks,'v088_dialogue_ids':[3,459],
        'v088_native_verification':'pending','dialogue_raw_bytes':meta['dialogue_report']['raw_bytes'],
        'glyph_count':len(meta['assigned']),'bank_index':meta['bank_index']}
    (image.parent/'build-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    (image.parent/'new_dialogue_offsets.json').write_text(json.dumps(meta['new_offsets']),'utf8')
    for name in ['battle-big-text-insertion.json']:shutil.copy2(prior/name,image.parent/name)
    print(json.dumps({'candidate':str(image),'sha256':report['target_sha256'],'changed':changed,'banks':banks},ensure_ascii=False))

if __name__=='__main__':main()
