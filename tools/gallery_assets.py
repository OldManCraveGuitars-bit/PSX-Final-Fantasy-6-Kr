"""Read the game's fixed-size 8-bit TIM gallery pages without recompression."""
import hashlib,struct
from pathlib import Path
from PIL import Image
from textcodec import ROOT

STRIDE=0x4c000
COUNTS={1:25,2:18,3:31,4:15,5:29}

def tim_page(data,index):
    start=index*STRIDE
    if data[start:start+8]!=struct.pack('<II',16,9):raise ValueError('Gallery TIM header guard')
    clut=start+8;n,cx,cy,cw,ch=struct.unpack_from('<I4H',data,clut)
    if (n,cw,ch)!=(524,256,1):raise ValueError('Gallery CLUT guard')
    palette=[]
    for i in range(256):
        v=struct.unpack_from('<H',data,clut+12+i*2)[0]
        palette.append(((v&31)*255//31,((v>>5)&31)*255//31,((v>>10)&31)*255//31))
    at=clut+n;n,x,y,w,h=struct.unpack_from('<I4H',data,at)
    if (n,w,h)!=(307212,320,480):raise ValueError('Gallery pixel dimensions guard')
    return at+12,palette,start,at+n

def picture(data,index):
    pixels,palette,_,_=tim_page(data,index)
    im=Image.frombytes('P',(640,480),bytes(data[pixels:pixels+640*480]))
    im.putpalette([c for rgb in palette for c in rgb]);return im.convert('RGB')

def source_hash(data,index):
    _,_,start,end=tim_page(data,index)
    return hashlib.sha256(data[start:end]).hexdigest()

def main():
    import json
    from PIL import ImageDraw
    folder=ROOT/'analysis/gallery-assets';folder.mkdir(exist_ok=True)
    rows=[]
    for n,count in COUNTS.items():
        rel=f'OMAKEDIR/GALLERY{n}.BIN';data=(ROOT/'work/extracted'/rel).read_bytes()
        if len(data)!=count*STRIDE:raise ValueError('Gallery file size guard')
        sheet=Image.new('RGB',(1280,((count+3)//4)*260),(25,25,25));d=ImageDraw.Draw(sheet)
        for i in range(count):
            im=picture(data,i);target=folder/f'GALLERY{n}-{i:02}.png';im.save(target)
            rows.append(dict(file=rel,image=i,sha256=source_hash(data,i),preview=target.relative_to(ROOT).as_posix()))
            x=i%4*320;y=i//4*260;sheet.paste(im.resize((320,240)),(x,y+20));d.text((x+4,y+3),f'GALLERY{n} / {i:02}',fill='white')
        sheet.save(ROOT/'analysis'/f'gallery{n}-contact.png')
    (ROOT/'analysis/gallery-original-assets.json').write_text(json.dumps(rows,indent=2)+'\n','utf8')
    print('Original gallery TIM pages:',len(rows))

if __name__=='__main__':main()
