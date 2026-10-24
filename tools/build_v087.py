"""Update all SwdTech name paths while preserving the v086 field cache."""
import json,shutil
import lz4.block
from textcodec import ROOT
from pac import compress,decompress
from cdimage import build_image

NAME='FF6-KR-main-development-v087'
def main():
    prior=ROOT/'work/candidates/FF6-KR-main-development-v086'
    old=json.loads((prior/'build-report.json').read_text('utf8'))
    base=ROOT/'work/v086-cache-payloads';out=ROOT/'work/v087-cache-payloads'
    changes={p:(base/p).read_bytes() for p in old['changed_files']}
    from swdtech_battle import patch as patch_bushido
    payload,battle,big=patch_bushido(changes['BTL/FF6_BTL.BIN'],decompress(changes['BTL/BATTLE.PAC'])[0])
    resource,data=payload[:0x3c00],payload[0x3c00:]
    packed=compress(bytes(battle));capacity=len(changes['BTL/BATTLE.PAC'])
    assert len(packed)<=capacity
    changes['BTL/BATTLE.PAC']=packed+bytes(capacity-len(packed))
    changes['BTL/FF6_BTL.BIN']=bytes(resource+data)
    from menu_big_text import patch as patch_menu
    menu=bytearray(changes['HAR/MENUMENU.BIN']);har=bytearray(decompress(changes['HAR/HARATA.PAC'])[0])
    menu_small=json.loads((ROOT/'analysis/small-runtime.json').read_text('utf8'))['mapping']
    menu,har=patch_menu(menu,har,menu_small)
    packed=compress(bytes(har));capacity=len(changes['HAR/HARATA.PAC']);assert len(packed)<=capacity
    changes['HAR/HARATA.PAC']=packed+bytes(capacity-len(packed));changes['HAR/MENUMENU.BIN']=bytes(menu)
    for name,b in [('battle-korean-persistent.bin',resource),('battle-korean-data.bin',resource+data),('battle-overlay-small-names.bin',battle)]:
        (ROOT/'work'/name).write_bytes(b)
    (ROOT/'work/battle-big-runtime.bin').write_bytes(data[big['font_tail_offset']:big['font_tail_offset']+big['runtime_bytes']])
    changed=[]
    for p,b in changes.items():
        dest=out/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
        if b!=(base/p).read_bytes():changed.append(p)
    assert set(changed)=={'BTL/BATTLE.PAC','BTL/FF6_BTL.BIN','HAR/HARATA.PAC','HAR/MENUMENU.BIN'},changed
    disk=bytearray((base/'menu-disc.bin').read_bytes());p1,p2=old['field_cache']['menu_part_bytes'];banks=[]
    for at,raw,capacity in [(0,menu[:0x33000],p1),(p1,menu[0x52000:0x60000],p2)]:
        packed=lz4.block.compress(bytes(raw),mode='high_compression',compression=12,store_size=True)
        assert lz4.block.decompress(packed)==raw and len(packed)<=capacity,(len(packed),capacity)
        disk[at:at+capacity]=packed+bytes(capacity-len(packed));banks.append({'packed':len(packed),'capacity':capacity})
    (out/'menu-disc.bin').write_bytes(disk)
    disc_changes=dict(changes);disc_changes['HAR/MENUMENU.BIN']=bytes(disk)
    image,report=build_image(ROOT,disc_changes,NAME,relocations=old['relocations'],resizes={'DEODIR/DEO.PAC':0x13000,'BTL/BATTLE.PAC':0x4c000,'NAR/NAR_BIN3.BIN':0x20000})
    result={**old,**report,'incremental_baseline':'v086','payload_directory':'work/v087-cache-payloads',
        'v087_changed_payloads':changed,'v087_fix':'Eight Bushido defaults, 249 saved-name characters, skill menu, rename preview and picker; original save bytes preserved.',
        'v087_menu_banks':banks,
        'v087_native_verification':'pending'}
    (image.parent/'build-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    shutil.copy2(ROOT/'analysis/battle-big-text-insertion.json',image.parent/'battle-big-text-insertion.json')
    print(json.dumps({'candidate':str(image),'sha256':report['target_sha256'],'changed':changed},ensure_ascii=False))

if __name__=='__main__':main()
