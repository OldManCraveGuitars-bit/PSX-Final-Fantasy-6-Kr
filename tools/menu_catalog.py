"""Relocate Korean menu names while retaining the native fixed-size tables."""
import json,struct,re
from textcodec import ROOT
from korean_codec import JP,normalize,CONTROL
from small_text import encode_small,allocate_aliases

def patch(menu,label_end,mapping):
    originals=json.loads((ROOT/'analysis/fixed-catalog-original.json').read_text('utf8'))
    translated=json.loads((ROOT/'translations/fixed-catalog.ko.json').read_text('utf8'))
    aliases=allocate_aliases(mapping)
    selected=[row for row in originals if row['category'] in ['spell','command','item','monster'] and JP.search(row['source'])]
    jobs=json.loads((ROOT/'translations/menu-jobs.ko.json').read_text('utf8'))
    for i in range(64):
        row=jobs[str(i)];identifier=f'job_{i}'
        selected.append({'id':identifier,'category':'job','source':row['source'],
            'occurrences':[{'file':'HAR/MENUMENU.BIN','offset':0x19b1b+i*7,'length':7}]})
        translated[identifier]=row
    pointer_end=(0x53020+len(selected)*4+15)&~15
    spans=[(0x25050,0x25400),(0x25700,0x25800),(0x25990,0x26000),(0x30800,0x30d00),(label_end,0x32000),(pointer_end,0x54000)]
    if pointer_end>=0x54000:raise ValueError('Menu-name pointer table overflow')
    span=0;cursor=spans[0][0];unique={};wide=[];count={};inserted=[]
    for identifier,row in enumerate(selected):
        text=normalize(translated[str(row['id'])]['translation']).strip()
        encoded=encode_small(text,mapping,aliases)+b'\0'
        if encoded not in unique:
            while cursor+len(encoded)>spans[span][1]:
                span+=1
                if span>=len(spans):raise ValueError('Korean menu-name dictionary overflow')
                cursor=spans[span][0]
            unique[encoded]=0x80140000+cursor;menu[cursor:cursor+len(encoded)]=encoded;cursor+=len(encoded)
        struct.pack_into('<I',menu,0x53020+identifier*4,unique[encoded])
        for occurrence in row['occurrences']:
            if occurrence['file']!='HAR/MENUMENU.BIN':continue
            offset=occurrence['offset'];length=occurrence['length']
            icon=bytes.fromhex(row['original_hex'])[:1] if row['category'] in ['item','spell'] else b''
            if icon and icon[0]<0xe0:raise ValueError(('Unsupported leading icon',row['source'],icon.hex()))
            stub=icon+bytes((0x17,identifier&255,identifier>>8))
            menu[offset:offset+length]=stub+b'\xff'*(length-len(stub))
        count[row['category']]=count.get(row['category'],0)+1
        plain=CONTROL.sub('■',text);width=sum(4 if c==' ' else 8 for c in plain)
        limit=row['occurrences'][0]['length']*8
        if width>limit:wide.append({'id':row['id'],'category':row['category'],'source':row['source'],'translation':text,'pixels':width,'original_cell_pixels':limit})
        inserted.append({'id':row['id'],'dictionary_id':identifier,'translation':text,'encoded_hex':encoded.hex()})
    report={'menu_entries':len(selected),'categories':count,'unique_strings':len(unique),
        'dictionary_bytes':sum(len(x) for x in unique),'pointer_bytes':len(selected)*4,
        'layout_overflow_count':len(wide),'menu_only':True,'battle_and_field_tables':'pending their own native output paths'}
    (ROOT/'analysis/menu-catalog-insertion.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    (ROOT/'analysis/menu-catalog-wide.json').write_text(json.dumps(wide,ensure_ascii=False,indent=2)+'\n','utf8')
    (ROOT/'analysis/menu-catalog-encoded.json').write_text(json.dumps(inserted,ensure_ascii=False,indent=2)+'\n','utf8')
    return menu,report
