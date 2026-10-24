"""Relocate large menu labels and descriptions behind native reference records."""
import json,struct
from textcodec import ROOT
from korean_codec import allocate,encode,font_index,fixed_relocations,normalize,raster,JP
from small_text import encode_small,allocate_aliases

def reference(identifier):
    return bytes((0x18,identifier%255+1,identifier//255+1))

def patch(menu,overlay,small_mapping):
    catalog=json.loads((ROOT/'analysis/fixed-catalog-original.json').read_text('utf8'))
    names=json.loads((ROOT/'translations/fixed-catalog.ko.json').read_text('utf8'))
    descriptions=json.loads((ROOT/'analysis/descriptions-original.json').read_text('utf8'))
    translated=json.loads((ROOT/'translations/descriptions.ko.json').read_text('utf8'))
    abilities=json.loads((ROOT/'analysis/battle-abilities-original.json').read_text('utf8'))
    ability_translations=json.loads((ROOT/'translations/battle-abilities.ko.json').read_text('utf8'))
    extras=[r for r in abilities if r['category']!='monster_dialogue']
    selected=[r for r in catalog if r['encoding']=='bigText' and JP.search(r['source'])]
    texts=[normalize(names[str(r['id'])]['translation']).strip() for r in selected]
    texts += [normalize(translated[str(r['id'])]['translation']).strip() for r in descriptions]
    texts += [normalize(ability_translations[str(r['id'])]['translation']).strip() for r in extras]
    sword_chars=json.loads((ROOT/'translations/swdtech-characters.ko.json').read_text('utf8'))
    mapping,assigned=allocate(texts+[r['translation'] for r in sword_chars.values()])
    original=(ROOT/'work/extracted/HAR/MENUMENU.BIN').read_bytes()
    font=bytearray(original[0x12fdb:0x19b1b]);widths=bytearray(original[0x12adb:0x12fdb])
    for c,code in assigned.items():
        image=raster(c)
        glyph=b''.join(struct.pack('<H',sum(1<<(11-x) for x in range(12) if image.getpixel((x,y)))) for y in range(11))
        at=font_index(code)*22;font[at:at+22]=glyph;widths[font_index(code)+32]=12
    for _,old,new in fixed_relocations(mapping,assigned):
        a,b=font_index(old),font_index(new)
        font[b*22:(b+1)*22]=original[0x12fdb+a*22:0x12fdb+(a+1)*22]
        widths[b+32]=original[0x12adb+a+32]
    widths[0xff]=6
    menu[0x12adb:0x12fdb]=widths;menu[0x12fdb:0x19b1b]=font
    aliases=allocate_aliases(small_mapping);cursor=0x58000;unique={};encoded=[]
    for i,text in enumerate(texts):
        big=encode(text,mapping)+b'\0'
        # Description rows can contain native line separators. Their small
        # alternative is used only by single-line fixed-name output paths.
        small=encode_small(text,small_mapping,aliases)+b'\0' if i<len(selected) else b'\x16\0'
        for table,stream in [(0x54000,big),(0x56000,small)]:
            if stream not in unique:
                if cursor+len(stream)>0x5d000:raise ValueError('Menu description dictionary overlaps SwdTech helper')
                unique[stream]=cursor;menu[cursor:cursor+len(stream)]=stream;cursor+=len(stream)
            struct.pack_into('<I',menu,table+i*4,0x80140000+unique[stream])
        encoded.append({'id':i,'translation':text,'big_hex':big.hex(),'small_hex':small.hex()})
    for i,row in enumerate(selected):
        for occ in row['occurrences']:
            if occ['file']=='HAR/MENUMENU.BIN':
                at,n=occ['offset'],occ['length']
                menu[at:at+n]=reference(i)+b'\0'+b'\xff'*(n-4)
    cursors={}
    for i,row in enumerate(descriptions+extras,len(selected)):
        occ=next(x for x in row['occurrences'] if x['file']=='HAR/MENUMENU.BIN')
        base=occ['base'];at=cursors.get(base,base)
        stream=reference(i)+b'\0' if texts[i] else b'\0'
        if at+len(stream)>base+occ['capacity']:raise ValueError('Description reference pool overflow')
        struct.pack_into('<H',menu,occ['pointer_offset'],at-base)
        menu[at:at+len(stream)]=stream;cursors[base]=at+len(stream)
    code=(ROOT/'work/menu-big-runtime.bin').read_bytes()
    if len(code)>0x400:raise ValueError('Menu helper overlaps boost runtime')
    menu[0x5f000:0x5f000+len(code)]=code
    from swdtech_menu import patch as patch_swdtech
    menu,overlay=patch_swdtech(menu,overlay,mapping)
    report={'fixed_big_names':len(selected),'descriptions':len(descriptions),'ability_descriptions':len(extras),'dictionary_records':len(texts),
        'dictionary_bytes':cursor-0x58000,'glyphs':len(assigned),'font':'Galmuri9','cell':[12,11],'space_pixels':6,
        'runtime_bytes':len(code),'encoded':encoded,'mapping':{k:v.hex() for k,v in mapping.items()},
        'native_verification':'pending','battle_copy_insertion':'pending'}
    (ROOT/'analysis/menu-big-text-insertion.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    return menu,overlay
