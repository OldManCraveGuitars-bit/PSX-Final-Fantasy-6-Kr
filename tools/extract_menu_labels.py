"""Match positioned menu labels against the local PSX overlay bytes."""
import json,re,struct
from textcodec import ROOT,encode_original

ROMAJI_ALIASES={'MAIN_MENU_TIME','SKILLS_MP_COST','SKILLS_CHAR_LEVEL','SKILLS_CHAR_HP','SKILLS_CHAR_MP'}
JP=re.compile('[\u3040-\u30ff\u3400-\u9fff]')

def main():
    reference=ROOT/'references/ff6-disassembly/src/menu/menu_text.jp.inc'
    overlay=(ROOT/'work/decompressed/HAR/HARATA.PAC').read_bytes()
    rows=[];unmatched=[];seen=set();definitions=[]
    pattern=re.compile(r'^\.define\s+(\w+)\s+BG([123])([ABCD]),\s*\{(\d+),\s*(\d+)\},\s*\{([br]?)"([^"]*)"\}')
    for line in reference.read_text('utf8').splitlines():
        m=pattern.match(line)
        if not m:continue
        name,bg,screen,x,y,codec,text=m.groups()
        if codec or name in ROMAJI_ALIASES or not JP.search(text):continue
        definitions.append((name,bg,screen,x,y,text))
        xy=0x1849+(int(bg)-1)*0x2000+(ord(screen)-65)*0x800+(int(y)*32+int(x))*2
        try:encoded=encode_original(text.replace('{0}',''),'smallText')+b'\0'
        except ValueError as e:unmatched.append({'name':name,'source':text,'reason':str(e)});continue
        record=struct.pack('<H',xy)+encoded;matches=[];start=0
        while (at:=overlay.find(record,start))>=0:
            if at>=0x60000:matches.append(at)
            start=at+1
        if not matches:unmatched.append({'name':name,'source':text,'reason':'No identical PSX record'});continue
        for at in matches:
            if at in seen:continue
            seen.add(at)
            rows.append({'id':len(rows),'label':name,'source':text.replace('{0}','').rstrip('\u3000 '),
                'offset':at,'xy':xy,'record_bytes':len(record),'original_hex':record.hex(),'encoding':'smallText',
                'position':{'layer':f'BG{bg}{screen}','x':int(x),'y':int(y)}})
    # PSX uses FF padding in places where the SFC reference uses kana spaces.
    # Several controller labels also omit the final long-vowel mark.
    for name,bg,screen,x,y,text in definitions:
        if re.fullmatch(r'CTRL_CONFIG_(?:[ABXYLR]|SELECT_TEXT)',name):continue
        clean=text.replace('{0}','').rstrip('\u3000 ')
        variants={clean,clean.replace('コントローラー','コントローラ')}
        for variant in variants:
            for space in ['\u3000','\\pad']:
                try:encoded=encode_original(variant.replace('＿','…').replace('\u3000',space),'smallText')
                except ValueError:continue
                start=0x63000
                while (p:=overlay.find(encoded,start))>=0:
                    start=p+max(1,len(encoded));at=p-2
                    if at&3 or at in seen:continue
                    end=p+len(encoded)
                    while end<len(overlay) and overlay[end] in (0xff,0xfe):end+=1
                    if end>=len(overlay) or overlay[end]!=0:continue
                    if any(at<r['offset']+r['record_bytes'] and end+1>r['offset'] for r in rows):continue
                    xy=struct.unpack_from('<H',overlay,at)[0]
                    if not (0x1849<=xy<0x7849 and xy&1):continue
                    seen.add(at)
                    rows.append({'id':len(rows),'label':name,'source':clean,'offset':at,'xy':xy,
                        'record_bytes':end+1-at,'original_hex':overlay[at:end+1].hex(),'encoding':'smallText',
                        'position':{'layer':'PSX native','tile_address':hex(xy)}})
    matched_names={r['label'] for r in rows}
    unmatched=[r for r in unmatched if r['name'] not in matched_names]
    (ROOT/'analysis/menu-labels-original.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n','utf8')
    (ROOT/'analysis/menu-labels-unmatched.json').write_text(json.dumps(unmatched,ensure_ascii=False,indent=2)+'\n','utf8')
    print('Matched positioned Japanese labels:',len(rows),'Unmatched:',len(unmatched))
    print([(x['label'],x['source'],hex(x['offset'])) for x in rows[:12]])

if __name__=='__main__':main()
