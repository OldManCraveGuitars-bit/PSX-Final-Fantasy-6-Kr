"""Check source art, arrow tails, English quotes and formerly clipped glyphs."""
import hashlib,json,sys
from gallery_assets import COUNTS,STRIDE,tim_page
from textcodec import ROOT


def main():
    originals={n:(ROOT/f'work/extracted/OMAKEDIR/GALLERY{n}.BIN').read_bytes() for n in COUNTS}
    outputs={n:(ROOT/f'work/modified/OMAKEDIR/GALLERY{n}.BIN').read_bytes() if n in (2,4,5) else originals[n] for n in COUNTS}
    def crop(bank,n,i,box):
        x,y,w,h=box;offset,*_=tim_page(bank[n],i)
        return b''.join(bank[n][offset+yy*640+x:offset+yy*640+x+w] for yy in range(y,y+h))
    protected=[
      (2,12,'metal arrow',[233,288,21,14]),
      (2,12,'belt arrow',[246,354,19,10]),
      (2,12,'helmet arrow',[412,281,40,28]),
      (5,28,'tip arrow',[396,201,16,27]),
      (5,28,'muscle arrow',[547,122,8,24]),
      (5,28,'surface-pattern arrow',[491,133,24,29]),
      (2,0,'English Vecta quotation',[252,408,318,13]),
      (2,5,'English command quotation',[252,431,318,16]),
      (2,6,'English attack quotation',[252,63,318,14]),
      (2,1,'unreadable handwritten timing note and diagram',[350,259,72,40]),
    ]
    results=[]
    for n,i,label,box in protected:
        before=crop(originals,n,i,box);after=crop(outputs,n,i,box)
        assert before==after,('Protected gallery pixels changed',n,i,label)
        results.append(dict(file=f'GALLERY{n}.BIN',image=i,description=label,rect=box,byte_identical=True,sha256=hashlib.sha256(after).hexdigest()))
    # These source antialiasing strokes used to survive outside the old boxes.
    cleared=[(2,1,[322,45,248,4]),(5,28,[18,298,9,26]),(5,28,[343,179,92,4]),(5,28,[527,87,4,33])]
    for n,i,box in cleared:
        offset,palette,*_=tim_page(outputs[n],i)
        white=min(range(256),key=lambda j:sum((v-255)**2 for v in palette[j]))
        pixels=crop(outputs,n,i,box)
        assert all(palette[v]==palette[white] for v in pixels),('Japanese stroke remains',n,i,box)
    rows=json.loads((ROOT/'translations/gallery-text.ko.json').read_text('utf8'))
    changed={(int(r['file'][-5]),r['image']) for r in rows}
    for n,count in COUNTS.items():
        assert len(outputs[n])==len(originals[n])==count*STRIDE
        for i in range(count):
            offset,_,start,end=tim_page(originals[n],i)
            assert outputs[n][start:offset]==originals[n][start:offset],('Header or palette changed',n,i)
            assert outputs[n][end:(i+1)*STRIDE]==originals[n][end:(i+1)*STRIDE],('TIM padding changed',n,i)
            if (n,i) not in changed:assert outputs[n][start:(i+1)*STRIDE]==originals[n][start:(i+1)*STRIDE],('Unedited page changed',n,i)
    result=dict(records=len(rows),edited_pages=len(changed),total_pages=sum(COUNTS.values()),
        palettes_headers_padding_and_unedited_pages='byte-identical',protected_regions=results,
        old_stray_stroke_regions_clean=len(cleared),
        pending=['GALLERY2 image 1: original tiny handwritten timing note is illegible; preserved complete, untranslated.'])
    tag=sys.argv[1] if len(sys.argv)>1 else 'v070'
    (ROOT/f'analysis/{tag}-gallery-graphics-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    print(dict(records=len(rows),edited_pages=len(changed),protected_regions=len(results),stray_stroke_regions_clean=len(cleared)))


if __name__=='__main__':main()
