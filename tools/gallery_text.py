"""Replace only explicitly reviewed text rectangles in native gallery TIMs."""
import json
from PIL import Image,ImageDraw,ImageFont
from textcodec import ROOT
from gallery_assets import STRIDE,COUNTS,tim_page,picture,source_hash
from gallery_format import validate_gallery_rows
from text_manager_model import Store,Metrics


def patch(changes):
    rows=json.loads((ROOT/'translations/gallery-text.ko.json').read_text('utf8')) if (ROOT/'translations/gallery-text.ko.json').exists() else []
    if not rows:return changes
    validate_gallery_rows(rows)
    store=Store(ROOT);metrics=Metrics(json.loads((ROOT/'assets/text-manager/text-metrics.json').read_text('utf8')))
    records={r.key:r for r in store.records if r.group=='갤러리 설명'}
    originals={rel:(ROOT/'work/extracted'/rel).read_bytes() for rel in {r['file'] for r in rows}}
    output={rel:bytearray(data) for rel,data in originals.items()}
    masks={};font=ImageFont.truetype(str(ROOT/'assets/fonts/Galmuri7.ttf'),8)
    report=[]
    for row in rows:
        rel=row['file'];i=row['image'];record=records[str(row['id'])]
        if not record.reviewed:raise ValueError('Gallery translation not reviewed: '+record.key)
        if row['source_TIM_sha256']!=source_hash(originals[rel],i):raise ValueError('Gallery source image changed')
        issues,text,lines=metrics.check(record)
        if any(v.severity=='오류' for v in issues):raise ValueError(('Gallery layout error',record.key,issues))
        if len({line.page for line in lines})!=1:raise ValueError('Gallery text must stay in one rectangle')
        offset,palette,start,end=tim_page(originals[rel],i)
        white=min(range(256),key=lambda j:sum((v-255)**2 for v in palette[j]))
        black=min(range(256),key=lambda j:sum(v*v for v in palette[j]))
        x,y,w,h=row['rect'];bg,fg=(black,white) if row.get('background')=='black' else (white,black)
        bitmap=Image.new('1',(w,h));draw=ImageDraw.Draw(bitmap)
        for line in lines:
            cursor=line.offset
            for token in line.tokens:
                if token.startswith('{'):raise ValueError('Gallery does not execute game text controls')
                if token!=' ':draw.text((cursor,(line.number-1)*record.profile.pitch),token,font=font,fill=1)
                cursor+=metrics.advance(token,record.profile)
        mask=masks.setdefault((rel,i),bytearray(640*480))
        # Erase the complete source glyphs, independently of the Korean layout.
        # Drawing foreground only keeps arrows and artwork inside a layout box.
        for a,b,c,d in row.get('erase_rects',[row['rect']]):
            for yy in range(b,b+d):
                at=yy*640+a
                erase_bg=originals[rel][offset+yy*640+row['erase_sample_x']] if 'erase_sample_x' in row else bg
                output[rel][offset+at:offset+at+c]=bytes([erase_bg])*c
                mask[at:at+c]=b'\1'*c
        for yy in range(h):
            for xx in range(w):
                if bitmap.getpixel((xx,yy)):
                    at=(y+yy)*640+x+xx
                    if palette[originals[rel][offset+at]]!=palette[bg] and not mask[at]:
                        # Native text is antialiased; any drawing over artwork
                        # must be explicitly included in a reviewed erase box.
                        raise ValueError(('Korean glyph touches unapproved source ink',row['id'],x+xx,y+yy))
                    output[rel][offset+at]=fg;mask[at]=1
        report.append(dict(id=row['id'],file=rel,image=i,rect=row['rect'],erase_rects=row.get('erase_rects',[row['rect']]),max_width=max(l.width for l in lines),lines=len(lines),font='Galmuri7',cell=8,space=4))
    # Compare every byte, including palettes, image headers and per-page padding.
    changed_bytes=0
    for rel,data in output.items():
        original=originals[rel];allowed=bytearray(len(original))
        for (file,index),mask in masks.items():
            if file==rel:
                offset,*_=tim_page(original,index);allowed[offset:offset+640*480]=mask
        for pos,(a,b) in enumerate(zip(original,data)):
            if a!=b:
                if not allowed[pos]:raise ValueError(('Gallery artwork changed outside text',rel,pos))
                changed_bytes+=1
        if len(data)!=len(original):raise ValueError('Gallery extent length changed')
    folder=ROOT/'analysis/gallery-korean';folder.mkdir(exist_ok=True)
    for rel,i in masks:picture(output[rel],i).save(folder/f'{rel.split("/")[-1][:-4]}-{i:02}.png')
    result=dict(records=len(rows),pages=len(masks),files=sorted(output),changed_pixel_bytes=changed_bytes,
        untouched_artwork_headers_palettes_and_padding='byte-identical outside approved text rectangles',
        font='Galmuri7',cell=8,space=4,entries=report)
    (ROOT/'analysis/gallery-text-insertion.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    changes=dict(changes);changes.update({rel:bytes(data) for rel,data in output.items()});return changes

if __name__=='__main__':
    result=patch({})
    for rel,data in result.items():
        out=ROOT/'work/modified'/rel;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
    print({rel:len(data) for rel,data in result.items()})
